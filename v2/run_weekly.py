"""周报生产编排入口（新 SOP 三板块周报，单篇 report.md）。

与 run_daily.py（每日采集）并列的独立编排。跑通 5 个阶段：
  1. compute   纯本地：7天 diff + 范围闸门（范围外库排斥 + 范围内库名准入）
               + 板块归属 + 8 分类 + 适用数据库 + 三板块候选池（活跃榜超额选取；
               新锐候选取自新生项目源 new_projects，7 天内创建者）→ sections.json
  2. readme    对候选池（活跃榜+新锐池）拉 README → readmes.json
  3. select    README 范围复核（范围外生态剔除递补 + 适用数据库精化）
               + 定榜（活跃榜 Top3 / 新锐 / 本周解读）→ 回写 sections.json
  4. ai        每项目 80 字中性 AI 解读 + 本周解读三维分析（带缓存）→ ai_reviews.json
  5. render    组装三板块周报 Markdown（板块卡片 + Top 总榜表格）→ weekly/report.md

依赖 run_daily 已产出当日候选池（merged/all_projects.json）。
旧版 releases/license 采集与 toolkit 周报已移除（新 SOP 不含 License 栏 / 工具合辑）。

用法：
  python run_weekly.py                       # 全流程
  python run_weekly.py --only compute        # 只算（diff/板块/选取），不调网络
  python run_weekly.py --only readme         # 只拉候选 README（需先 compute）
  python run_weekly.py --only ai             # 只生成 AI 解读（需先 compute+readme）
  python run_weekly.py --only render         # 只渲染（需先 compute+ai）
  python run_weekly.py --date 20260813 --prev-date 20260805
  python run_weekly.py --no-resume           # 强制重算（忽略断点）
  python run_weekly.py -v
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

import config
import storage
from ai_client import AIClient
from github_client import GitHubClient

from collectors import commit_activity as commit_mod
from collectors import readme as readme_mod

import analytics
import filters
import render
import sections
import tool_registry as reg

log = logging.getLogger("run_weekly")

SECTION_ORDER = render.SECTION_ORDER


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def _full(it: dict[str, Any]) -> str:
    return str(it.get("full_name") or "")


def _human_date(date: str) -> str:
    """YYYYMMDD → YYYY-MM-DD；格式非法时回退当天。"""
    if len(date) == 8 and date.isdigit():
        return f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    return config.TODAY_HUMAN


def _issue_no(date: str) -> int:
    """期号：距 config.FIRST_ISSUE_DATE 的满周数 + 1（首期 1，每周 +1）。"""
    from datetime import datetime as _dt

    try:
        d0 = _dt.strptime(config.FIRST_ISSUE_DATE, "%Y%m%d").date()
        d1 = _dt.strptime(date, "%Y%m%d").date()
    except ValueError:
        return 0
    return max(0, (d1 - d0).days // 7 + 1)


def _load_candidate_pool(date: str) -> list[dict[str, Any]]:
    """读当日候选池（run_daily 产出）。不存在则报错退出。"""
    pool = storage.load_snapshot_pool(date)
    if not pool:
        log.error("当日候选池不存在或为空：%s\n请先跑 `python run_daily.py` 完成每日采集。", date)
        sys.exit(2)
    return pool


def _to_row(it: dict[str, Any], cat: str, db: str, growth: Any) -> dict[str, Any]:
    """把项目 + 分类/适用数据库/增长打成 render 用的 row。

    topics 一并保留 —— select 阶段用 README 精化「适用数据库」时需要重建检索串；
    commit_count_7d 保留 —— 新锐 0-star 项目按近 7 天 commit 排序用。
    """
    return {
        "full_name": _full(it),
        "html_url": it.get("html_url", "#"),
        "category": cat,
        "databases": db,
        "growth": growth,
        "description": it.get("description") or "",
        "topics": it.get("topics") or [],
        "star": it.get("stargazers_count", 0),
        "commit_count_7d": it.get("commit_count_7d"),
    }


# ============================================================
# 阶段 1：compute（纯本地）
# ============================================================
def stage_compute(
    display_pool: list[dict[str, Any]],
    date: str,
    prev_date: str | None,
) -> dict[str, Any]:
    """diff + 板块归属 + 分类 + 适用数据库 + 三板块选取 → 落 sections.json。"""
    log.info("==== 阶段1：计算（diff / 板块 / 分类 / 选取）====")

    prev_pool = None
    if prev_date:
        prev_raw = storage.load_snapshot_pool(prev_date)
        if prev_raw:
            prev_pool = filters.filter_display_pool(prev_raw)
    diffs = analytics.diff_snapshots(display_pool, prev_pool)
    star_deltas: dict[str, int] = diffs.get("star_deltas", {})
    log.info(
        "diff：%s（基准 %s），star 增量 %d 项，新入榜 %d",
        "首期(无基准)" if diffs["first_period"] else "正常",
        prev_date or "无",
        len(star_deltas), len(diffs.get("new_entries", [])),
    )
    storage.save_weekly_meta("diff", {**diffs, "current_date": date, "prev_date": prev_date}, date)

    # 板块归属 + 分类 + 适用数据库 + 排除（内核 + SOP §3.3 + 范围外库）
    items_by_sec: dict[str, list[dict[str, Any]]] = {s: [] for s in SECTION_ORDER}
    meta_map: dict[str, tuple[str, str]] = {}  # full_name -> (category, databases)
    excluded_kernel = excluded_sop = excluded_scope = 0
    for it in display_pool:
        full = _full(it)
        if reg.is_kernel(full):
            excluded_kernel += 1
            continue
        if sections.should_exclude_sop(it):
            excluded_sop += 1
            continue
        if sections.is_out_of_scope(it):
            excluded_scope += 1
            continue
        sec = sections.assign_section(it)
        if sec not in items_by_sec:
            continue
        cat = sections.infer_category(it)
        db = sections.infer_databases(it)
        items_by_sec[sec].append(it)
        meta_map[full] = (cat, db)
    log.info(
        "板块归属：国外 %d / 国产 %d / AI %d（剔除内核 %d、SOP排除 %d、范围外 %d）",
        len(items_by_sec["国外数据库"]), len(items_by_sec["国产数据库"]),
        len(items_by_sec["AI工具"]), excluded_kernel, excluded_sop, excluded_scope,
    )

    # 新锐发现：新生项目源（new_projects：30 天窗 + star≥3）为主，
    # 存量池里 7 天内创建的项目（org 扫描/白名单捞到的，如 openGauss 镜像仓）并入。
    # 存量池主力是 star≥10 的 topic 采集，7 天内新建项目大多不在其中，
    # 旧逻辑只从存量池找新锐几乎必然为空。两源并集去重，按 star 预排候选；
    # 最终排序在 select：star 降序，0-star（或同 star）按近 7 天 commit 数降序。
    new_secs: dict[str, list[dict[str, Any]]] = {s: [] for s in SECTION_ORDER}
    seen_new: set[str] = set()
    new_raw = filters.filter_display_pool(storage.load_all_new_projects(date))
    for it in new_raw:
        full = _full(it)
        if reg.is_kernel(full) or sections.should_exclude_sop(it) or sections.is_out_of_scope(it):
            continue
        if not analytics._created_recent(it, config.NEWSTAR_DAYS):
            continue
        sec = sections.assign_section(it)
        if sec not in new_secs or full in seen_new:
            continue
        seen_new.add(full)
        new_secs[sec].append(it)
        meta_map[full] = (sections.infer_category(it), sections.infer_databases(it))
    for sec, sec_items in items_by_sec.items():
        for it in sec_items:
            full = _full(it)
            if full in seen_new or not analytics._created_recent(it, config.NEWSTAR_DAYS):
                continue
            seen_new.add(full)
            new_secs[sec].append(it)
            meta_map.setdefault(full, (sections.infer_category(it), sections.infer_databases(it)))
    for sec_items in new_secs.values():
        sec_items.sort(key=lambda x: x.get("stargazers_count", 0) or 0, reverse=True)
    log.info(
        "新锐候选（7 天内创建，新生源+存量池）：国外 %d / 国产 %d / AI %d",
        len(new_secs["国外数据库"]), len(new_secs["国产数据库"]), len(new_secs["AI工具"]),
    )

    sections_out: list[dict[str, Any]] = []
    for key in SECTION_ORDER:
        items = items_by_sec[key]

        def _rows(seq: list[dict[str, Any]]) -> list[dict[str, Any]]:
            out = []
            for it in seq:
                cat, db = meta_map.get(_full(it), ("其他", "待确认"))
                # 新生项目不在 diff 里，增长以当前 star 计（新建项目周增长≈当前 star）
                growth = star_deltas.get(_full(it))
                if growth is None:
                    growth = it.get("stargazers_count", 0)
                out.append(_to_row(it, cat, db, growth))
            return out

        # 超额选取候选池（含缓冲）；README 范围复核剔除后由 select 阶段递补定榜
        active_pool = analytics.section_active_top(items, star_deltas, n=config.SECTION_POOL_N)
        active_fulls = {_full(it) for it in active_pool}
        newcomer_items = [
            it for it in new_secs[key] if _full(it) not in active_fulls
        ][: config.NEWSTAR_POOL_N]
        sections_out.append({
            "key": key,
            "active_pool": _rows(active_pool),
            "newcomer_pool": _rows(newcomer_items),
            "active": [],
            "newcomers": [],
            "focus": None,
        })
        log.info(
            "  %s：活跃候选 %d、新锐候选 %d（定榜待 README 复核）",
            key, len(active_pool), len(newcomer_items),
        )

    # Top 总榜（历史 Star 降序取 Top5；与三板块同一套范围闸门：
    # 内核 / SOP排除 / 范围外 / 无归属的项目一律不收）
    tb_sorted = sorted(
        (it for it in display_pool
         if not reg.is_kernel(_full(it)) and not sections.should_exclude_sop(it)),
        key=lambda it: it.get("stargazers_count", 0) or 0,
        reverse=True,
    )
    topboard = []
    for it in tb_sorted:
        if len(topboard) >= config.TOPBOARD_TOP:
            break
        full = _full(it)
        sec = sections.assign_section(it)
        if sec is None:
            continue
        cat, _db = meta_map.get(full, (sections.infer_category(it), ""))
        topboard.append({
            "full_name": full,
            "html_url": it.get("html_url", "#"),
            "star": it.get("stargazers_count", 0),
            "section": sec,
            "category": cat,
            "description": it.get("description") or "",
        })

    data = {
        "snapshot_date": _human_date(date),
        "first_period": diffs["first_period"],
        "prev_date": prev_date,
        "finalized": False,  # select 阶段定榜后置 True
        "sections": sections_out,
        "topboard": topboard,
    }
    storage.save_weekly_meta("sections", data, date)
    return data


def _pool_fulls(sections_data: dict[str, Any]) -> list[str]:
    """收集候选池（活跃池+新锐池）full_name，供 README 采集（去重保序）。"""
    seen: set[str] = set()
    out: list[str] = []
    for sec in sections_data.get("sections", []):
        for row in (sec.get("active_pool") or []) + (sec.get("newcomer_pool") or []):
            fn = row.get("full_name", "")
            if fn and fn not in seen:
                seen.add(fn)
                out.append(fn)
    return out


def _candidate_fulls(sections_data: dict[str, Any]) -> list[str]:
    """收集需要 AI 解读的定榜候选（活跃榜+新锐+本周解读，去重保序）。"""
    seen: set[str] = set()
    out: list[str] = []
    for sec in sections_data.get("sections", []):
        for row in (sec.get("active") or []) + (sec.get("newcomers") or []):
            fn = row.get("full_name", "")
            if fn and fn not in seen:
                seen.add(fn)
                out.append(fn)
        focus = sec.get("focus") or {}
        fn = focus.get("full_name", "")
        if fn and fn not in seen:
            seen.add(fn)
            out.append(fn)
    return out


# ============================================================
# 阶段 2：readme（拉候选 README）
# ============================================================
def stage_readme(date: str, candidates: list[str], resume: bool) -> dict[str, str]:
    """对候选清单拉 README → weekly/meta/readmes.json（断点续采）。"""
    log.info("==== 阶段2：README 采集（%d 候选）====", len(candidates))
    if not candidates:
        return {}
    client = GitHubClient()
    return readme_mod.collect_readmes(client, candidates, resume=resume, date=date)


# ============================================================
# 阶段 3：select（README 范围复核 + 三板块定榜）
# ============================================================
def _row_item(row: dict[str, Any]) -> dict[str, Any]:
    """从 row 还原 infer_databases 需要的最小 item（full_name/description/topics）。"""
    return {
        "full_name": row.get("full_name", ""),
        "description": row.get("description", ""),
        "topics": row.get("topics") or [],
    }


def _readme_scope_ok(row: dict[str, Any], readme: str | None) -> bool:
    """README 范围复核：

    - README 命中范围内库名 → 通过；
    - 未命中且出现范围外库名 → 剔除（desc/topics 误报，如只把范围内库当卖点词）；
    - 两者皆无 / README 未采到 → 保守保留（desc 准入已通过）。
    注意不在 README 上做单向排除：README 提到范围内库 + 范围外库（对比/部署依赖）
    属正常情况，以范围内命中为准。
    """
    if not readme:
        return True
    if sections.in_scope_hit_text(readme):
        return True
    return not sections.is_out_of_scope_text(readme)


def _fetch_zero_star_commits(rows: list[dict[str, Any]]) -> GitHubClient | None:
    """对 0-star 且缺 commit 数据的新锐候选拉取近 7 天 commit 数（新锐排序次级键）。

    懒创建 client：无待拉项目时不产生任何 API 调用。participation 首次常返回
    202（get_commit_count_7d 内部已轮询处理）；拉不到记 None，排序时视为 0。
    """
    need = [r for r in rows if not (r.get("star") or 0) and r.get("commit_count_7d") is None]
    if not need:
        return None
    client = GitHubClient()
    for r in need:
        owner, _, repo = (r.get("full_name") or "").partition("/")
        if not owner or not repo:
            continue
        try:
            count, _src = commit_mod.get_commit_count_7d(client, owner, repo)
        except Exception as e:  # noqa: BLE001
            log.warning("commit 活跃度拉取失败 %s: %s", r.get("full_name"), e)
            count = None
        r["commit_count_7d"] = count
        log.info("  新锐 commit ✓ %-42s 近7天 %s",
                 r.get("full_name"), count if count is not None else "未知")
    return client


def stage_select(date: str, sections_data: dict[str, Any], readmes: dict[str, str]) -> dict[str, Any]:
    """README 范围复核 + 三板块定榜（活跃榜 Top3 / 新锐 / 本周解读）→ 回写 sections.json。

    compute 超额选取的候选池在此复核：范围外生态项目剔除后由后续名次递补；
    上榜项目用 README 精化「适用数据库」（关键词表仅含范围内库，不会引入范围外名）。
    新锐排序：star 降序，0-star（或同 star）项目按近 7 天 commit 数降序。
    """
    log.info("==== 阶段3：定榜（README 范围复核）====")
    readmes = readmes or {}
    interpreted: set[str] = set()
    for sec in sections_data.get("sections", []):
        key = sec.get("key", "")
        active_pool = sec.get("active_pool") or []
        newcomer_pool = sec.get("newcomer_pool") or []

        def _refine(row: dict[str, Any]) -> None:
            readme = readmes.get(row.get("full_name", ""))
            db = sections.infer_databases(_row_item(row), extra_text=readme or "")
            if db and db != "待确认":
                row["databases"] = db

        def _ok(row: dict[str, Any]) -> bool:
            return _readme_scope_ok(row, readmes.get(row.get("full_name", "")))

        active = [r for r in active_pool if _ok(r)][: config.SECTION_TOP_N]
        for r in active:
            _refine(r)

        active_names = {r.get("full_name", "") for r in active}
        newcomer_cands = [
            r for r in newcomer_pool
            if r.get("full_name", "") not in active_names and _ok(r)
        ]
        _fetch_zero_star_commits(newcomer_cands)
        newcomer_cands.sort(
            key=lambda r: (-(r.get("star") or 0), -(r.get("commit_count_7d") or 0))
        )
        newcomers = newcomer_cands[: config.NEWSTAR_TOP_N]
        for r in newcomers:
            _refine(r)

        focus = analytics.pick_section_focus(active, interpreted)
        if focus:
            interpreted.add(focus.get("full_name", ""))

        sec["active"] = active
        sec["newcomers"] = newcomers
        sec["focus"] = focus
        log.info(
            "  %s：定榜 活跃 %d/%d、新锐 %d/%d、解读 %s",
            key, len(active), len(active_pool),
            len(newcomers), len(newcomer_pool),
            (focus or {}).get("full_name", "无"),
        )
    sections_data["finalized"] = True
    storage.save_weekly_meta("sections", sections_data, date)
    return sections_data


# ============================================================
# 阶段 3：ai（每项目 80 字中性解读 + 三维分析，带缓存）
# ============================================================
def stage_ai(
    date: str,
    sections_data: dict[str, Any],
    pool: list[dict[str, Any]],
    readmes: dict[str, str],
    resume: bool,
) -> dict[str, Any]:
    """生成 AI 解读 → weekly/meta/ai_reviews.json（key=full_name，断点续采）。"""
    log.info("==== 阶段4：AI 解读（80 字中性 + 三维）====")
    cache: dict[str, Any] = {}
    if resume:
        existing = storage.load_weekly_meta("ai_reviews", date)
        if isinstance(existing, dict):
            cache = existing
    brief_cache: dict[str, str] = dict(cache.get("brief") or {})
    three_cache: dict[str, dict[str, str]] = dict(cache.get("three") or {})

    pool_map = {_full(it): it for it in pool}
    ai = AIClient()
    if not ai.enabled:
        log.warning("AI 未启用（无 AI_API_KEY），将回退占位解读。")

    candidates = _candidate_fulls(sections_data)
    focus_fulls = {
        (sec.get("focus") or {}).get("full_name", "")
        for sec in sections_data.get("sections", [])
    }
    focus_fulls.discard("")

    # 80 字中性解读（活跃榜+新锐+本周解读全部）
    done_brief = 0
    for fn in candidates:
        if fn in brief_cache:
            continue
        it = pool_map.get(fn, {"full_name": fn, "description": "", "topics": []})
        cat, db = _meta_for(sections_data, fn)
        brief_cache[fn] = ai.brief_review(it, cat, db, readmes.get(fn))
        done_brief += 1
        log.info("  解读 ✓ %-40s (%d/%d)", fn, done_brief, len(candidates))

    # 三维分析（本周解读项目）
    done_three = 0
    for fn in focus_fulls:
        if fn in three_cache:
            continue
        it = pool_map.get(fn, {"full_name": fn, "description": "", "topics": []})
        cat, db = _meta_for(sections_data, fn)
        three_cache[fn] = ai.three_dimension_analysis(it, cat, db, readmes.get(fn))
        done_three += 1
        log.info("  三维 ✓ %-40s (%d/%d)", fn, done_three, len(focus_fulls))

    out = {
        "snapshot_date": _human_date(date),
        "brief": brief_cache,
        "three": three_cache,
    }
    storage.save_weekly_meta("ai_reviews", out, date)
    log.info("AI 解读完成：brief %d、three %d（已落盘 ai_reviews.json）",
             len(brief_cache), len(three_cache))
    return out


def _meta_for(sections_data: dict[str, Any], full_name: str) -> tuple[str, str]:
    """从 sections_data 查某项目的分类/适用数据库（找不到回退其他/待确认）。"""
    for sec in sections_data.get("sections", []):
        for row in (sec.get("active") or []) + (sec.get("newcomers") or []):
            if row.get("full_name") == full_name:
                return row.get("category", "其他"), row.get("databases", "待确认")
        f = sec.get("focus") or {}
        if f.get("full_name") == full_name:
            return f.get("category", "其他"), f.get("databases", "待确认")
    return "其他", "待确认"


# ============================================================
# 阶段 4：render（组装三板块周报）
# ============================================================
def stage_render(date: str, sections_data: dict[str, Any], ai_reviews: dict[str, Any]) -> str:
    """把 sections + ai_reviews 合并成 report_data，渲染 → weekly/report.md。"""
    log.info("==== 阶段5：渲染（三板块周报）====")
    brief = (ai_reviews or {}).get("brief") or {}
    three = (ai_reviews or {}).get("three") or {}

    # 把 AI 解读/三维并入 sections
    for sec in sections_data.get("sections", []):
        for row in (sec.get("active") or []) + (sec.get("newcomers") or []):
            fn = row.get("full_name", "")
            row["review"] = brief.get(fn, "")
        f = sec.get("focus")
        if f:
            f["three"] = three.get(f.get("full_name", ""), {})

    report_md = render.render_main_report(sections_data, issue_no=_issue_no(date))
    report_path = storage.report_file(date)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    log.info("周报已生成：%s", report_path)
    return report_path


# ============================================================
# 编排
# ============================================================
def run_pipeline(args: argparse.Namespace) -> None:
    date = args.date or config.TODAY
    resume = not args.no_resume
    only = args.only
    start = time.time()

    pool = _load_candidate_pool(date)
    display_pool = filters.filter_display_pool(pool)
    if len(display_pool) < len(pool):
        log.info("展示相关性过滤：候选池 %d → 展示池 %d（剔除 %d 个非数据库相关）",
                 len(pool), len(display_pool), len(pool) - len(display_pool))

    # 基准快照
    prev_date = args.prev_date
    if prev_date is None and only in (None, "compute", "render"):
        prev_date = storage.find_prev_snapshot_date(date)
        if prev_date:
            log.info("基准快照（自动定位）：%s", prev_date)
        else:
            log.info("无更早快照，本期为首期（动态栏目将标注'首期无基准'）")

    # ---- compute ----
    sections_data: dict[str, Any] | None = None
    if only in (None, "compute", "readme", "select", "ai", "render"):
        if only in (None, "compute"):
            sections_data = stage_compute(display_pool, date, prev_date)
        else:
            sections_data = storage.load_weekly_meta("sections", date)
            if not isinstance(sections_data, dict) or not sections_data.get("sections"):
                log.error("缺少 compute 结果（sections.json）。请先跑 `--only compute` 或全流程。")
                sys.exit(2)

    # ---- readme ----
    readmes: dict[str, str] = {}
    if only in (None, "readme", "select", "ai"):
        if only in (None, "readme"):
            readmes = stage_readme(date, _pool_fulls(sections_data), resume)
        else:
            rdata = storage.load_weekly_meta("readmes", date)
            readmes = (rdata or {}).get("by_repo") if isinstance(rdata, dict) else {}
            readmes = {k: v for k, v in (readmes or {}).items() if v}

    # ---- select ----
    if only in (None, "select", "ai", "render"):
        if only in (None, "select"):
            sections_data = stage_select(date, sections_data, readmes)
        elif not sections_data.get("finalized"):
            log.error("sections.json 尚未定榜。请先跑 `--only select` 或全流程。")
            sys.exit(2)

    # ---- ai ----
    ai_reviews: dict[str, Any] = {}
    if only in (None, "ai", "render"):
        if only in (None, "ai"):
            ai_reviews = stage_ai(date, sections_data, pool, readmes, resume)
        else:  # render：复用已落盘 ai_reviews
            ai_reviews = storage.load_weekly_meta("ai_reviews", date) or {}

    # ---- render ----
    if only in (None, "render"):
        # 基准日以 sections.json 为准（compute 时记入），避免 render 单跑时重新自动定位导致显示不一致
        prev_date = sections_data.get("prev_date") or prev_date
        report_path = stage_render(date, sections_data, ai_reviews)
        print()
        print("=" * 56)
        print(f"  周报：    {report_path}")
        print(f"  采集日：{sections_data.get('snapshot_date') or config.TODAY_HUMAN} ({date})  基准：{prev_date or '无(首期)'}")
        print("=" * 56)

    elapsed = time.time() - start
    log.info("==== 周报生产完成（耗时 %.1f 分钟）====", elapsed / 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="数据库开源生态周报 · 周报生产（新 SOP 三板块，对标 run_daily.py）"
    )
    parser.add_argument(
        "--only",
        choices=["compute", "readme", "select", "ai", "render"],
        help="只跑指定阶段（默认全流程）",
    )
    parser.add_argument("--date", help="快照日期 YYYYMMDD（默认今天）")
    parser.add_argument(
        "--prev-date",
        help="对比基准快照日期 YYYYMMDD（默认自动找 7 天前最近的）",
    )
    parser.add_argument(
        "--no-resume", action="store_true",
        help="强制重采/重算（忽略断点续采与已落盘中间结果）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")
    args = parser.parse_args()

    _setup_logging(args.verbose)
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        log.warning("用户中断（中间数据已落盘 weekly/meta/，重跑可续）")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        log.exception("周报生产失败：%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
