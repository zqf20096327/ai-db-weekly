"""周报渲染层 —— 主周报 + 工具合辑周报 两套渲染（纯函数）。

每个函数返回一段 Markdown 字符串。全部纯函数（不调网络、不读写文件）。

两套产物：
  - report.md  主周报：导语→精选解读→工具速递→新生→Top→License（按重要性切片）
  - toolkit.md 工具合辑周报：六类工具体检→新晋→静默→类目趋势（按类目切片）

设计依据：编辑策展型漏斗结构 + DBA 工具视角 + 数据边界（内核以厂商为准）。
"""

from __future__ import annotations

from typing import Any

import config
import templates as T
import tool_registry as reg
from ai_client import AIClient

# 榜单归属 key → 中文（cross_ref "见XX榜"用）
_SECTION_CN = {
    "focus": "🔍精选解读",
    "new": "🆕新生项目",
    "rising": "①快速上涨",
    "ai": "🤖AI 能力",
    "topboard": "Top 总榜",
}


# ============================================================
# 辅助
# ============================================================
def _star_k(num: int | None) -> str:
    """star 格式化为带 k（如 40385 → 40.4k）。"""
    if num is None:
        return "—"
    if num >= 1000:
        return f"{num / 1000:.1f}k"
    return str(num)


def _short_name(full: str) -> str:
    """full_name 取 repo 部分（如 pingcap/tidb → tidb）。"""
    return full.split("/", 1)[1] if "/" in full else full


def _md_escape_cell(s: str) -> str:
    """表格单元格转义（去换行/管道），不截断。"""
    return (s or "").replace("\n", " ").replace("|", "/").strip()


def _date_only(iso: str | None) -> str:
    """ISO 日期取 YYYY-MM-DD；缺失返回 —。"""
    if not iso:
        return "—"
    return str(iso)[:10]


def _category_cn(item: dict[str, Any]) -> str:
    """品类中文（⑤总榜品类列）。工具 / 内核 / AI。"""
    full = item.get("full_name", "")
    if reg.is_kernel(full):
        return "内核"
    cats = item.get("category") or []
    if isinstance(cats, list) and "ai" in cats:
        return "AI"
    return "工具"


