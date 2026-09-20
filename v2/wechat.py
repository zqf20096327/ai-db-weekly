"""公众号专用 HTML 渲染层（全内联样式，纯函数）。

公众号编辑器会剥掉 <style>/class/媒体查询等非内联样式，因此本模块输出
全部使用内联 style 的 <section>/<p> 标签（编辑器保留度最高的写法），
按手机单栏固定布局设计，Top 总榜用卡片列表替代表格（表格在手机端显示差）。
正文中的 GitHub 链接以纯文本呈现（普通公众号正文不允许外链）。

产物：weekly/wechat.html —— 浏览器打开 → 全选复制 → 粘贴进公众号编辑器。

数据结构同 render.render_main_report 的 report_data（见其 docstring）。
"""

from __future__ import annotations

from typing import Any

import config

# ---- 设计令牌（与 2026-09-07 第 1 期手工定稿版一致，调整需同步 SOP） ----
TXT = "#1e293b"          # 正文
TXT_DARK = "#0f172a"     # 标题/强调
TXT_GRAY = "#475569"     # 次要信息
TXT_MUTED = "#64748b"    # 弱说明
CARD_BG = "#fafcff"      # 项目卡片底色
CARD_BORDER = "#e9edf4"
BADGE_BG = "#e6edf8"
BADGE_TXT = "#1e4b7a"
STAR_BLUE = "#2563eb"    # Top 总榜 star 数字

SECTION_SCOPE = {
    "国外数据库": "Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse",
    "国产数据库": config.SCOPE_CN_DISPLAY,
    "AI工具": "板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）",
}
SECTION_EMOJI = {"国外数据库": "🗄️", "国产数据库": "🇨🇳", "AI工具": "🤖"}
SECTION_TITLE = {
    "国外数据库": "板块一 · 国际主流数据库",
    "国产数据库": "板块二 · 国内数据库",
    "AI工具": "板块三 · AI 工具",
}


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _star_k(num: int | None) -> str:
    if num is None:
        return "—"
    return f"{num / 1000:.1f}k" if num >= 1000 else str(num)


def _short_name(full: str) -> str:
    return full.split("/", 1)[1] if "/" in full else full


def _field(row: dict[str, Any], key: str, default: str = "—") -> str:
    v = row.get(key)
    return v if isinstance(v, str) and v.strip() else default


def _cut(s: str, n: int) -> str:
    """手机卡片内截断长描述（GitHub description 常为长英文，撑爆卡片）。

    英文按词边界收尾再补省略号，避免单词拦腰截断。
    """
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[: n - 1]
    sp = cut.rfind(" ")
    if sp >= int(n * 0.6):
        cut = cut[:sp]
    return cut.rstrip(" ，,、；;：:") + "…"


def _h2(text: str, margin_top: str = "28px") -> str:
    return (f'<p style="margin:{margin_top} 0 4px 0;font-size:18px;'
            f'font-weight:700;color:{TXT_DARK};">{_esc(text)}</p>')


def _sub(text: str) -> str:
    return (f'<p style="margin:0 0 14px 0;padding-left:10px;border-left:3px solid #d0d9e8;'
            f'font-size:12px;color:{TXT_MUTED};line-height:1.6;">{_esc(text)}</p>')


def _label(text: str, margin_top: str = "16px") -> str:
    return (f'<p style="margin:{margin_top} 0 10px 0;font-size:15px;'
            f'font-weight:600;color:{TXT_DARK};">{_esc(text)}</p>')


def _badge(text: str) -> str:
    return (f'<span style="font-size:11px;background:{BADGE_BG};padding:1px 10px;'
            f'border-radius:30px;color:{BADGE_TXT};font-weight:500;">{_esc(text)}</span>')


def _card_open() -> str:
    return (f'<section style="background:{CARD_BG};border:1px solid {CARD_BORDER};'
            f'border-radius:14px;padding:14px 16px;margin-bottom:12px;">')


