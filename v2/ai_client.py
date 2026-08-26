"""AI 客户端 —— 周报内容增强的统一调用层（DeepSeek）。

SOP 内容三类型中两类依赖 AI：
  - AI 翻译（生态工具 / AI 板块）：忠实翻译 README/description 的作用
  - AI 理解受控（仅④本周重点解读）

接通 DeepSeek chat completion（.env 有 AI_API_KEY/AI_BASE_URL/AI_MODEL）。
红线：翻译/解读均受 SOP 红线约束（禁对比/评判/预测，禁用词见 templates.BANNED_WORDS）
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import config

log = logging.getLogger(__name__)


# ============================================================
# .env 加载（不依赖 python-dotenv，只读 .env）
# ============================================================
def load_ai_env() -> None:
    """从 .env 读 AI_API_KEY/AI_BASE_URL/AI_MODEL 到 os.environ（不覆盖已有）。"""
    env_path = config.ENV_FILE
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k in ("AI_API_KEY", "AI_BASE_URL", "AI_MODEL"):
                    if not os.environ.get(k):
                        os.environ[k] = v
    except OSError as e:
        log.warning("读取 .env 失败: %s", e)


class AIClient:
    """AI 调用封装（DeepSeek chat completion）。

    enabled=True 时调真实 API；key 缺失或调用失败时回退占位逻辑，保证周报不中断。
    """

    def __init__(self) -> None:
        load_ai_env()
        self.api_key = os.environ.get("AI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = os.environ.get("AI_BASE_URL") or config.AI_BASE_URL_DEFAULT
        self.model = os.environ.get("AI_MODEL") or config.AI_MODEL_DEFAULT
        self.enabled = bool(self.api_key)
        if not self.enabled:
            log.warning("AI_API_KEY 未配置，AI 解读将回退占位模式")

    # ============================================================
    # DeepSeek chat completion
    # ============================================================
    def _chat(self, prompt: str) -> str:
        """调 DeepSeek chat completion，返回文本。失败返回空串。"""
        import requests  # noqa: PLC0415

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.AI_TEMPERATURE,
            "max_tokens": config.AI_MAX_TOKENS,
        }
        for attempt in range(2):  # 超时重试 1 次
            try:
                resp = requests.post(
                    url, json=payload, headers=headers, timeout=config.AI_TIMEOUT_SEC,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            except Exception as e:  # noqa: BLE001
                if attempt < 1:
                    import time  # noqa: PLC0415
                    log.warning("AI 调用失败，重试 1 次: %s", e)
                    time.sleep(3)
                    continue
                log.warning("AI 调用失败（回退占位）: %s", e)
                return ""
        return ""

    # ============================================================
    # 主周报精选解读：工具的"发生了什么"+"为什么值得关注"
    # ============================================================
    def focus_tool_review(
        self,
        item: dict[str, Any],
        release_body: str | None,
        tag: str | None,
        readme_text: str | None = None,
    ) -> tuple[str, str]:
        """精选解读：基于 README + release notes 生成中文点评。

        enabled=True 时调 DeepSeek；失败回退占位。
        返回 (what_happened, why_care)。
        """
        full = item.get("full_name", "")
        desc = item.get("description") or ""

        if self.enabled:
            what, why = self._ai_review(full, desc, release_body, tag, readme_text)
            if what or why:
                return what, why
            # AI 返回空 → 回退占位
            log.warning("AI 解读返回空，回退占位: %s", full)

        # ---- 占位逻辑（降级）----
        return self._placeholder_review(item, release_body, tag)

    def _ai_review(
        self, full: str, desc: str, release_body: str | None, tag: str | None, readme_text: str | None,
    ) -> tuple[str, str]:
        """调 DeepSeek 生成受控中文点评。"""
        import templates as T  # noqa: PLC0415

        prompt = (
            "你是数据库技术编辑。基于以下信息，用中文客观解读这个开源工具。\n"
            "要求：不要评判好坏，不要预测未来，不要与其他项目对比。只陈述事实。\n\n"
            f"项目：{full}\n"
            f"描述：{desc}\n"
            f"本周发版：{tag or '无'}\n"
            f"Release Notes：\n{(release_body or '无')}\n\n"
            f"README：\n{(readme_text or '无')}\n\n"
            "请输出两段，用 ===SPLIT=== 分隔：\n"
            "第一段「发生了什么」：本周发版的核心变更（基于 Release Notes，3-5 句中文）。"
            "如果 Release Notes 无实质内容则说明本次发版的大致方向。\n"
            "第二段「为什么值得关注」：这个工具解决什么问题、面向什么场景、核心能力"
            "（基于 README 和描述，3-5 句中文）。"
        )
        raw = self._chat(prompt)
        if not raw:
            return "", ""

        # 拆分两段
        parts = raw.split("===SPLIT===")
        what = parts[0].strip() if len(parts) >= 1 else ""
        why = parts[1].strip() if len(parts) >= 2 else ""
        # 如果没按分隔符拆，尝试按换行段拆
        if not why and "\n\n" in what:
            chunks = what.split("\n\n", 1)
            what, why = chunks[0].strip(), chunks[1].strip()

        # 过禁用词
        what = _strip_banned(what, T.BANNED_WORDS)
        why = _strip_banned(why, T.BANNED_WORDS)
        return what, why

    def _placeholder_review(
        self, item: dict[str, Any], release_body: str | None, tag: str | None,
    ) -> tuple[str, str]:
        """占位逻辑：release notes 截取 + description（降级用）。"""
        desc = item.get("description") or ""
        body = (release_body or "").strip()

        if body:
            lines = [
                ln.strip() for ln in body.split("\n")
                if ln.strip() and not ln.strip().startswith("#")
                and not ln.strip().startswith("![")
            ][:3]
            what = " ".join(lines)[:200] if lines else f"发布版本 {tag or ''}。"
        else:
            what = f"发布版本 {tag or ''}。" if tag else ""

        if desc:
            why = f"{item.get('full_name', '')} 定位：{_md_truncate(desc, 120)}"
        else:
            why = ""
        return what, why

    # ============================================================
    # 新 SOP：每项目 80 字中性 AI 解读（§4.3）+ 本周解读三维分析（§4.5）
    # ============================================================
    def brief_review(
        self,
        item: dict[str, Any],
        category: str,
        databases: str,
        readme: str | None = None,
    ) -> str:
        """§4.3 每项目 AI 解读：≤80 字，中性、客观、无绝对词。

        enabled=True 调 DeepSeek；失败/未配置回退占位。README 缺失时退化为 description。
        """
        full = item.get("full_name", "")
        desc = item.get("description") or ""
        topics = ", ".join(item.get("topics") or []) or "无"
        readme_brief = (readme or "")[:2000] or "无"

        if self.enabled:
            text = self._ai_brief(full, desc, topics, category, databases, readme_brief)
            if text:
                return text
            log.warning("AI 解读返回空，回退占位: %s", full)
        return self._placeholder_brief(desc)

    def _compress(self, text: str, limit: int) -> str:
        """超字数时带原文重问一次，让模型自行压缩（保信息完整优于硬截）。

        返回压缩文本；失败返回空串（调用方沿用原文走边界截断兜底）。
        """
        prompt = (
            f"请把下面这段中文压缩到{limit}字以内（含标点）。保留关键信息，"
            "不评判好坏、不对比、不预测、不使用绝对词，只输出压缩后的文字：\n" + text
        )
        out = self._chat(prompt)
        if out:
            return out.strip().strip("\"“”'")
        return ""

    def _ai_brief(
        self, full: str, desc: str, topics: str,
        category: str, databases: str, readme_brief: str,
    ) -> str:
        """调 DeepSeek 生成 ≤80 字中性客观解读。"""
        import templates as T  # noqa: PLC0415

        prompt = (
            "你是数据库技术编辑。请根据以下项目信息，用中文写一段 AI 解读。\n\n"
            f"项目名称：{full}\n项目描述：{desc}\nTopics：{topics}\n"
            f"README关键内容：{readme_brief}\n分类：{category}\n适用数据库：{databases}\n\n"
            "要求：\n"
            "1. 中性、客观地说明这个项目是什么、对数据库使用者有什么用，只陈述事实\n"
            "2. 语气克制、专业，不评判好坏，不与其他项目对比，不预测未来\n"
            f"3. 全文（含标点）严格不超过{config.BRIEF_MAX_CHARS}字，宁可精简也不要超出\n"
            "4. 禁止使用任何绝对词（如：最、第一、唯一、完全、彻底、必将、永远 等）\n"
            "5. 提及数据库产品时仅限："
            f"{'/'.join(config.APPLICABLE_DB_KEYWORDS)}；"
            "范围外数据库（如 MongoDB/Redis/SQLite/Doris 等）不点名，用泛称代替\n"
            "只输出这段解读本身，不要额外解释或加引号。"
        )
        raw = self._chat(prompt)
        if not raw:
            return ""
        text = _scrub_out_of_scope(_clean_ai_text(raw))
        # 模型常数不准字数：超限先带原文压缩重问，仍超由边界截断兜底（不拦腰硬切）
        if len(text) > config.BRIEF_MAX_CHARS:
            retry = self._compress(text, config.BRIEF_MAX_CHARS)
            if retry:
                text = _scrub_out_of_scope(_clean_ai_text(retry)) or text
        return _strip_banned(
            _smart_truncate(text, config.BRIEF_MAX_CHARS), T.BANNED_WORDS
        )

    def _placeholder_brief(self, desc: str) -> str:
        """占位：无 AI 时用 description 兜底（截断到解读字数上限）。"""
        if desc:
            return _md_truncate(desc, config.BRIEF_MAX_CHARS)
        return "（描述缺失，AI 解读待补充）"

    def three_dimension_analysis(
        self,
        item: dict[str, Any],
        category: str,
        databases: str,
        readme: str | None = None,
    ) -> dict[str, str]:
        """§4.5 本周解读三维分析：解决什么 / 核心亮点 / 使用场景。

        返回 {what, highlights, scenarios}，每段 ≤ FOCUS_SEG_MAX_CHARS 字，
        中性客观。enabled=True 调 DeepSeek；失败回退占位。
        """
        full = item.get("full_name", "")
        desc = item.get("description") or "（无 description）"
        readme_full = (readme or "")[:5000] or "无"

        if self.enabled:
            d = self._ai_three(full, desc, category, databases, readme_full)
            if d:
                return d
            log.warning("AI 三维分析返回空，回退占位: %s", full)
        return self._placeholder_three(full, desc)

    def _ai_three(
        self, full: str, desc: str, category: str,
        databases: str, readme_full: str,
    ) -> dict[str, str]:
        """调 DeepSeek 生成三维解读，解析成 dict。"""
        import templates as T  # noqa: PLC0415

        prompt = (
            "你是一位数据库技术编辑。请根据以下项目信息，生成项目解读。\n\n"
            f"项目名称：{full}\n项目描述：{desc}\nREADME内容：{readme_full}\n"
            f"分类：{category}\n适用数据库：{databases}\n\n"
            "要求：中性、客观，只陈述事实；不评判好坏、不与其他项目对比、不预测未来；"
            "禁止使用任何绝对词（如：最、第一、唯一、完全、彻底、必将、永远 等）；"
            "提及数据库产品时仅限："
            f"{'/'.join(config.APPLICABLE_DB_KEYWORDS)}，"
            "范围外数据库不点名，用泛称代替。\n"
            "请严格按以下格式输出三段，段与段之间用独占一行的 === 分隔：\n"
            "第一段【解决什么】：用1-2句话说清楚解决的核心问题\n"
            "第二段【核心亮点】：列出2-4个关键技术或功能亮点（顿号或短句）\n"
            "第三段【使用场景】：说明适合哪些场景使用\n"
            f"每段（含标点）严格不超过{config.FOCUS_SEG_MAX_CHARS}字，宁可精简也不要超出；"
            "每段不要带【标签】等前缀，直接输出内容。"
        )
        raw = self._chat(prompt)
        if not raw:
            return {}

        parts = [p.strip() for p in raw.split("===")]
        # 兜底：未按 === 拆但有多空行段
        if len(parts) < 3 and "\n\n" in raw:
            parts = [p.strip() for p in raw.split("\n\n")]

        keys = ["what", "highlights", "scenarios"]
        d: dict[str, str] = {}
        for i, k in enumerate(keys):
            v = parts[i] if i < len(parts) else ""
            v = _LABEL_HEAD_RE.sub("", v)
            v = _scrub_out_of_scope(_clean_ai_text(v)).strip()
            if len(v) > config.FOCUS_SEG_MAX_CHARS:
                retry = self._compress(v, config.FOCUS_SEG_MAX_CHARS)
                if retry:
                    v = _scrub_out_of_scope(_clean_ai_text(retry)).strip() or v
            d[k] = (
                _strip_banned(
                    _smart_truncate(v, config.FOCUS_SEG_MAX_CHARS), T.BANNED_WORDS
                )
                if v else ""
            )
        return d

    def _placeholder_three(self, full: str, desc: str) -> dict[str, str]:
        """占位：无 AI 时三维留半空。"""
        return {
            "what": _md_truncate(f"{full}：{desc}", config.FOCUS_SEG_MAX_CHARS),
            "highlights": "（待基于 README 补充）",
            "scenarios": "（待补充）",
        }

    # ============================================================
    # 其他方法（保留接口，供其他栏目用）
    # ============================================================
    def summarize_release_notes(self, body: str | None, *, tag: str | None = None) -> str:
        """摘要 release notes。占位：返回 body 前 240 字。"""
        if not body:
            return f"`{tag or ''}` 官方 Release Notes 暂无正文（详见出处链接）。"
        snippet = body.strip().replace("\r\n", "\n")
        if len(snippet) > 240:
            snippet = snippet[:240].rstrip() + "…"
        return f"> {snippet}"

    def translate_readme_role(self, item: dict[str, Any]) -> str:
        """翻译项目"做什么"。占位：返回 description 原文。"""
        desc = item.get("description") or ""
        if not desc:
            return "（该项目无 description）"
        return desc

    def focus_four_questions(
        self,
        item: dict[str, Any],
        signals: dict[str, Any],
        release: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """④本周重点固定四问（旧接口保留）。"""
        full = item.get("full_name", "")
        desc = item.get("description") or "（无 description）"
        reasons = signals.get("reasons", [])
        reason_text = "、".join(reasons) if reasons else "本周信号分最高"
        tag = release.get("tag_name") if release else None
        version_hint = f"（本周发布 {tag}）" if tag else ""
        return {
            "what": f"**{full}**：{desc}",
            "problem": f"_（待读取官方文档后补充面向场景）_{version_hint}",
            "highlights": "_（待基于 release notes 转述特性）_",
            "why": f"本周信号分最高：{reason_text}。当前 star {item.get('stargazers_count', 0)}。",
        }


# ============================================================
# 辅助
# ============================================================
# AI 输出常自带标签前缀（【解决什么】/**核心亮点**：/第X段 等），渲染层会再加标签，须剥离。
# 标签后必须跟分隔符（空白/:：/* 等），避免误剥"使用场景为…"这类正文开头。
_LABEL_HEAD_RE = re.compile(
    r"^[\s*【】#>]*(?:第[一二三1-3]段[\s:：*【】]*)?(?:"
    r"解决什么|解决了什么|核心亮点|使用场景|适用场景|DBA行动指南"
    r")[\s*【】:：\-–]+"
)


def _clean_ai_text(s: str) -> str:
    """清理 AI 输出：行内列表符（ - / • ）转顿号，避免单行内残留列表样式。"""
    return re.sub(r"\s+[-•]\s+", "、", s)


# AI 解读文本中范围外数据库产品名 → 泛称（板块口径：范围外库名不入周报正文；
# 长名在前，防止 "mongodb" 被 "mongo" 先行替换）
_OOS_TEXT_REPLACEMENTS = {
    "mongodb": "文档数据库",
    "mongo": "文档数据库",
    "sqlite": "轻量级文件数据库",
    "redis": "内存数据库",
    "duckdb": "嵌入式分析数据库",
    "doris": "OLAP 数据库",
    "starrocks": "OLAP 数据库",
    "tdengine": "时序数据库",
    "influxdb": "时序数据库",
    "bigquery": "云端数据仓库",
    "snowflake": "云端数据仓库",
    "databricks": "云端数据平台",
}


def _scrub_out_of_scope(text: str) -> str:
    """把 AI 文本中的范围外数据库产品名替换为泛称。"""
    out = text
    for name, generic in _OOS_TEXT_REPLACEMENTS.items():
        out = re.sub(re.escape(name), generic, out, flags=re.IGNORECASE)
    return out


def _md_truncate(s: str, limit: int) -> str:
    """截断字符串到指定长度（去换行）。"""
    s = (s or "").replace("\n", " ").strip()
    return s[:limit] + ("…" if len(s) > limit else "")


# 句读边界字符：超字数截断时优先在这些边界收尾，避免句子拦腰截断
_BREAK_CHARS = "。！？；，、：,;"


def _smart_truncate(text: str, limit: int) -> str:
    """截断到 limit 字内：能落在句读边界就整句/整分句收尾，否则才硬截加省略号。

    向前找边界时保底保留 60% 篇幅，防止首句超长时被截得只剩几个字。
    """
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    floor = max(int(limit * 0.6), 1)
    for i in range(len(cut) - 1, floor - 1, -1):
        if cut[i] in _BREAK_CHARS:
            return cut[: i + 1].rstrip("，、；：,; ")
    return cut[:-1] + "…"


def _strip_banned(text: str, banned: list[str]) -> str:
    """去除禁用词（SOP 红线：禁评判/广告/绝对词）。"""
    out = text
    for w in banned:
        out = out.replace(w, "")
    return out