def _latest_release_per_repo(
    releases: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """聚合：每 repo 只留 published_at 最新的一条 release。"""
    latest: dict[str, dict[str, Any]] = {}
    for rel in releases:
        full = rel.get("repo_full_name", "")
        if not full:
            continue
        cur = latest.get(full)
        if cur is None or (rel.get("published_at") or "") > (cur.get("published_at") or ""):
            latest[full] = rel
    return latest


# ============================================================
# 主周报 (report.md)
# ============================================================
def render_main_report(
    snapshot_date: str,
    pool: list[dict[str, Any]],
    diffs: dict[str, Any],
    releases: list[dict[str, Any]],
    license_summary: dict[str, Any],
    new_projects: list[dict[str, Any]],
    attribution: dict[str, str],
    readmes: dict[str, str] | None = None,
    issue_no: int = 0,
) -> str:
    """渲染主周报全文。

    参数说明：
      pool       展示池（已过滤）
      diffs      diff_snapshots 结果
      releases   本周 release 列表
      license_summary  license 变更检测结果
      new_projects     新生项目列表
      attribution      榜单归属（assign_main_section 结果）
      readmes          {full_name: readme_text}（精选解读 AI 用）
    """
    pool_map = {it.get("full_name", ""): it for it in pool}
    star_deltas = diffs.get("star_deltas", {})
    new_entries = set(diffs.get("new_entries", []))
    latest_rel = _latest_release_per_repo(releases)

    # ---- 导语 ----
    intro = _render_main_intro(snapshot_date, star_deltas, new_entries, latest_rel, license_summary)

    # ---- 精选解读 ----
    focus, focus_fulls = _render_main_focus(pool_map, star_deltas, latest_rel, readmes or {})

    # ---- 工具动态速递 ----
    digest = _render_main_digest(pool_map, star_deltas, latest_rel, focus_fulls)

    # ---- 新生项目 ----
    new_sec = _render_main_new(new_projects)

    # ---- Top 总榜 ----
    topboard = _render_main_topboard(pool, star_deltas, attribution)

    # ---- License ----
    license_sec = _render_main_license(license_summary)

    # ---- 关于 ----
    meta = _render_main_meta(snapshot_date)

    parts = [
        f"> **{T.REPORT_NAME} · 第 {issue_no or 'N'} 期**\n{T.MAIN_SLOGAN}\n> _{snapshot_date}_\n",
        f"{T.DATA_BOUNDARY}\n> 📌 **配套阅读**：本期 [**运维工具合辑周报**]({T.TOOLKIT_LINK})"
        "（6 类工具本周动态体检）\n\n---\n",
        f"\n## {T.MAIN_SECTIONS['intro']}\n\n{intro}\n",
        f"\n## {T.MAIN_SECTIONS['focus']}\n\n{focus}\n",
        f"\n## {T.MAIN_SECTIONS['digest']}\n\n{digest}\n",
        f"\n## {T.MAIN_SECTIONS['new']}\n\n{new_sec}\n",
        f"\n## {T.MAIN_SECTIONS['topboard']}\n\n{topboard}\n",
        f"\n## {T.MAIN_SECTIONS['license']}\n\n{license_sec}\n",
        f"\n## {T.MAIN_SECTIONS['meta']}\n\n{meta}\n",
        f"\n---\n\n**🗂️ 往期回顾 ｜ 👍 点赞 + 在看 ｜ 🔔 关注「{T.REPORT_NAME}」**\n",
    ]
    return "\n".join(parts).rstrip() + "\n"


def _render_main_intro(
    snapshot_date: str,
    star_deltas: dict[str, int],
    new_entries: set[str],
    latest_rel: dict[str, dict[str, Any]],
    license_summary: dict[str, Any],
) -> str:
    """导语：客观陈述本周异常事件（异常上涨/新入榜/发版/License）。"""
    if diffs_first := not star_deltas:
        return "本期为创刊号，先建立数据基线，动态栏目自第 02 期起完整。"

    # 异常上涨（≥阈值，剔除内核）
    anomaly = sorted(
        ((fn, d) for fn, d in star_deltas.items()
         if d >= config.ANOMALY_RISE_STAR and not reg.is_kernel(fn)),
        key=lambda x: x[1], reverse=True,
    )
    # 工具发版数（剔除内核）
    tool_releases = [fn for fn in latest_rel if not reg.is_kernel(fn)]
    changed = license_summary.get("changed", []) if license_summary else []

    lines = []
    if anomaly:
        names = "、".join(f"{_short_name(fn)}（+{d}）" for fn, d in anomaly[:5])
        lines.append(f"本周 star 异常上涨（≥{config.ANOMALY_RISE_STAR}）{len(anomaly)} 个：{names}。")
    if new_entries:
        tool_new = [fn for fn in new_entries if not reg.is_kernel(fn)]
        if tool_new:
            lines.append(f"新入榜工具 {len(tool_new)} 个。")
    lines.append(f"本周 {len(tool_releases)} 个工具发版。")
    if changed:
        lines.append(f"License 变更 {len(changed)} 个项目。")
    else:
        lines.append("无 License 变更。")
    lines.append("详见下方各栏。")
    return "\n".join(lines)


def _select_focus_candidates(
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
) -> list[str]:
    """精选候选选择：异常上涨(≥100) ∩ 有发版，不足时降级补发版+star头部。"""
    # 候选：异常上涨 ∩ 有发版（剔除内核）
    anomaly_set = {fn for fn, d in star_deltas.items() if d >= config.ANOMALY_RISE_STAR}
    candidates = [fn for fn in anomaly_set & set(latest_rel) if not reg.is_kernel(fn)]
    candidates.sort(key=lambda fn: star_deltas.get(fn, 0), reverse=True)

    # 不足则降级补：有发版 + star 头部
    if len(candidates) < config.FOCUS_DEEPDIVE_COUNT:
        extra = [fn for fn in latest_rel if fn not in candidates and not reg.is_kernel(fn)]
        extra.sort(key=lambda fn: pool_map.get(fn, {}).get("stargazers_count", 0), reverse=True)
        candidates.extend(extra[: config.FOCUS_DEEPDIVE_COUNT - len(candidates)])

    return candidates[: config.FOCUS_DEEPDIVE_COUNT]


def _render_main_focus(
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
    readmes: dict[str, str],
) -> tuple[str, set[str]]:
    """精选解读：异常上涨 ∩ 有发版 的工具，AI 基于 README 深度点评。

    返回 (markdown, focus_fulls) —— focus_fulls 供速递栏去重用。
    """
    candidates = _select_focus_candidates(pool_map, star_deltas, latest_rel)
    if not candidates:
        return "_（本周无满足精选条件的工具；待 release/diff 数据完整后自动选出。）_\n", set()

    ai = AIClient()
    parts = []
    focus_fulls: set[str] = set()
    for i, fn in enumerate(candidates, 1):
        focus_fulls.add(fn)
        item = pool_map.get(fn, {})
        star = item.get("stargazers_count", 0)
        delta = star_deltas.get(fn, 0)
        rel = latest_rel.get(fn, {})
        tag = rel.get("tag_name", "")
        url = item.get("html_url", "#")
        rel_url = rel.get("html_url", "#")

        title = f"{_short_name(fn)} {tag}" if tag else _short_name(fn)
        parts.append(f"### {i}. {title}\n")
        parts.append(
            f"[{fn}]({url}) · ⭐ {_star_k(star)}"
            + (f"（+{delta}）" if delta else "")
            + (f" · [发版说明]({rel_url})\n" if rel_url else "\n")
        )
        # AI 点评：基于 README 全文 + release notes
        body = rel.get("body")
        readme_text = readmes.get(fn)
        what, why = ai.focus_tool_review(item, body, tag, readme_text=readme_text)
        if what:
            parts.append(f"**发生了什么**：{what}\n")
        if why:
            parts.append(f"**为什么值得关注**：{why}\n")
    return "\n".join(parts) + "\n", focus_fulls


def _render_main_digest(
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
    focus_fulls: set[str],
) -> str:
    """工具动态速递：本周有发版/活跃/涨星的工具，每条一句话。剔除内核+精选项目。"""
    rows: list[tuple[str, str, int, int, bool]] = []
    for fn, item in pool_map.items():
        if reg.is_kernel(fn) or fn in focus_fulls:
            continue
        if not reg.is_tool(fn):
            continue
        star = item.get("stargazers_count", 0)
        delta = star_deltas.get(fn, 0)
        c7 = item.get("commit_count_7d", 0) or 0
        has_rel = fn in latest_rel
        if not (has_rel or c7 >= config.DYNAMIC_COMMIT_MIN or delta > config.DYNAMIC_STAR_MIN):
            continue
        rows.append((fn, item.get("html_url", "#"), star, delta, c7, has_rel))

    # 排序：有发版优先，然后按综合(涨幅+活跃)
    rows.sort(key=lambda r: (r[5], r[3] + r[4]), reverse=True)

    if not rows:
        return f"{T.DIGEST_NOTE}\n\n_（本周无工具动态。）_\n"

    lines = [T.DIGEST_NOTE, ""]
    for fn, url, star, delta, c7, has_rel in rows[: config.TOOL_DIGEST_LIMIT]:
        flags = []
        if has_rel:
            tag = latest_rel[fn].get("tag_name", "")
            flags.append(f"🏷️ `{tag}`" if tag else "🏷️发版")
        if c7 >= config.DYNAMIC_COMMIT_MIN:
            flags.append(f"🔥{c7}c")
        if delta > config.DYNAMIC_STAR_MIN:
            flags.append(f"📈+{delta}")
        desc = _md_escape_cell(pool_map[fn].get("description", ""))
        flag_str = " ".join(flags)
        lines.append(f"- {flag_str} **[{fn}]({url})** — {desc}（⭐ {_star_k(star)}）")
    return "\n".join(lines) + "\n"


def _render_main_new(new_projects: list[dict[str, Any]]) -> str:
    """新生项目：潜力榜 + 新星榜，各 top5。"""
    out = [T.NEW_NOTE + "\n"]
    potential = [p for p in new_projects if p.get("new_tier") == "potential"]
    rising = [p for p in new_projects if p.get("new_tier") == "rising"]

    # 潜力榜
    out.append("### 🌟 潜力榜（star ≥ 30，已发酵）\n")
    out.append("| 项目 | 作用 | Star | 创建日 |")
    out.append("|---|---|---:|---|")
    for p in potential[: config.NEW_LIST_LIMIT]:
        role = _md_escape_cell(p.get("description", ""))
        out.append(
            f"| [{p.get('full_name', '')}]({p.get('html_url', '#')}) "
            f"| {role} | {p.get('stargazers_count', 0)} "
            f"| {_date_only(p.get('created_at'))} |"
        )

    # 新星榜
    out.append(f"\n### 🆕 新星榜（star 3 ~ 30，早期观察）\n\n{T.NEW_RISING_NOTE}\n")
    out.append("| 项目 | 作用 | Star |")
    out.append("|---|---|---:|")
    for p in rising[: config.NEW_LIST_LIMIT]:
        role = _md_escape_cell(p.get("description", ""))
        out.append(
            f"| [{p.get('full_name', '')}]({p.get('html_url', '#')}) "
            f"| {role} | {p.get('stargazers_count', 0)} |"
        )
    return "\n".join(out) + "\n"


def _render_main_topboard(
    pool: list[dict[str, Any]],
    star_deltas: dict[str, int],
    attribution: dict[str, str],
) -> str:
    """Top 总榜：star 降序 top10（排除内核）+ 作用。"""
    out = [T.TOPBOARD_NOTE + "\n"]
    out.append("| 排名 | 项目 | Star | 作用 |")
    out.append("|:--:|---|---:|---|")
    # 排除内核：内核 star 排名以厂商官方为准，不在此列
    tools_only = [it for it in pool if not reg.is_kernel(it.get("full_name", ""))]
    sorted_pool = sorted(tools_only, key=lambda x: x.get("stargazers_count", 0), reverse=True)
    for i, it in enumerate(sorted_pool[: config.TOPBOARD_LIMIT], 1):
        full = it.get("full_name", "")
        desc = _md_escape_cell(it.get("description", ""))
        out.append(
            f"| {i} | [{full}]({it.get('html_url', '#')}) "
            f"| {_star_k(it.get('stargazers_count'))} | {desc} |"
        )
    out.append(f"\n📎 来源:[GitHub API](https://api.github.com)\n")
    return "\n".join(out)


def _render_main_license(license_summary: dict[str, Any]) -> str:
    """License 雷达：有变更展开，无变更一句话。"""
    changed = (license_summary or {}).get("changed", [])
    if not changed:
        return T.LICENSE_EMPTY + "\n"
    out = [f"> ⚠️ 本周检测到 **{len(changed)}** 个项目 LICENSE 文件变更：\n"]
    out.append("| 项目 | 变更时间 | 变更者 | 提交信息 |")
    out.append("|---|---|---|---|")
    for c in changed[:20]:
        repo = c.get("repo_full_name", "")
        ch = (c.get("changes") or [{}])[0]
        out.append(
            f"| {repo} | {_date_only(ch.get('changed_at'))} "
            f"| {ch.get('changed_by', '')} | {_md_escape_cell(ch.get('message', ''))} |"
        )
    return "\n".join(out) + "\n"


def _render_main_meta(snapshot_date: str) -> str:
    """关于本报告：统计口径 + 数据说明 + 配套阅读。"""
    meta = T.MAIN_META.format(date=snapshot_date)
    return (
        meta + "\n\n"
        f"**📂 配套阅读**\n"
        f"- 本期 [**运维工具合辑周报**]({T.TOOLKIT_LINK})："
        "6 类工具本周动态体检、新晋工具、静默观察、类目趋势（发布后替换为链接）"
    )


# ============================================================
# 工具合辑周报 (toolkit.md)
# ============================================================
def render_toolkit_report(
    snapshot_date: str,
    pool: list[dict[str, Any]],
    diffs: dict[str, Any],
    releases: list[dict[str, Any]],
    issue_no: int = 0,
) -> str:
    """渲染工具合辑周报全文。"""
    pool_map = {it.get("full_name", ""): it for it in pool}
    star_deltas = diffs.get("star_deltas", {})
    latest_rel = _latest_release_per_repo(releases)

    # 计算每个标杆工具的动态状态
    tool_status = _compute_tool_status(pool_map, star_deltas, latest_rel)

    intro = _render_toolkit_intro(tool_status, pool_map, star_deltas, latest_rel)
    checkup = _render_toolkit_checkup(tool_status, pool_map, star_deltas, latest_rel)
    newcomer = _render_toolkit_newcomer(pool_map, star_deltas, latest_rel)
    silent = _render_toolkit_silent(tool_status)
    trend = _render_toolkit_trend(tool_status, star_deltas)
    meta = _render_toolkit_meta(snapshot_date)

    parts = [
        f"> **数据库运维工具合辑 · 第 {issue_no or 'N'} 期**\n{T.TOOLKIT_SLOGAN}\n> _{snapshot_date}_\n",
        f"> 📌 配套阅读：本期 [**主周报**]({T.MAIN_LINK})"
        "（含精选解读、新生项目、Top 总榜）\n"
        f"{T.DATA_BOUNDARY}\n\n---\n",
        f"\n## {T.TOOLKIT_SECTIONS['intro']}\n\n{intro}\n",
        f"\n## {T.TOOLKIT_SECTIONS['checkup']}\n\n{checkup}\n",
        f"\n## {T.TOOLKIT_SECTIONS['newcomer']}\n\n{newcomer}\n",
        f"\n## {T.TOOLKIT_SECTIONS['silent']}\n\n{silent}\n",
        f"\n## {T.TOOLKIT_SECTIONS['trend']}\n\n{trend}\n",
        f"\n## {T.TOOLKIT_SECTIONS['meta']}\n\n{meta}\n",
        f"\n---\n\n**🗂️ 往期合辑 ｜ 👍 点赞 + 在看 ｜ 🔔 关注「{T.REPORT_NAME}」**\n",
    ]
    return "\n".join(parts).rstrip() + "\n"


def _compute_tool_status(
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """计算每个标杆工具的本周动态状态。

    返回 {full_name: {has_release, commit_7d, star_delta, is_dynamic, category}}
    """
    status: dict[str, dict[str, Any]] = {}
    for cat, fns in reg.BENCHMARK_TOOLS.items():
        for fn in fns:
            item = pool_map.get(fn, {})
            c7 = item.get("commit_count_7d", 0) or 0
            delta = star_deltas.get(fn, 0)
            has_rel = fn in latest_rel
            is_dynamic = (
                has_rel
                or c7 >= config.DYNAMIC_COMMIT_MIN
                or delta > config.DYNAMIC_STAR_MIN
            )
            status[fn] = {
                "has_release": has_rel,
                "commit_7d": c7,
                "star_delta": delta,
                "is_dynamic": is_dynamic,
                "category": cat,
                "star": item.get("stargazers_count", 0),
            }
    return status


def _format_change_flags(st: dict[str, Any], latest_rel: dict[str, dict[str, Any]], fn: str) -> str:
    """格式化工具的本周变化标记（🏷️发版 🔥活跃 📈涨星）。"""
    flags = []
    if st["has_release"]:
        tag = latest_rel.get(fn, {}).get("tag_name", "")
        flags.append(f"🏷️{tag}" if tag else "🏷️发版")
    if st["commit_7d"] >= config.DYNAMIC_COMMIT_MIN:
        flags.append(f"🔥{st['commit_7d']}c")
    if st["star_delta"] > config.DYNAMIC_STAR_MIN:
        flags.append(f"📈+{st['star_delta']}")
    return " ".join(flags) if flags else "— 静默"


def _render_toolkit_intro(
    tool_status: dict[str, dict[str, Any]],
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
) -> str:
    """工具合辑导语：动态数/静默数/各类活跃度概述/新晋提示。"""
    total = len(tool_status)
    dynamic_count = sum(1 for s in tool_status.values() if s["is_dynamic"])
    silent_count = total - dynamic_count

    # 各类动态数
    cat_dynamic: dict[str, int] = {}
    cat_total: dict[str, int] = {}
    for st in tool_status.values():
        cat = st["category"]
        cat_total[cat] = cat_total.get(cat, 0) + 1
        if st["is_dynamic"]:
            cat_dynamic[cat] = cat_dynamic.get(cat, 0) + 1

    # 最活跃的类目
    most_active = max(cat_dynamic.items(), key=lambda x: x[1]) if cat_dynamic else ("—", 0)
    # 最静默的类目
    silent_rates = {c: cat_total[c] - cat_dynamic.get(c, 0) for c in cat_total}
    most_silent = max(silent_rates.items(), key=lambda x: x[1]) if silent_rates else ("—", 0)

    # 新晋工具数
    newcomer_count = len(_find_newcomers(pool_map, star_deltas, latest_rel))

    lines = [
        f"本周 {total} 个标杆工具中 **{dynamic_count} 个有动态**"
        f"（发版/活跃/涨星），{silent_count} 个静默。"
    ]
    if most_active[1] > 0:
        lines.append(f"{most_active[0]}类最活跃（{most_active[1]} 个有动态）；")
    if most_silent[1] > 0:
        lines.append(f"{most_silent[0]}类整体偏静默（{most_silent[1]} 个静默）。")
    if newcomer_count:
        lines.append(f"此外，{newcomer_count} 个本周高热度工具此前不在标杆清单，本期起纳入观察。")
    return "".join(lines) + "\n"


def _render_toolkit_checkup(
    tool_status: dict[str, dict[str, Any]],
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
) -> str:
    """六类工具体检：每类一张表，动态在前静默在后。"""
    out = [T.CHECKUP_NOTE + "\n"]
    for cat, fns in reg.BENCHMARK_TOOLS.items():
        # 该类工具按"动态优先，star 降序"排
        items = []
        for fn in fns:
            st = tool_status.get(fn, {})
            star = pool_map.get(fn, {}).get("stargazers_count", 0) or st.get("star", 0)
            items.append((fn, st, star))
        # 动态在前，同状态按 star 降序
        items.sort(key=lambda x: (not x[1]["is_dynamic"], -x[2]))

        dyn = sum(1 for _, st, _ in items if st["is_dynamic"])
        sil = len(items) - dyn
        out.append(f"### {cat} — 本周 {dyn} 动态 / {sil} 静默\n")
        out.append("| 项目 | Star | 本周变化 | 状态 | 作用 |")
        out.append("|---|---:|---|---|---|")
        for fn, st, star in items:
            change = _format_change_flags(st, latest_rel, fn)
            status_cn = "静默" if not st["is_dynamic"] else (
                "发版" if st["has_release"] else ("活跃" if st["commit_7d"] >= config.DYNAMIC_COMMIT_MIN else "涨星")
            )
            item = pool_map.get(fn, {})
            url = item.get("html_url", "#")
            desc = _md_escape_cell(item.get("description", ""))
            out.append(f"| [{fn}]({url}) | {_star_k(star)} | {change} | {status_cn} | {desc} |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _find_newcomers(
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    """找出不在标杆清单、但本周"有发版 或 star涨幅≥NEWCOMER_STAR_MIN"的工具。

    额外过滤：剔除应用模板/ORM/驱动等"用了数据库但本身非 DBA 工具"的项目
    （fastapi-template/nocodb/prisma 等，靠关键词与已知名单排除）。
    """
    # 非运维工具的关键词（description 命中即剔除新晋候选）
    NON_OPS_KW = [
        "template", "full stack", "full-stack", "orm", "airtable alternative",
        "headless cms", "application", "starter", "boilerplate",
    ]
    newcomers: list[tuple[str, dict[str, Any]]] = []
    for fn, item in pool_map.items():
        if fn in reg.ALL_BENCHMARK or reg.is_kernel(fn):
            continue
        if not reg.is_tool(fn):
            continue
        desc = (item.get("description") or "").lower()
        if any(kw in desc for kw in NON_OPS_KW):
            continue
        has_rel = fn in latest_rel
        delta = star_deltas.get(fn, 0)
        if has_rel or delta >= config.NEWCOMER_STAR_MIN:
            newcomers.append((fn, item))
    # 按 star 降序
    newcomers.sort(key=lambda x: x[1].get("stargazers_count", 0), reverse=True)
    return newcomers


def _render_toolkit_newcomer(
    pool_map: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
    latest_rel: dict[str, dict[str, Any]],
) -> str:
    """本周新晋工具：不在标杆但本周冒头的。"""
    newcomers = _find_newcomers(pool_map, star_deltas, latest_rel)
    if not newcomers:
        return f"{T.NEWCOMER_NOTE}\n\n_（本周无新晋工具。）_\n"

    out = [T.NEWCOMER_NOTE + "\n"]
    out.append("| 项目 | Star | 本周变化 | 归类 | 作用 |")
    out.append("|---|---:|---|---|---|")
    for fn, item in newcomers[:8]:
        star = item.get("stargazers_count", 0)
        delta = star_deltas.get(fn, 0)
        c7 = item.get("commit_count_7d", 0) or 0
        has_rel = fn in latest_rel
        flags = []
        if has_rel:
            tag = latest_rel[fn].get("tag_name", "")
            flags.append(f"🏷️{tag}" if tag else "🏷️发版")
        if c7 >= config.DYNAMIC_COMMIT_MIN:
            flags.append(f"🔥{c7}c")
        if delta > config.DYNAMIC_STAR_MIN:
            flags.append(f"📈+{delta}")
        # 归类：用标杆类目关键词粗判，否则"AI 工具"或"其他"
        cat = _guess_newcomer_category(item)
        desc = _md_escape_cell(item.get("description", ""))
        # 标注深度解读在主周报
        cross = "（深度解读见主周报）" if delta >= config.ANOMALY_RISE_STAR else ""
        out.append(
            f"| [{fn}]({item.get('html_url', '#')}) | {_star_k(star)} "
            f"| {' '.join(flags)} | {cat} | {desc}{cross} |"
        )
    return "\n".join(out) + "\n"


def _guess_newcomer_category(item: dict[str, Any]) -> str:
    """粗判新晋工具归类（token 匹配，后续可换 AI 读 README）。

    用词边界匹配（避免 "ha" 命中 "share"/"hostable" 等子串误判）。
    """
    import re

    desc = (item.get("description") or "").lower()
    topics = " ".join(str(t).lower() for t in (item.get("topics") or []))
    hay = f"{desc} {topics}"
    toks = set(re.findall(r"[a-z0-9-]+", hay))

    cat_tokens = {
        "连接池/代理": {"proxy", "pooler", "shard", "sharding", "bastion", "connection-pool"},
        "高可用/容灾": {"failover", "high-availability", "replication", "cluster"},
        "迁移/变更": {"migration", "migrate", "schema", "ddl", "migrations"},
        "备份/恢复": {"backup", "restore", "dump", "recovery", "pitr"},
        "监控/诊断": {"monitor", "monitoring", "performance", "observability", "metrics"},
        "管理客户端": {"workbench", "studio", "explorer", "browser", "ide"},
    }
    for cat, tokens in cat_tokens.items():
        if toks & tokens:
            return cat
    # "client" 单独判（范围宽，放最后避免 ORM 误命中）
    if {"client", "gui", "sql-client"} & toks:
        return "管理客户端"
    cats = item.get("category") or []
    return "AI 工具" if (isinstance(cats, list) and "ai" in cats) else "其他"


def _render_toolkit_silent(tool_status: dict[str, dict[str, Any]]) -> str:
    """静默观察：本周无发版/commit/涨星的标杆工具。"""
    out = [T.SILENT_NOTE + "\n"]
    silent = [fn for fn, st in tool_status.items() if not st["is_dynamic"]]
    if not silent:
        out.append("_（本周无静默工具。）_\n")
        return "\n".join(out)

    # 按类目分组
    by_cat: dict[str, list[str]] = {}
    for fn in silent:
        cat = tool_status[fn]["category"]
        by_cat.setdefault(cat, []).append(fn)
    for cat, fns in by_cat.items():
        out.append(f"**{cat}**：{' · '.join(fns)}")
    total = len(tool_status)
    rate = len(silent) / total * 100 if total else 0
    out.append(f"\n> 📊 本周静默率 {len(silent)}/{total}（{rate:.0f}%）。")
    # 静默率最高的类目
    cat_silent = {c: len(fns) for c, fns in by_cat.items()}
    if cat_silent:
        worst = max(cat_silent.items(), key=lambda x: x[1])
        cat_total = sum(1 for s in tool_status.values() if s["category"] == worst[0])
        if cat_total:
            out.append(f"{worst[0]}类静默率最高（{worst[1]}/{cat_total}）。")
    return "\n".join(out) + "\n"


def _render_toolkit_trend(
    tool_status: dict[str, dict[str, Any]],
    star_deltas: dict[str, int],
) -> str:
    """类目趋势速览：各类工具数/动态数/静默数/star净增合计。"""
    # 按配置的类目顺序
    cat_order = list(reg.BENCHMARK_TOOLS.keys())
    rows = []
    for cat in cat_order:
        fns = reg.BENCHMARK_TOOLS[cat]
        in_pool = [fn for fn in fns if fn in tool_status]
        dyn = sum(1 for fn in in_pool if tool_status[fn]["is_dynamic"])
        sil = len(in_pool) - dyn
        star_sum = sum(star_deltas.get(fn, 0) for fn in in_pool)
        rows.append((cat, len(in_pool), dyn, sil, star_sum))

    out = ["| 类目 | 工具数 | 本周动态 | 静默 | 类目 star 净增 |", "|---|:--:|:--:|:--:|---:|"]
    for cat, n, dyn, sil, ss in rows:
        out.append(f"| {cat} | {n} | {dyn} | {sil} | {'+' if ss >= 0 else ''}{ss} |")
    total_n = sum(r[1] for r in rows)
    total_dyn = sum(r[2] for r in rows)
    total_sil = sum(r[3] for r in rows)
    total_ss = sum(r[4] for r in rows)
    out.append(f"| **合计** | **{total_n}** | **{total_dyn}** | **{total_sil}** | **{'+' if total_ss >= 0 else ''}{total_ss}** |")
    return "\n".join(out) + "\n"


def _render_toolkit_meta(snapshot_date: str) -> str:
    """关于本期：统计口径 + 相关阅读。"""
    meta = T.TOOLKIT_META.format(
        date=snapshot_date, star_min=config.DYNAMIC_STAR_MIN
    )
    return (
        meta + "\n\n"
        f"**📎 相关阅读**\n"
        f"- 本期 [**主周报**]({T.MAIN_LINK})：精选解读、新生项目、Top 总榜、License 雷达"
    )