def _card_head(name: str, badge: str, star: int | None, growth: Any,
               databases: str, commit_note: str = "") -> str:
    """卡片头：项目名 + 分类徽标一行；star/增长/适用数据库一行。"""
    growth_str = (f' · 本周 <strong style="color:{TXT_DARK};">+{growth}</strong>'
                  if isinstance(growth, int) and growth > 0 else "")
    head = (f'<p style="margin:0 0 4px 0;font-size:16px;font-weight:700;'
            f'color:{TXT_DARK};line-height:1.5;">{_esc(name)} {_badge(badge)}</p>')
    meta = (f'<p style="margin:0 0 8px 0;font-size:13px;color:{TXT_GRAY};">'
            f'⭐ {_star_k(star)}{growth_str}{commit_note}　适用：{_esc(databases)}</p>')
    return head + meta


def _para(strong: str, text: str, last: bool = True) -> str:
    m = "0" if last else "8px 0"
    return (f'<p style="margin:{m};font-size:14px;line-height:1.8;color:{TXT};">'
            f'<strong style="color:{TXT_DARK};">{_esc(strong)}</strong>：{_esc(text)}</p>')


# ============================================================
# 各区块
# ============================================================
def _w_header(report_data: dict[str, Any], issue_no: int) -> str:
    date = report_data.get("snapshot_date", "")
    return (
        '<section style="border-bottom:2px solid #eef2f6;padding-bottom:14px;margin-bottom:20px;">'
        f'<h1 style="margin:0;font-size:20px;font-weight:700;color:{TXT_DARK};line-height:1.4;">'
        f'📌 本周 DBA 速览</h1>'
        f'<p style="margin:8px 0 0 0;font-size:12px;color:{TXT_MUTED};line-height:1.8;">'
        f'📊 数据源：GitHub&nbsp;&nbsp;📅 {_esc(date)}&nbsp;&nbsp;第 {issue_no or "N"} 期<br/>'
        f'<span style="background:#eef2f6;padding:2px 10px;border-radius:30px;color:#334155;">聚焦开源工具 · 实验项目</span>&nbsp;'
        f'<span style="background:#eef2f6;padding:2px 10px;border-radius:30px;color:#334155;">⚠️ 生产可用性请自行评估</span>'
        '</p></section>'
    )


def _w_card(row: dict[str, Any], badge: str) -> str:
    """活跃榜卡片：核心亮点取 description（沿用第 1 期定稿版式，跨期保持一致），
    AI 解读单列一段。"""
    parts = [_card_open(), _card_head(
        f"{badge} {_short_name(row.get('full_name', ''))}",
        _field(row, "category"),
        row.get("star"), row.get("growth"),
        _field(row, "databases"),
    )]
    desc = _cut(_field(row, "description", ""), 100)
    if desc and desc != "—":
        parts.append(_para("核心亮点", desc, last=False))
    review = _field(row, "review", "")
    if review and review != "—":
        parts.append(_para("🤖 AI 解读", review))
    elif desc and desc != "—":
        parts[-1] = _para("核心亮点", desc)
    parts.append("</section>")
    return "".join(parts)


def _w_card_compact(row: dict[str, Any], badge: str) -> str:
    """新锐卡片（紧凑：头 + 一句话解读）。"""
    review = _field(row, "review", "")
    one_liner = review if review != "—" else _field(row, "description", "")
    head = (
        f'<p style="margin:0 0 4px 0;font-size:15px;font-weight:700;color:{TXT_DARK};">'
        f'{_esc(badge + " " + _short_name(row.get("full_name", "")))} {_badge(_field(row, "category"))}'
        f'<span style="font-weight:400;font-size:13px;color:{TXT_GRAY};">　⭐ '
        f'{_star_k(row.get("star"))}</span></p>'
    )
    body = (
        f'<p style="margin:0;font-size:13.5px;line-height:1.7;color:{TXT};">'
        f'<strong style="color:{TXT_DARK};">一句话解读</strong>：{_esc(one_liner)}'
        f'　适用：{_esc(_field(row, "databases"))}</p>'
    )
    return _card_open().replace("padding:14px 16px", "padding:12px 16px") + head + body + "</section>"


def _w_focus_card(focus: dict[str, Any]) -> str:
    """本周解读卡片：三维分析三段。"""
    three = focus.get("three") or {}
    parts = [
        _card_open(),
        _card_head(_short_name(focus.get("full_name", "")), _field(focus, "category"),
                   focus.get("star"), focus.get("growth"), _field(focus, "databases")),
        _para("解决什么问题", _field(three, "what"), last=False),
        _para("核心亮点", _field(three, "highlights"), last=False),
        _para("适用场景", _field(three, "scenarios")),
        "</section>",
    ]
    return "".join(parts)


