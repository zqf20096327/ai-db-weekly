"""SOP 三板块分类 —— 板块归属 / 8 分类 / 适用数据库 / 排除（纯函数）。

新 SOP 周报专用，不耦合每日采集的 filters 漏斗：
  - 采集期 filters.classify 做 ai/tool/core 粗标（不影响是否采集）
  - 本模块在周报期按 SOP §3.x 精判（板块归属、分类、适用数据库）

依据：deepseek SOP 文本 + 2026-08-14 用户口径
  - 板块范围闸门：范围外数据库（config.OUT_OF_SCOPE_DB_KEYWORDS）一律排斥
  - §3.1 板块归属（AI 优先 > 国产 > 国外，命中即停；板块一/二禁 AI 项目）
  - §3.3 排除（ORM / PaaS / 应用层 / 教程）
  - §3.4 八分类枚举（高可用/监控/备份/管理/迁移/连接代理/平台/其他）
  - §3.5 适用数据库推断（仅范围内数据库）

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
# 板块范围闸门（范围外数据库排斥 + AI 板块范围复核）
# ============================================================
def is_out_of_scope_text(text: str) -> bool:
    """文本是否命中范围外数据库（MongoDB/Redis/SQLite/Doris 等）。

    子串匹配（清单词在 DB 语境中独特）。供 desc/topics 检查与 README 复核复用。
    """
    t = (text or "").lower()
    return any(kw in t for kw in config.OUT_OF_SCOPE_DB_KEYWORDS)


def in_scope_hit_text(text: str) -> bool:
    """文本是否命中范围内数据库产品名（板块一/二准入口径，README 复核复用）。"""
    t = (text or "").lower()
    return _match(config.SCOPE_DB_NAME_KEYWORDS, t, set(_TOKEN_RE.findall(t)))


def is_out_of_scope(item: dict[str, Any]) -> bool:
    """是否纯范围外生态项目 → 不进周报。

    口径：命中范围外库名 且 未命中任何范围内库名 才排除（如 Redis 专属工具）。
    范围内+范围外混合的多库工具（如 WrenAI/Chat2DB，既支持 PostgreSQL/ClickHouse
    也支持 BigQuery/DuckDB）保留 —— 归属按范围内命中走，卡片「适用数据库」
    只展示范围内库名，范围外库名不出现在周报。
    """
    hay = _haystack(item)
    if not is_out_of_scope_text(hay):
        return False
    return not in_scope_hit_text(hay)


# AI 板块范围复核词：DBA 强词（挡 chroma 类与范围内库生态无关的向量库本体，
# 它们只有 "database" 泛词、无任何 SQL/DBA/范围内库名信号）
_AI_SCOPE_STRONG = [
    "sql", "dba", "database-admin", "database admin",
    "text2sql", "text-to-sql", "nl2sql", "chat2db",
    "schema", "migration", "backup", "odbc", "jdbc",
]


def _ai_scope_hit(item: dict[str, Any]) -> bool:
    """AI 工具是否与范围内数据库生态相关（命中范围内库名或 DBA 强词）。"""
    hay = _haystack(item)
    toks = _tokens(item)
    return (
        _match(_AI_SCOPE_STRONG, hay, toks)
        or _match(config.SCOPE_DB_NAME_KEYWORDS, hay, toks)
    )


# ============================================================
# 板块归属（新口径：AI 优先 > 国产 > 国外，范围外一律排斥）
# ============================================================
def assign_section(item: dict[str, Any]) -> str | None:
    """归入唯一板块。

    返回 "AI工具" | "国产数据库" | "国外数据库" | None（None=不归属，由调用方排除）。
    优先级说明：AI 检查在最前，保证板块一/二不出现 AI 项目（板块口径禁 AI）；
    AI 项目还须与范围内数据库生态相关（_ai_scope_hit），否则整个排除，
    不允许其凭 "database" 泛词落入国外板块。
    KERNEL_REPOS 排除不在此做 —— 由调用方统一 reg.is_kernel 过滤，保证全局一致
    （含国产板块：tidb/oceanbase 等内核即使在国产关键词命中也被上层剔除）。
    """
    if is_out_of_scope(item):
        return None

    hay = _haystack(item)
    toks = _tokens(item)
    topics = _topics_set(item)

    # 1. AI 工具（须 AI 信号 + 范围内数据库生态相关，否则整体排除）
    if is_ai_project(item):
        return "AI工具" if _ai_scope_hit(item) else None

    # 2. 国产数据库（产品名 token 命中）
    if _match(config.SECTION_KEYWORDS["国产数据库"], hay, toks) or (
        topics & {kw for kw in config.SECTION_KEYWORDS["国产数据库"]}
    ):
        return "国产数据库"

    # 3. 国外数据库（须命中范围内国外库名 且 DB 相关；泛词不再兜底，
    #    SawitDB/discodb 这类独立实验引擎不入板块）
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
    "column-oriented", "nosql database", "newsql database",
    "graph database", "vector database",
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
def _extract_in_scope_dbs(text: str, extra: str = "") -> list[str]:
    """从检索串提取范围内库名（去重保序；PolarDB 与 PolarDB-X 同显时只留后者）。"""
    found: list[str] = []
    for db_name, keywords in config.APPLICABLE_DB_KEYWORDS.items():
        for kw in keywords:
            if kw in text or (extra and kw in extra):
                found.append(db_name)
                break
    seen: set[str] = set()
    uniq = [d for d in found if not (d in seen or seen.add(d))]
    # "polardb" 子串必然命中 polardb-x 文本 → 同显两者时只留更具体的 PolarDB-X
    if "PolarDB-X" in uniq and "PolarDB" in uniq:
        uniq.remove("PolarDB")
    return uniq


def _format_dbs(uniq: list[str]) -> str:
    """范围内库名列表 → 展示串：1 种直写；2-5 种「 / 」连接；>5 种 N+种（前3等）。"""
    if not uniq:
        return ""
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) <= 5:
        return " / ".join(uniq)
    return f"{len(uniq)}+种数据库（{' / '.join(uniq[:3])}等）"


def infer_databases(item: dict[str, Any], *, extra_text: str = "") -> str:
    """推断适用数据库，按 SOP §3.5 格式输出。

    1 种 → 直写；2-5 种 → 「 / 」连接；>5 种 → N+种数据库（前3等）；
    数据库本体 → 仍提取范围内库名（timescaledb 这类 PG 扩展需要生态归属）：
    命中 → 「PostgreSQL（扩展/本体）」带身份注记；未命中 → 不适用（数据库本身）；
    未识别且无多库泛化词 → 待确认。
    extra_text：候选层可传 README 全文，从 README 补充提取范围内库名
    （关键词表仅含范围内数据库，README 提及范围外库名不会进入结果）。
    注意：本体判定与本体分支的库名提取只看 desc/topics —— README 常出现
    "vector database" 等短语，会把工具误判成本体；README 的兼容性提及
    也可能给无关本体错挂库名（如 QuestDB 提 PostgreSQL 仅协议兼容）。
    """
    hay = _haystack(item)
    extra = extra_text.lower() if extra_text else ""

    # 数据库本体（非工具，仅以 desc/topics 判定，见 docstring）：
    # 注记仅限强绑定 —— 「XX extension」（扩展）或恰好单一范围内库（本体）。
    # 多库命中多为工具兼容列表误入本体分支（chartbrew/tbls 等），回退不适用，
    # 避免给非本体项目错挂「（本体）」身份。库名提取同样只信 desc/topics。
    if any(p in hay for p in _DB_IDENTITY):
        uniq = _extract_in_scope_dbs(hay)
        is_ext = "extension" in hay or "扩展" in hay
        if uniq and (is_ext or len(uniq) == 1):
            return f"{_format_dbs(uniq)}（{'扩展' if is_ext else '本体'}）"
        return "不适用（数据库本身）"

    uniq = _extract_in_scope_dbs(hay, extra)
    if not uniq:
        if any(h in hay for h in config.DATABASE_MULTI_HINTS):
            return "多数据库"
        return "待确认"
    return _format_dbs(uniq)


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
