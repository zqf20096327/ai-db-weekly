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
def _md_truncate(s: str, limit: int) -> str:
    """截断字符串到指定长度（去换行）。"""
    s = (s or "").replace("\n", " ").strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def _strip_banned(text: str, banned: list[str]) -> str:
    """去除禁用词（SOP 红线：禁评判/广告词）。"""
    out = text
    for w in banned:
        out = out.replace(w, "**")
    return out
