"""周报渲染层 —— 新 SOP 三板块周报（纯函数）。

每个函数返回一段 Markdown 字符串。全部纯函数（不调网络、不读写文件）。

产物：
  - report.md  三板块周报：DBA速览 + 国外/国产/AI 三板块
    （每板块：活跃榜 Top3 + 新锐发现 + 本周解读三维，均为卡片形式）
    + Top 总榜（表格）+ 互动说明

板块范围口径（2026-08-14）：范围外数据库项目不进周报（compute 层闸门保证）；
板块一/二不含 AI 项目；AI 解读中性客观 ≤80 字；本周解读三段各 ≤100 字。

设计依据：deepseek SOP 文本 §5.1 输出模板 + §3.6/3.7/4.4/4.5 + 用户板块口径。
数据由 run_weekly 的 compute/ai 阶段组装成 report_data，本模块只负责格式化。
"""

from __future__ import annotations

from typing import Any

import config
import templates as T

# 三板块元数据（顺序 = 报告展示顺序：国外 → 国产 → AI）
SECTION_META = {
    "国外数据库": {
        "emoji": "🗄️",
        "title": "板块一 · 国际主流数据库",
        "intro": (
            f"范围：{config.SCOPE_INTL_DISPLAY}。"
            "仅收录上述数据库生态的开源工具，不含 AI 项目。"
        ),
    },
    "国产数据库": {
        "emoji": "🇨🇳",
        "title": "板块二 · 国内数据库",
        "intro": (
            f"范围：{config.SCOPE_CN_DISPLAY}。"
            "仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。"
        ),
    },
    "AI工具": {
        "emoji": "🤖",
        "title": "板块三 · AI 工具",
        "intro": (
            "范围：板块一 / 板块二所列数据库生态的 AI 辅助工具"
            "（text2sql / AI DBA / DB-MCP 等）。"
        ),
    },
}
SECTION_ORDER = ["国外数据库", "国产数据库", "AI工具"]


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


def _row_field(row: dict[str, Any], key: str, default: str = "—") -> str:
    """取 row 字段，None/空 → default。"""
    v = row.get(key)
    return v if isinstance(v, str) and v.strip() else default


# ============================================================
# 主周报 (report.md)
# ============================================================
def render_main_report(report_data: dict[str, Any], issue_no: int = 0) -> str:
    """渲染新 SOP 三板块周报全文。

    report_data 结构：
      {
        snapshot_date, first_period, prev_date,
        sections: [{key, active:[row], newcomers:[row], focus:row|None}, ...],
        topboard: [row, ...],
      }
    row（活跃榜/新锐）字段：full_name, html_url, category, databases,
                            growth, description, review, star
    focus row 额外：three={what,highlights,scenarios}
    topboard row 字段：full_name, html_url, star, section, category, description
    """
    snapshot_date = report_data.get("snapshot_date", "")
    first_period = report_data.get("first_period", False)
    sections = report_data.get("sections", [])

    parts: list[str] = [
        f"# 📋 {T.REPORT_NAME} · 第 {issue_no or 'N'} 期\n",
        f"> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。"
        "生产可用性请自行评估。\n",
        f"> _{snapshot_date}_\n\n---\n",
    ]

    # ---- DBA 速览 ----
    parts.append(f"## 📌 本周 DBA 速览\n\n{_render_overview(sections, first_period)}\n")

    # ---- 三板块 ----
    for sec in sections:
        parts.append(f"\n{_render_section(sec, first_period)}\n")

    # ---- Top 总榜 ----
    parts.append(f"\n## 📊 Top 总榜（历史 Star 总数）\n\n"
                 f"{_render_topboard(report_data.get('topboard', []))}\n")

    # ---- 互动与说明 ----
    parts.append(f"\n## 💬 互动与说明\n\n{T.MAIN_META.format(date=snapshot_date)}\n")
    parts.append("\n---\n")
    return "\n".join(parts).rstrip() + "\n"


def _render_overview(sections: list[dict[str, Any]], first_period: bool) -> str:
    """本周 DBA 速览：每板块一行（代表项目 + 增长 + 一句话提炼）。"""
    if first_period:
        return "> _本期为首期（无 7 天基准），活跃榜/新锐自第 02 期起完整。_\n"
    lines = []
    for sec in sections:
        meta = SECTION_META.get(sec.get("key", ""), {})
        emoji = meta.get("emoji", "")
        name = sec.get("key", "")
        # 代表项目：本周解读优先，否则活跃榜第一
        rep = sec.get("focus") or (sec.get("active") or [None])[0]
        if not rep:
            lines.append(f"- {emoji} **{name}**：本周无显著动态")
            continue
        full = rep.get("full_name", "")
        url = rep.get("html_url", "#")
        growth = rep.get("growth")
        growth_str = f"+{growth}" if isinstance(growth, int) and growth > 0 else ""
        desc = _md_escape_cell(rep.get("description", ""))[:60]
        lines.append(
            f"- {emoji} **{name}**：[{_short_name(full)}]({url})"
            f"（{growth_str}）—— {desc}"
        )
    return "\n".join(lines) + "\n"


