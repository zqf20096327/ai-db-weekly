"""周报生产编排入口（新 SOP 三板块周报，单篇 report.md）。

与 run_daily.py（每日采集）并列的独立编排。跑通 4 个阶段：
  1. compute   纯本地：7天 diff + 板块归属 + 8 分类 + 适用数据库 + 三板块选取 → sections.json
  2. readme    对候选清单（活跃榜+新锐+本周解读）拉 README → readmes.json
  3. ai        每项目 100 字 AI 解读 + 本周解读四维分析（带缓存）→ ai_reviews.json
  4. render    组装三板块周报 Markdown → weekly/report.md

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


def _load_candidate_pool(date: str) -> list[dict[str, Any]]:
    """读当日候选池（run_daily 产出）。不存在则报错退出。"""
    pool = storage.load_snapshot_pool(date)
    if not pool:
        log.error("当日候选池不存在或为空：%s\n请先跑 `python run_daily.py` 完成每日采集。", date)
        sys.exit(2)
    return pool


def _to_row(it: dict[str, Any], cat: str, db: str, growth: Any) -> dict[str, Any]:
    """把项目 + 分类/适用数据库/增长打成 render 用的 row。"""
    return {
        "full_name": _full(it),
        "html_url": it.get("html_url", "#"),
        "category": cat,
        "databases": db,
        "growth": growth,
        "description": it.get("description") or "",
        "star": it.get("stargazers_count", 0),
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

    # 板块归属 + 分类 + 适用数据库 + 排除（内核 + SOP §3.3）
    items_by_sec: dict[str, list[dict[str, Any]]] = {s: [] for s in SECTION_ORDER}
    meta_map: dict[str, tuple[str, str]] = {}  # full_name -> (category, databases)
    excluded_kernel = excluded_sop = 0
    for it in display_pool:
        full = _full(it)
        if reg.is_kernel(full):
            excluded_kernel += 1
            continue
        if sections.should_exclude_sop(it):
            excluded_sop += 1
            continue
        sec = sections.assign_section(it)
        if sec not in items_by_sec:
            continue
        cat = sections.infer_category(it)
        db = sections.infer_databases(it)
        items_by_sec[sec].append(it)
        meta_map[full] = (cat, db)
    log.info(
        "板块归属：国外 %d / 国产 %d / AI %d（剔除内核 %d、SOP排除 %d）",
        len(items_by_sec["国外数据库"]), len(items_by_sec["国产数据库"]),
        len(items_by_sec["AI工具"]), excluded_kernel, excluded_sop,
    )

    sections_out: list[dict[str, Any]] = []
    interpreted: set[str] = set()
    for key in SECTION_ORDER:
        items = items_by_sec[key]
        active = analytics.section_active_top(items, star_deltas)
        active_fulls = {_full(it) for it in active}
        newcomers = analytics.section_newcomers(items, star_deltas, exclude=active_fulls)
        focus = analytics.pick_section_focus(active, interpreted)
        if focus:
            interpreted.add(_full(focus))

        def _rows(seq: list[dict[str, Any]]) -> list[dict[str, Any]]:
            out = []
            for it in seq:
                cat, db = meta_map.get(_full(it), ("其他", "待确认"))
                out.append(_to_row(it, cat, db, star_deltas.get(_full(it))))
            return out

        focus_row = None
        if focus:
            cat, db = meta_map.get(_full(focus), ("其他", "待确认"))
            focus_row = _to_row(focus, cat, db, star_deltas.get(_full(focus)))

        sections_out.append({
            "key": key,
            "active": _rows(active),
            "newcomers": _rows(newcomers),
            "focus": focus_row,
        })
        log.info(
            "  %s：活跃 %d、新锐 %d、解读 %s",
            key, len(active), len(newcomers),
            _full(focus) if focus else "无",
        )

    # 附录总榜 Top5（内核已在上面剔除；带板块+分类）
    tb_pool = [it for it in display_pool
               if not reg.is_kernel(_full(it)) and not sections.should_exclude_sop(it)]
    topboard_items = analytics.global_topboard(tb_pool)
    topboard = []
    for it in topboard_items:
        full = _full(it)
        sec = sections.assign_section(it) or "国外数据库"
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
        "snapshot_date": config.TODAY_HUMAN,
        "first_period": diffs["first_period"],
        "prev_date": prev_date,
        "sections": sections_out,
        "topboard": topboard,
    }
    storage.save_weekly_meta("sections", data, date)
    return data


def _candidate_fulls(sections_data: dict[str, Any]) -> list[str]:
    """收集需要拉 README + AI 解读的候选（活跃榜+新锐+本周解读，去重保序）。"""
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
# 阶段 3：ai（每项目 100 字解读 + 四维分析，带缓存）
# ============================================================
def stage_ai(
    date: str,
    sections_data: dict[str, Any],
    pool: list[dict[str, Any]],
    readmes: dict[str, str],
    resume: bool,
) -> dict[str, Any]:
    """生成 AI 解读 → weekly/meta/ai_reviews.json（key=full_name，断点续采）。"""
    log.info("==== 阶段3：AI 解读（100 字 + 四维）====")
    cache: dict[str, Any] = {}
    if resume:
        existing = storage.load_weekly_meta("ai_reviews", date)
        if isinstance(existing, dict):
            cache = existing
    brief_cache: dict[str, str] = dict(cache.get("brief") or {})
    four_cache: dict[str, dict[str, str]] = dict(cache.get("four") or {})

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

    # 100 字解读（活跃榜+新锐+本周解读全部）
    done_brief = 0
    for fn in candidates:
        if fn in brief_cache:
            continue
        it = pool_map.get(fn, {"full_name": fn, "description": "", "topics": []})
        cat, db = _meta_for(sections_data, fn)
        brief_cache[fn] = ai.brief_review(it, cat, db, readmes.get(fn))
        done_brief += 1
        log.info("  解读 ✓ %-40s (%d/%d)", fn, done_brief, len(candidates))

    # 四维分析（本周解读项目）
    done_four = 0
    for fn in focus_fulls:
        if fn in four_cache:
            continue
        it = pool_map.get(fn, {"full_name": fn, "description": "", "topics": []})
        cat, db = _meta_for(sections_data, fn)
        four_cache[fn] = ai.four_dimension_analysis(it, cat, db, readmes.get(fn))
        done_four += 1
        log.info("  四维 ✓ %-40s (%d/%d)", fn, done_four, len(focus_fulls))

    out = {
        "snapshot_date": config.TODAY_HUMAN,
        "brief": brief_cache,
        "four": four_cache,
    }
    storage.save_weekly_meta("ai_reviews", out, date)
    log.info("AI 解读完成：brief %d、four %d（已落盘 ai_reviews.json）",
             len(brief_cache), len(four_cache))
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
    log.info("==== 阶段4：渲染（三板块周报）====")
    brief = (ai_reviews or {}).get("brief") or {}
    four = (ai_reviews or {}).get("four") or {}

    # 把 AI 解读/四维并入 sections
    for sec in sections_data.get("sections", []):
        for row in (sec.get("active") or []) + (sec.get("newcomers") or []):
            fn = row.get("full_name", "")
            row["review"] = brief.get(fn, "")
        f = sec.get("focus")
        if f:
            f["four"] = four.get(f.get("full_name", ""), {})

    report_md = render.render_main_report(sections_data)
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
    if only in (None, "compute", "readme", "ai", "render"):
        if only in (None, "compute"):
            sections_data = stage_compute(display_pool, date, prev_date)
        else:
            sections_data = storage.load_weekly_meta("sections", date)
            if not isinstance(sections_data, dict) or not sections_data.get("sections"):
                log.error("缺少 compute 结果（sections.json）。请先跑 `--only compute` 或全流程。")
                sys.exit(2)

    # ---- readme ----
    readmes: dict[str, str] = {}
    if only in (None, "readme", "ai"):
        candidates = _candidate_fulls(sections_data)
        if only in (None, "readme"):
            readmes = stage_readme(date, candidates, resume)
        else:
            rdata = storage.load_weekly_meta("readmes", date)
            readmes = (rdata or {}).get("by_repo") if isinstance(rdata, dict) else {}
            readmes = {k: v for k, v in (readmes or {}).items() if v}

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
        print(f"  采集日：{config.TODAY_HUMAN} ({date})  基准：{prev_date or '无(首期)'}")
        print("=" * 56)

    elapsed = time.time() - start
    log.info("==== 周报生产完成（耗时 %.1f 分钟）====", elapsed / 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="数据库开源生态周报 · 周报生产（新 SOP 三板块，对标 run_daily.py）"
    )
    parser.add_argument(
        "--only",
        choices=["compute", "readme", "ai", "render"],
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
