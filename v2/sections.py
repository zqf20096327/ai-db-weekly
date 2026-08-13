"""SOP 三板块分类 —— 板块归属 / 8 分类 / 适用数据库 / 排除（纯函数）。

新 SOP 周报专用，不耦合每日采集的 filters 漏斗：
  - 采集期 filters.classify 做 ai/tool/core 粗标（不影响是否采集）
  - 本模块在周报期按 SOP §3.x 精判（板块归属、分类、适用数据库）

依据：deepseek SOP 文本
  - §3.1 板块归属（国产 > AI > 国外，命中即停）
  - §3.3 排除（ORM / PaaS / 应用层 / 教程）
  - §3.4 八分类枚举（高可用/监控/备份/管理/迁移/连接代理/平台/其他）
  - §3.5 适用数据库推断

匹配设计（防子串污染）：
  纯单词关键词 → tokenize 后匹配独立 token（挡 ha→java、orm→transform、
  ai→available、rag→storage、sync→async、demo→democracy）；
  含空格/连字符的短语 → 子串匹配。
  topics 数组天然是 token，用精确集合匹配。
"""

from __future__ import annotations

import re
from typing import Any

import config
import filters

# token 切分：连续字母数字为一段（连字符/空格/斜杠均为分隔符）
_TOKEN_RE = re.compile(r"[a-z0-9]+")


# ============================================================
# 文本抽取与匹配辅助
# ============================================================
def _topics_set(item: dict[str, Any]) -> set[str]:
    """topics 转小写集合（保持原样，含连字符）。"""
    return {str(t).lower() for t in (item.get("topics") or [])}


def _haystack(item: dict[str, Any]) -> str:
    """full_name + description + topics 拼成的小写检索串。"""
    parts = [
        item.get("full_name") or "",
        item.get("description") if isinstance(item.get("description"), str) else "",
        " ".join(str(t) for t in (item.get("topics") or [])),
    ]
    return " ".join(p for p in parts if p).lower()


def _tokens(item: dict[str, Any]) -> set[str]:
    """haystack 切成的 token 集合（连字符/空格均为分隔）。"""
    return set(_TOKEN_RE.findall(_haystack(item)))


def _match(keywords: list[str], haystack: str, tokens: set[str]) -> bool:
    """关键词命中判断（含非字母数字→子串；纯单词→token）。"""
    for kw in keywords:
        kw_l = kw.lower()
        if re.search(r"[^a-z0-9]", kw_l):
            if kw_l in haystack:
                return True
        elif kw_l in tokens:
            return True
    return False


# ============================================================
# AI 项目识别（§3.1 AI 支 —— 分层 + DB 相关性复核）
# ============================================================
def is_ai_project(item: dict[str, Any]) -> bool:
    """是否 AI 项目（SOP §3.1 AI 支 + 防子串污染分层 + DB 相关性复核）。

    三层任一命中即可，但都须叠加 is_db_relevant（SOP「与数据库相关」）：
      1. topics 精确集合匹配 AI_TOPICS（最可靠）
      2. description 强信号词子串匹配 AI_KW_STRONG（llm/mcp/text2sql… 够独特）
      3. description tokenize 后匹配 AI_KW_TOKEN（ai/rag/agent/glm… 防误命中）
    """
    topics = _topics_set(item)
    hay = _haystack(item)
    toks = _tokens(item)

    hit = (
        bool(topics & config.AI_TOPICS)
        or _match(config.AI_KW_STRONG, hay, toks)
        or bool(toks & config.AI_KW_TOKEN)
    )
    if not hit:
        return False
    # 叠加 DB 相关性 —— 挡纯通用 AI（通用 chatbot、图像生成、LLM 训练框架）
    return filters.is_db_relevant(item)


