"""筛选漏斗 —— SOP 第六章四层漏斗 + 新生项目专用过滤。

全部为纯函数（不调网络），便于单测。
依据：SOP 6 第1-3层 + 6.x 新生项目专用过滤 + 采集策略清单 第五步后置过滤
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import config


def _text_of(item: dict[str, Any], *keys: str) -> str:
    """取多个字段的文本，拼成小写串用于关键词匹配。"""
    parts: list[str] = []
    for k in keys:
        v = item.get(k)
        if isinstance(v, str):
            parts.append(v.lower())
        elif isinstance(v, list):
            parts.extend(str(x).lower() for x in v)
    return " ".join(parts)


# ============================================================
# 第 2 层：黑名单关键词（命中任一即剔除）
# ============================================================
# 仅按"完整 token"匹配（边界为非字母数字），避免子串误杀。
#   错误：kw="docs" 命中 "documentation" / "oGRAC-docs" → 误杀
#   正确：kw="docs" 仅当 name 出现独立 "docs" token（如 "xxx-docs"/"docs-xxx"）时命中
import re as _re


def _token_hit(haystack: str, keyword: str) -> bool:
    """keyword 是否作为完整 token 出现在 haystack 中。

    token 边界：字符串首尾 或 非字母数字字符（含 - _ / . 空格）。
    特例：keyword 以 '-' 开头时（如 '-cn'）按后缀匹配。
    """
    if not haystack:
        return False
    h = haystack.lower()
    kw = keyword.lower()
    if kw.startswith("-"):
        return h.rstrip("/").endswith(kw) or ("-" + kw[1:]) in h.split("/")
    # 用正则保证 token 边界（kw 自身可含字母数字）
    pattern = r"(?:^|[^a-z0-9])" + _re.escape(kw) + r"(?:[^a-z0-9]|$)"
    return _re.search(pattern, h) is not None


# 这些 token 只对 repo 名称（name）敏感，避免误伤 description
# 例如 "docs" 在 description 里很常见（合法项目也会写 "see docs"）
_NAME_ONLY_KEYWORDS = {"docs", "site", "website", "homepage", "blog", "mirror", "-cn"}


def is_blacklisted(item: dict[str, Any]) -> bool:
    """命中黑名单关键词 → 剔除。

    匹配策略（避免子串误杀）：
      - _NAME_ONLY_KEYWORDS（docs/site/blog/mirror/-cn 等）：仅匹配 repo 名称
        （这些是"搬运/镜像站"特征名，但出现在 description 里是合法的）
      - 其余关键词（教程/作业/比赛等）：匹配 name + description + full_name
      - 全部按完整 token 匹配（边界为非字母数字），不做子串匹配
    SOP 6 第2层 + 采集策略清单 第五步后置过滤②。
    """
    name = (item.get("name") or "").lower()
    full = (item.get("full_name") or "").lower()
    # repo 名（full_name 去掉 owner/ 前缀）—— name-only 关键字只匹配这个，
    # 避免被 org 名污染（如 opengauss-mirror/* 被误判为 mirror）
    repo_name = name or (full.split("/", 1)[1] if "/" in full else full)
    desc = (item.get("description") or "").lower() if isinstance(item.get("description"), str) else ""

    for kw in config.BLACKLIST_KEYWORDS:
        kw_l = kw.lower()
        if kw_l in _NAME_ONLY_KEYWORDS:
            # 仅匹配 repo 名（不含 org 前缀），不碰 description
            if _token_hit(repo_name, kw):
                return True
        else:
            # 教程/作业/比赛等：匹配 repo 名 + full_name + description
            if _token_hit(repo_name, kw) or _token_hit(full, kw) or _token_hit(desc, kw):
                return True
    return False


# ============================================================
# 第 1 层：准入闸门（SOP 6 第1层）
# ============================================================
def pass_gate(item: dict[str, Any]) -> bool:
    """准入闸门：fork 默认剔除（SOP 6 第1层⑤）。

    其他准入条件（有版本/活跃/有 README）需要额外 API 调用，本次地基
    仅做"fork 默认剔除"这个不依赖额外 API 的硬规则。MariaDB 这类
    "fork 已独立发展且 star 远超原项目"的例外，由白名单兜底（白名单
    会强制纳入，不经过此过滤）。
    """
    if item.get("fork") is True:
        return False
    if item.get("archived") is True:
        # archived = 已归档（停止维护），剔除
        return False
    return True


# ============================================================
# 工程语言过滤（SOP ②降噪 + 6.x 通用降噪）
# ============================================================
def is_engineering_language(item: dict[str, Any]) -> bool:
    """主语言属工程语言白名单。None 视为不通过（无法判定）。"""
    lang = item.get("language")
    if not lang:
        return False
    return lang in config.ENGINEERING_LANGUAGES


# ============================================================
# 第 3 层：内容相关性（新生项目专用 —— SOP 6.x 第③层）
# ============================================================
def is_db_relevant(item: dict[str, Any]) -> bool:
    """description / topics 含数据库核心词。

    SOP 6.x 第③层：挡伪相关（记账 app 打了 postgresql 标签但本身不是数据库项目）。
    判定：description 或 topics 含 DB 核心词之一即视为相关。
    """
    text = _text_of(item, "description")
    topics = " ".join(str(t).lower() for t in (item.get("topics") or []))
    hay = f"{text} {topics}"
    if not hay.strip():
        return False
    return any(kw.lower() in hay for kw in config.DB_KEYWORDS)


# ============================================================
# 展示相关性过滤（SOP 6.y 第二层分工 —— ①⑤⑧防"用了数据库但非数据库项目"霸屏）
# ============================================================
# 强核心词：description 含这些精确 token → 视为"本身是数据库相关"。
# 区别于 DB_KEYWORDS（后者用于②新生内容过滤，含产品名做子串匹配较宽）：
#   - STRONG 用精确 token，避免 "postgreSQL pool" 这类工具被产品名宽松命中
#   - 补数据库品类词（search/tsdb/kv/列存/数仓），挡 meilisearch/tdengine/victoriametrics 误杀
#
# 设计权衡：曾尝试把 search/query/migration 等泛词"降级"（单独命中剔除），
# 但实测会误杀 meilisearch/StarRocks/dicedb/arquero 等真数据库——这些引擎的
# description 本就只有 "search engine"/"query engine" 而无产品名。故保留泛词为强词，
# 改用下面的业务领域黑名单做二次校验（只挡"用数据库做别的事"的伪相关）。
_DISPLAY_STRONG = {
    # 通用概念
    "database", "sql", "query", "queries", "dba", "olap", "oltp",
    "migration", "schema", "vector", "warehouse",
    # 产品/引擎名
    "postgres", "postgresql", "mysql", "mongo", "mongodb", "redis",
    "clickhouse", "duckdb", "tidb", "oceanbase", "opengauss", "polardb",
    "mariadb", "sqlite", "oracle", "sqlserver", "dynamodb", "spanner",
    # 数据库品类词（搜索引擎/时序/键值/列存 均属 DB 范畴）
    "search", "timeseries", "tsdb", "keyvalue",
}
# 复合词（含连字符/空格，token 正则会拆开，单独匹配）
_DISPLAY_COMPOUND = [
    "time-series", "time series", "in-process", "in-memory", "in memory",
    "key-value", "graph database",
]
# 中文数据库核心词（description 中文写法）
_DISPLAY_CN = ["数据库", "存储引擎", "搜索引擎", "时序", "查询", "迁移", "备份", "代理", "连接池"]

# ---- 业务领域黑名单（二次校验，仅对"无 DB 身份短语"的边缘项生效）----
# 只收无歧义的强业务词 —— 排除会被真数据库用到的歧义词（store=存储/商店、bot、shop 等）。
# 语义：项目"靠 search/query/migration 等泛词弱命中 + description 主体是非数据库业务"
#       → 判定伪相关剔除。挡 dm/tidb 等缩写 topic 带入的社交/电商/招聘/游戏类伪相关。
# 注意：真库已由 _DISPLAY_DB_IDENTITY 身份短语层先行保护，这里的词不会误伤它们。
_DISPLAY_BIZ_DOMAINS = {
    # 社交平台名（专有名词，无歧义）
    "discord", "telegram", "whatsapp", "instagram", "tiktok", "wechat",
    "weverse", "kpop", "twitter", "x.com",
    # 明确的非 DB 业务词
    "e-commerce", "ecommerce", "job-portal", "job-board", "dating",
    "minecraft", "duelmasters", "chess",
    # 爬虫（抓数据而非存/查数据的工具）
    "scraper", "crawler",
}
_DISPLAY_BIZ_DOMAINS_CN = [
    "电商", "商城", "旅游", "景点", "酒店", "预订", "招聘", "求职",
    "外卖", "配送", "网校", "网课", "考试系统", "民宿", "机票", "旅游住宿",
]

# ---- 数据库身份短语（真库保护层）----
# description 自指为"是个数据库/存储引擎/某品类 DB"时，视为真数据库，
# 业务黑名单与应用身份检测都不再适用。
# 保护 wcdb(database framework)、evitaDB(database engine, 用于 e-commerce 场景)、
# snkv(key-value store, 带个 discord topic)这类"开发方/目标场景/无关 topic 触发
# 业务词"的真库 —— 它们会被 _DISPLAY_BIZ_DOMAINS 误判伪相关。
_DISPLAY_DB_IDENTITY = [
    # 英文自指身份短语
    "is a database", "is an in-memory", "database engine",
    "database framework", "storage engine", "object-relational",
    "key-value store", "key value store", "key-value database",
    "document store", "document database", "columnar",
    "column-oriented", "column store", "nosql", "newsql",
    "graph database", "vector database", "time-series database",
    "in-memory database", "in-memory data", "relational database",
    # 中文身份词
    "数据库引擎", "存储引擎", "向量数据库", "时序数据库",
    "图数据库", "列式存储", "键值数据库", "文档数据库",
]

# ---- 应用身份检测（清"用数据库的应用"，仅对无 DB 身份短语的项目生效）----
# ⚠️ 实测此层无法做到零误杀：website/boilerplate/template/manager/store 等词既被
#    真数据库工具（sqlitebrowser=db browser、dbgate=database manager、seafowl=analytical
#    database for web apps）使用，也被非数据库应用使用，子串匹配无法区分。
#    收紧后仍误杀 ~450 个真工具。故此常量保留为空列表（禁用该层），改由业务黑名单 +
#    DB 身份保护两层组合过滤。如未来需复活，须配合"否定上下文"（如 website 且不含
#    database manager / browser 等 DB 工具词）才行。
_DISPLAY_APP_IDENTITY: list[str] = []


def is_display_relevant(item: dict[str, Any]) -> bool:
    """判断项目是否"本身是数据库相关"，用于①⑤⑧展示过滤。

    SOP 6.y：一个项目可能靠 topic 弱命中（plane 打了 postgresql 标签，或 dm/tidb
    这类缩写 topic 命中 Discord/Telegram 机器人）混进候选池，但本质是非数据库业务。
    这类在展示榜（①上涨/⑤总榜/⑧AI）应剔除，避免霸屏。

    判定（强词命中后逐层校验，顺序敏感）：
      1. 来源是白名单/org（人工确认的内核/生态，权威，直接留）
      2. full_name 命中 EXTRA_DB_REPOS（已知 DB 但 description 无技术词的兜底）
      3. full_name 命中 DISPLAY_BLOCK_REPOS（精确黑名单，兜底无业务词的伪相关）
      4. description 含强核心词（精确 token）/ 复合词 / 中文数据库词 → 否则剔除
      5. DB 身份短语命中（_DISPLAY_DB_IDENTITY）→ 真 DB，直接留（保护层）
      6. 业务领域黑名单命中（description+topics）→ 伪相关剔除
      7. 应用身份检测（_DISPLAY_APP_IDENTITY，当前为空→禁用）→ 见常量说明
      8. 其余（含产品名锚点的真 DB 工具）→ 留

    设计理由：早期版本"有产品名锚点就放行"，但 description 里出现 postgres/
    database 这类词，既可能是真 DB 工具，也可能只是"用了 PG 的约会网站"。
    纯靠锚点无法区分（pH7-CMS 的 desc 就含 "database"）。故改为：
      - 先用"DB 身份短语"（is a database / database engine / key-value store …）
        保护 wcdb/evitaDB/snkv 这类真库（其目标场景/开发方/无关 topic 会触发业务词）；
      - 再跑业务黑名单（dating/电商/克隆…），挡 pH7-CMS 这类"用 DB 做业务"的。
    应用身份检测层经实测无法做到零误杀（website/boilerplate/manager 等词被真工具
    sqlitebrowser/dbgate/seafowl 共用），故 _DISPLAY_APP_IDENTITY 置空禁用 —— 宁可漏
    remix-words-funny 这类无业务词的应用，也不误杀真工具。已用 13236 项真实数据验证：
    pH7-CMS/remix-words-funny 中 pH7-CMS 被清，真库（wcdb/evitaDB/snkv/rocksdb/
    clickhouse/duckdb/meilisearch/surrealdb/chroma 等）全保留，零误杀。

    与②新生用的 is_db_relevant 区别：后者偏宽（挡明显伪相关即可，新生池本就小）；
    本函数更严（展示榜是门面，宁可漏少数边缘项目也不让伪相关霸屏）。
    """
    src = item.get("source")
    if src in ("whitelist", "org"):
        return True
    full = (item.get("full_name") or "").lower()
    if full in {r.lower() for r in config.EXTRA_DB_REPOS}:
        return True
    # 精确 repo 黑名单（对称于白名单，兜底"无业务词、纯靠产品名命中"的伪相关）
    if full in {r.lower() for r in config.DISPLAY_BLOCK_REPOS}:
        return False
    desc = (item.get("description") or "")
    if not isinstance(desc, str):
        return False
    low = desc.lower()
    toks = set(_re.findall(r"[a-z0-9]+", low))
    # 强核心词 / 复合词 / 中文词 命中
    strong_hit = (
        bool(toks & _DISPLAY_STRONG)
        or any(kw in low for kw in _DISPLAY_COMPOUND)
        or any(kw in low for kw in _DISPLAY_CN)
    )
    if not strong_hit:
        return False
    # ---- DB 身份短语保护层：description 自指为数据库/存储引擎 → 真 DB，留 ----
    # 保护 wcdb(database framework) / evitaDB(database engine) / snkv(key-value store)
    # 这类"目标场景/开发方/无关 topic 触发业务黑名单词"的真库。
    if any(phrase in low for phrase in _DISPLAY_DB_IDENTITY):
        return True
    # ---- 业务领域黑名单：description+topics 含非 DB 业务词 → 伪相关剔除 ----
    # 不再因"有产品名锚点"提前返回（旧 bug：pH7-CMS 的 desc 含 database 就放行，
    # 跳过了这里的 dating 校验）。真库已由上面的身份短语层保护。
    topics_text = " ".join(str(t).lower() for t in (item.get("topics") or []))
    hay = f"{low} {topics_text}"
    for bw in _DISPLAY_BIZ_DOMAINS:
        if _token_hit(hay, bw):
            return False
    for cw in _DISPLAY_BIZ_DOMAINS_CN:
        if cw in low:
            return False
    # ---- 应用身份检测（当前 _DISPLAY_APP_IDENTITY 为空 → 此层禁用）----
    # 经实测此层无法零误杀（见常量说明），故置空。保留代码位置，便于未来配合
    # 否定上下文复活（如 website 且不含 database manager/browser 等 DB 工具词）。
    if any(kw in low for kw in _DISPLAY_APP_IDENTITY):
        return False
    return True


def filter_display_pool(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """对候选池做展示相关性过滤，返回过滤后的池（原地不动，返回新列表）。

    采集层候选池保持全量（license/release 采集等需要全量），仅展示榜用过滤后的池。
    """
    return [it for it in pool if is_display_relevant(it)]


# ============================================================
# 采集后分类标注（SOP 4.9.4 —— 关键词用于分类，不用于拆分）
# ============================================================
def classify(item: dict[str, Any]) -> list[str]:
    """根据 description / topics 标注分类标签（ai / tool / core 之一或多个）。

    返回 list，调用方可据此归入⑦生态工具栏或⑧AI 板块。
    这是"采集后标注"，不影响是否采集。
    """
    text = _text_of(item, "description", "topics")
    tags: list[str] = []
    if any(kw in text for kw in config.AI_KEYWORDS):
        tags.append("ai")
    if any(kw in text for kw in config.TOOL_KEYWORDS):
        tags.append("tool")
    # core = 无 tool/ai 关键词的，默认视为内核/通用（调用方可结合白名单再判）
    if not tags:
        tags.append("core")
    return tags


def annotate_categories(items: list[dict[str, Any]]) -> None:
    """批量给 items 打 category 标签（原地修改）。"""
    for item in items:
        item["category"] = classify(item)


# ============================================================
# 新生项目降噪（SOP ② + 采集策略清单 第五步后置过滤）
# ============================================================
def filter_new_projects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """新生项目专用四层过滤：

    ① 工程语言（主语言非工程语言剔除）
    ② 黑名单（教程/作业/镜像/撞名）
    ③ 内容相关性（description 含 DB 核心词）
    ④ fork 默认剔除
    ⑤ 同作者批量建库只取 1 个（star 最高的那个）
    """
    out: list[dict[str, Any]] = []
    seen_full: set[str] = set()
    for item in items:
        full = item.get("full_name")
        if not full or full in seen_full:
            continue
        if not pass_gate(item):
            continue
        if not is_engineering_language(item):
            continue
        if is_blacklisted(item):
            continue
        if not is_db_relevant(item):
            continue
        out.append(item)
        seen_full.add(full)

    out = dedupe_same_author(out)
    return out


def dedupe_same_author(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """同作者批量建库只取 star 最高的 1 个（SOP ②降噪 + 6.x 通用降噪）。

    判定：同一 owner 下，若其项目在本批里 >= 3 个（批量建库特征），
    只保留 star 最高的 1 个。owner 项目数 < 3 的不动（正常作者多仓库）。
    """
    by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        full = item.get("full_name", "")
        if "/" in full:
            owner = full.split("/", 1)[0]
            by_owner[owner].append(item)

    keep: list[dict[str, Any]] = []
    for owner, repos in by_owner.items():
        if len(repos) < 3:
            # 正常作者，全留
            keep.extend(repos)
            continue
        # 批量建库：只留 star 最高
        repos.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
        keep.append(repos[0])
    return keep