def _w_section(sec: dict[str, Any], first_period: bool) -> str:
    key = sec.get("key", "")
    out = [_h2(f"{SECTION_EMOJI.get(key, '')} {SECTION_TITLE.get(key, key)}"),
           _sub(SECTION_SCOPE.get(key, ""))]
    active = sec.get("active") or []
    newcomers = sec.get("newcomers") or []
    focus = sec.get("focus")

    out.append(_label("🔥 活跃榜 Top3"))
    if first_period or not active:
        out.append(f'<p style="margin:0;font-size:13px;color:{TXT_MUTED};">'
                   f'（首期无基准 / 本板块本周无正向增长项目。）</p>')
    else:
        out += [_w_card(r, b) for r, b in zip(active, ["🥇", "🥈", "🥉"])]

    if newcomers:
        out.append(_label("🌱 新锐发现"))
        out += [_w_card_compact(r, b) for r, b in zip(newcomers, ["①", "②", "③"])]

    out.append(_label(f"🔍 本周解读{(' · ' + _short_name(focus.get('full_name', ''))) if focus else ''}"))
    out.append(_w_focus_card(focus) if focus
               else f'<p style="margin:0;font-size:13px;color:{TXT_MUTED};">（本板块本周无解读项目。）</p>')
    return "".join(out)


def _w_topboard(rows: list[dict[str, Any]]) -> str:
    """Top 总榜：卡片列表替代表格。"""
    out = [_h2("📊 Top 总榜（历史 Star 总数）", margin_top="32px")]
    for i, r in enumerate(rows, 1):
        out.append(
            f'<section style="background:#f1f5f9;border-radius:12px;padding:12px 14px;margin-bottom:8px;">'
            f'<p style="margin:0;font-size:14px;font-weight:700;color:{TXT_DARK};">'
            f'{i}. {_esc(r.get("full_name", ""))}　'
            f'<span style="color:{STAR_BLUE};">{_star_k(r.get("star"))} ⭐</span></p>'
            f'<p style="margin:2px 0 0 0;font-size:12.5px;color:{TXT_GRAY};">'
            f'{_esc(_field(r, "section"))} · {_esc(_field(r, "category"))}｜'
            f'{_esc(_cut(_field(r, "description", ""), 70))}</p></section>'
        )
    return "".join(out)


def _w_footer(report_data: dict[str, Any]) -> str:
    return (
        f'<section style="margin-top:24px;padding-top:16px;border-top:2px solid #eef2f6;'
        f'font-size:13px;color:{TXT_GRAY};line-height:1.8;">'
        f'<section style="background:#f1f5f9;padding:12px 16px;border-radius:14px;'
        f'margin-bottom:12px;color:{TXT_DARK};font-size:14px;">'
        f'💬 <strong>互动</strong>：本周你最关注哪个项目？欢迎留言分享你的试用体验。</section>'
        f'<p style="margin:0;"><strong style="color:{TXT_DARK};">📌 板块范围说明</strong>：<br/>'
        f'板块一：{SECTION_SCOPE["国外数据库"]}<br/>'
        f'板块二：{SECTION_SCOPE["国产数据库"]}<br/>'
        f'板块三：上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。</p>'
        '</section>'
    )


# ============================================================
# 主入口
# ============================================================
def render_wechat_html(report_data: dict[str, Any], issue_no: int = 0) -> str:
    """渲染公众号专用 HTML（全内联样式，report_data 结构同 render_main_report）。"""
    parts = [
        '<!-- 公众号专用版：全内联样式。浏览器打开 → 全选复制 → 粘贴进公众号编辑器。 -->\n'
        '<body style="margin:0;padding:0;background:#ffffff;">\n'
        '<section style="max-width:677px;margin:0 auto;padding:16px 14px;'
        'font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;'
        f'color:{TXT};font-size:15px;line-height:1.7;">',
        _w_header(report_data, issue_no),
    ]
    for sec in report_data.get("sections", []):
        parts.append(_w_section(sec, report_data.get("first_period", False)))
    parts.append(_w_topboard(report_data.get("topboard", [])))
    parts.append(_w_footer(report_data))
    parts.append("</section>\n</body>\n")
    return "".join(parts)