# ============================================================
# 板块归属（§3.1，优先级 国产 > AI > 国外，命中即停）
# ============================================================
def assign_section(item: dict[str, Any]) -> str | None:
    """归入唯一板块。

    返回 "国产数据库" | "AI工具" | "国外数据库" | None（None=不归属，由调用方排除）。
    KERNEL_REPOS 排除不在此做 —— 由调用方统一 reg.is_kernel 过滤，保证全局一致
    （含国产板块：tidb/oceanbase/doris 等内核即使在国产关键词命中也被上层剔除）。
    """
    hay = _haystack(item)
    toks = _tokens(item)
    topics = _topics_set(item)

    # 1. 国产数据库（产品名 token 命中）
    if _match(config.SECTION_KEYWORDS["国产数据库"], hay, toks) or (
        topics & {kw for kw in config.SECTION_KEYWORDS["国产数据库"]}
    ):
        return "国产数据库"

    # 2. AI 工具（须 DB 相关）
    if is_ai_project(item):
        return "AI工具"

    # 3. 国外数据库（须命中国外词 且 DB 相关）
    if _match(config.SECTION_KEYWORDS["国外数据库"], hay, toks) and filters.is_db_relevant(item):
        return "国外数据库"

    return None


# ============================================================
# 八分类推断（§3.4，多命中取最先；无命中→其他）
# ============================================================
# 数据库本体自指身份短语 —— 命中则判为「平台」（SOP §3.4 例外：数据库本身→平台）
_DB_IDENTITY = [
    "is a database", "is an in-memory", "database engine", "storage engine",
    "key-value store", "key value store", "document database", "columnar",
    "column-oriented", "nosql", "newsql", "graph database", "vector database",
    "time-series database", "relational database",
    "数据库引擎", "存储引擎", "向量数据库", "时序数据库", "图数据库",
]


def infer_category(item: dict[str, Any]) -> str:
    """推断八分类之一（高可用/监控/备份/管理/迁移/连接代理/平台/其他）。

    例外（先于关键词）：description 自指为数据库本体 → 平台；
    引擎实验/重构类 → 由关键词兜底为「其他」。
    """
    desc = _haystack(item)
    # 例外：数据库本体 → 平台（避免 DB 引擎被关键词误判成工具类目）
    if any(p in desc for p in _DB_IDENTITY):
        return "平台"

    toks = _tokens(item)
    for cat, keywords in config.CATEGORY_KEYWORDS.items():
        if _match(keywords, desc, toks):
            return cat
    return "其他"


# ============================================================
# 适用数据库推断（§3.5）
# ============================================================
def infer_databases(item: dict[str, Any]) -> str:
    """推断适用数据库，按 SOP §3.5 格式输出。

    1 种 → 直写；2-5 种 → 「 / 」连接；>5 种 → N+种数据库（前3等）；
    数据库本体 → 不适用（数据库本身）；未识别且无多库泛化词 → 待确认。
    """
    hay = _haystack(item)

    # 数据库本体（非工具）→ 不适用
    if any(p in hay for p in _DB_IDENTITY):
        return "不适用（数据库本身）"

    found: list[str] = []
    for db_name, keywords in config.APPLICABLE_DB_KEYWORDS.items():
        for kw in keywords:
            if kw in hay:
                found.append(db_name)
                break

    # 去重保序
    seen: set[str] = set()
    uniq = [d for d in found if not (d in seen or seen.add(d))]

    if not uniq:
        if any(h in hay for h in config.DATABASE_MULTI_HINTS):
            return "多数据库"
        return "待确认"
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) <= 5:
        return " / ".join(uniq)
    return f"{len(uniq)}+种数据库（{' / '.join(uniq[:3])}等）"


# ============================================================
# §3.3 排除规则（叠加在 filters.is_display_relevant 之上）
# ============================================================
def should_exclude_sop(item: dict[str, Any]) -> bool:
    """是否应排除（SOP §3.3：ORM 框架 / PaaS 部署平台 / 纯应用层 / 教程示例）。

    在展示相关性过滤之上做二次清扫。关键词均为无歧义强信号
    （不放裸 platform/deploy/cloud，避免误杀 DB 平台/监控类工具）。
    """
    hay = _haystack(item)
    toks = _tokens(item)
    for group in config.SOP_EXCLUDE_KEYWORDS.values():
        if _match(group, hay, toks):
            return True
    return False