def _render_section(sec: dict[str, Any], first_period: bool) -> str:
    """渲染单个板块（标题 + 活跃榜 + 新锐 + 本周解读，卡片形式）。"""
    key = sec.get("key", "")
    meta = SECTION_META.get(key, {})
    out = [
        f"## {meta.get('emoji', '')} {meta.get('title', key)}",
        f"> {meta.get('intro', '')}\n",
    ]

    active = sec.get("active") or []
    newcomers = sec.get("newcomers") or []
    focus = sec.get("focus")

    # 活跃榜
    out.append("### 🔥 活跃榜 Top3\n")
    if first_period or not active:
        out.append("_（首期无基准 / 本板块本周无正向增长项目。）_\n")
    else:
        out.append(_render_cards(active, ["🥇", "🥈", "🥉"]))

    # 新锐发现
    if newcomers:
        out.append("### 🌱 新锐发现（最多 3 个）\n")
        out.append(_render_cards(newcomers, ["①", "②", "③"]))

    # 本周解读
    out.append(f"### 🔍 本周解读{(' · ' + _short_name(focus.get('full_name', ''))) if focus else ''}\n")
    if focus:
        out.append(_render_focus(focus))
    else:
        out.append("_（本板块本周无解读项目。）_\n")
    return "\n".join(out)


def _render_cards(rows: list[dict[str, Any]], badges: list[str]) -> str:
    """活跃榜 / 新锐发现引用块卡片（每项目一张卡，GitHub 原生渲染）。"""
    blocks: list[str] = []
    for i, r in enumerate(rows):
        badge = badges[i] if i < len(badges) else "•"
        full = r.get("full_name", "")
        url = r.get("html_url", "#")
        growth = r.get("growth")
        growth_str = f" · 本周 **+{growth}**" if isinstance(growth, int) and growth > 0 else ""
        head = f"> {badge} **[{full}]({url})** · ⭐ {_star_k(r.get('star'))}{growth_str}"
        # 0-star 新锐按近 7 天 commit 排序入选，卡片补示 commit 数以示依据
        commits = r.get("commit_count_7d")
        if not (r.get("star") or 0) and isinstance(commits, int):
            head += f" · 近7天 {commits} commits"
        lines = [
            head,
            f"> `{_row_field(r, 'category')}` · 适用：{_row_field(r, 'databases')}",
        ]
        desc = _md_escape_cell(r.get("description", ""))[:80]
        if desc:
            lines.append(f"> {desc}")
        review = _md_escape_cell(_row_field(r, "review", "")).strip()
        if review:
            lines.append(f"> 🤖 **AI 解读**：{review}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _render_focus(focus: dict[str, Any]) -> str:
    """本周解读：引用块卡片头部 + 解决什么/核心亮点/使用场景 三段。"""
    full = focus.get("full_name", "")
    url = focus.get("html_url", "#")
    desc = focus.get("description", "")
    three = focus.get("three") or {}

    growth = focus.get("growth")
    growth_part = f" · 本周 **+{growth}**" if isinstance(growth, int) and growth > 0 else ""
    head = [
        f"> 🔍 **[{full}]({url})** · ⭐ {_star_k(focus.get('star'))}{growth_part}",
        f"> `{_row_field(focus, 'category')}` · 适用：{_row_field(focus, 'databases')}",
    ]
    intro = _md_escape_cell(desc)[:120]
    if intro:
        head.append(f"> {intro}")

    segs = [
        ("**解决什么**", _row_field(three, "what", "—")),
        ("**核心亮点**", _row_field(three, "highlights", "—")),
        ("**使用场景**", _row_field(three, "scenarios", "—")),
    ]
    body = "\n\n".join(f"{label}：{_md_escape_cell(text)}" for label, text in segs)
    return "\n".join(head) + "\n\n" + body + "\n"


def _render_topboard(rows: list[dict[str, Any]]) -> str:
    """附录总榜 Top5。"""
    if not rows:
        return "_（无数据。）_\n"
    out = ["| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |", "| :--- | ---: | :--- | :--- | :--- |"]
    for r in rows:
        full = r.get("full_name", "")
        url = r.get("html_url", "#")
        out.append(
            f"| **[{full}]({url})** "
            f"| {_star_k(r.get('star'))} "
            f"| {_row_field(r, 'section')} "
            f"| {_row_field(r, 'category')} "
            f"| {_md_escape_cell(r.get('description', ''))[:70]} |"
        )
    return "\n".join(out) + "\n"
