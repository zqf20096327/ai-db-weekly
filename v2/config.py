"""配置中心 —— 所有可调参数集中在此。

加 topic / 调阈值 / 加黑名单 / 改路径，都只改这个文件，不动业务代码。
依据：数据库开源周报-SOP.md（第二章 topic、第四章采集架构、第五章信源、第六章筛选）
     采集策略清单.md（实测规模表、各级 topic 采法）
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

# ============================================================
# 路径（基于本文件所在目录，不依赖 CWD —— 保证 CI 和本地一致）
# ============================================================
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ENV_FILE = os.path.join(HERE, ".env")

# 快照日期：UTC YYYYMMDD（与 SOP 4.6 存储结构一致，旧脚本用 YYYY-MM-DD 不向后兼容）
TODAY = datetime.now(timezone.utc).strftime("%Y%m%d")
TODAY_HUMAN = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def snapshot_dir(date: str | None = None) -> str:
    """当天快照根目录：data/snapshot_YYYYMMDD/"""
    return os.path.join(DATA_DIR, f"snapshot_{date or TODAY}")


# ============================================================
# Topic 范围（SOP 2.1 —— 16 个 topic，不区分大小写）
# ============================================================
TOPICS = [
    "database",
    "oracle",
    "mysql",
    "postgresql",
    "mariadb",
    "sqlserver",
    "opengauss",
    "tidb",
    "oceanbase",
    "tdsql",
    "polardb",
    "polardb-x",
    "yashandb",
    "goldendb",
    "gbase",
    "dm",
]

# 四大"泛库"topic —— 仅这四个做互斥去重（SOP 4.9.1）
# 国产库 topic 不互斥：量小直接全采，且常打上游标签会被互斥误杀
BIG_FOUR = ["database", "mysql", "postgresql", "oracle"]

# 中型 topic —— 不互斥，但量较大需按 star 档位拆（采集策略清单 第二步）
# mariadb ~5.4k / sqlserver ~4.7k（实测 2026-08-05）
MEDIUM_NON_EXCLUDE = ["mariadb", "sqlserver"]


def _exclusion_expr(self_topic: str) -> str:
    """生成 BIG_FOUR 互斥的减号语法（GitHub 不支持 NOT，会返回 422）。

    每个 topic 排除其他三个：database 互斥 = topic:database -topic:mysql ...
    """
    others = [t for t in BIG_FOUR if t != self_topic]
    return " ".join(f"-topic:{t}" for t in others)


MUTUAL_EXCLUDE = {t: _exclusion_expr(t) for t in BIG_FOUR}


# ============================================================
# 量级判定与分级阈值（采集策略清单 第一步 量级判定规则）
# ============================================================
SIZE_THRESHOLDS = {
    "empty": 0,       # == 0：空，记录"无项目"跳过
    "micro": 100,     # <= 100：微型，直接全采一次取完
    "small": 1000,    # <= 1000：小型，直接全采 + 分页
    # > 1000：巨型/中型，三层拆分
}


def classify_tier(total_count: int) -> str:
    """按 total_count 判定量级，决定采法。"""
    if total_count == 0:
        return "empty"
    if total_count <= SIZE_THRESHOLDS["micro"]:
        return "micro"
    if total_count <= SIZE_THRESHOLDS["small"]:
        return "small"
    return "big"  # 巨型/中型统一走三层拆分


# ============================================================
# 采集参数（SOP 第四章 + 采集策略清单 全局规范）
# ============================================================
# 快照全量下限（采集策略清单：star<10 占 94% 是噪音，采集时就挡掉省 90% 调用）
STAR_MIN_SNAPSHOT = 10

# 新生项目池下限（SOP ②新生项目榜：30天内创建 + star >= 3）
STAR_MIN_NEW = 3
NEW_PROJECT_DAYS = 30

# GitHub Search 硬限制（采集策略清单 全局规范）
SEARCH_MAX_RESULTS = 1000  # 单次查询 per_page=100 × 最多 10 页
PER_PAGE = 100
MAX_PAGES = 10

# 限流（采集策略清单 全局规范 —— 动态限流，不固定 sleep）
RATE_LIMIT = {
    "search_per_min": 30,        # Search API（瓶颈！）
    "core_per_hour": 5000,       # Core API（充足）
    "min_interval_sec": 2,       # 正常调用间隔
    "safety_remaining": 5,       # 剩余 <= 此值则 sleep 到 reset
}

# 数据源4：commit 活跃度（SOP ③活跃度 → ⑤总榜🔥标签）
COMMIT_LOOKBACK_DAYS = 7
# 近 7 天 commit 达此阈值 → 打 🔥 标（SOP ③，初值待校准）
COMMIT_ACTIVITY_THRESHOLD = 10
# participation 接口异步轮询（SOP 4.2 数据源4 警告：首次常返回 202）
PARTICIPATION_POLL_MAX_RETRIES = 3
PARTICIPATION_POLL_INTERVAL_SEC = 5

# 按需采集（数据源4）只对候选池采，控制规模 —— 这里给候选池采样上限避免对 15000 项目全量调
# SOP 原意"对候选池项目采"，候选池已含白名单+topic 去重合并结果
# 4000 约占候选池 star 头部 30%，覆盖率与成本（Core API 5000/小时）的折中。
# 提升时留意：每项 ~1 次 participation 调用，超 5000 会触发 sleep 到配额重置（不出错，变慢）
COMMIT_ACTIVITY_MAX_REPOS = 4000  # 安全上限，超出按 star 降序截断


# ============================================================
# 关键词（SOP 4.9.4 —— 用于采集后分类标注，不用于主拆分）
# ============================================================
# 生态工具关键词（SOP ⑦生态工具栏）
TOOL_KEYWORDS = [
    "proxy", "pooler", "ha", "migration", "backup",
    "client", "operator", "orm", "etl", "sync",
]

# AI 板块关键词（SOP ⑧AI 能力专题，8 个）
AI_KEYWORDS = [
    "llm", "agent", "skill", "mcp", "text2sql", "nl2sql", "copilot", "ai-dba",
]

# 数据库核心词（SOP ②内容相关性 / 6.x 第③层 后置过滤）
# 用于判定项目"本身是数据库相关"。补全了 SOP 4.2 原词表缺失的产品名
# （oracle/sqlserver/mariadb 等），否则 oracle 生态真工具（如 go-ora 驱动）
# 会被误判为不相关。
DB_KEYWORDS = [
    # 通用概念
    "database", "sql", "query", "dba", "schema", "vector",
    "olap", "oltp", "migration",
    # 产品/引擎名（含国产）
    "postgres", "mysql", "mongo", "redis", "mariadb",
    "oracle", "sqlserver", "sqlite", "clickhouse",
    "tidb", "oceanbase", "opengauss", "polardb", "duckdb",
]


# ============================================================
# 黑名单（SOP 6 第2层 —— 命中任一即剔除）
# ============================================================
BLACKLIST_KEYWORDS = [
    # 教程 / 学习类
    "教程", "学习", "笔记", "面试", "面试题", "awesome", "course",
    "tutorial", "learning", "guide", "handbook", "cookbook", "实战", "课件",
    # 作业 / 培训类
    "educoder", "experiment", "homework", "lab", "高校", "大学", "训练",
    "比赛", "race", "contest", "exam",
    # 镜像 / 搬运类
    "mirror", "docs", "site", "website", "homepage", "blog", "-cn",
]


# ============================================================
# 工程语言白名单（SOP ②降噪 + 6.x 通用降噪：主语言非工程语言剔除）
# ============================================================
ENGINEERING_LANGUAGES = {
    "C", "C++", "Go", "Rust", "Java", "Python", "Scala", "Kotlin",
    "JavaScript", "TypeScript", "C#", "Ruby", "PHP", "Swift", "D",
    "Elixir", "Erlang", "Haskell", "OCaml", "Zig", "Crystal",
    "Shell",  # 部分数据库工具是 Shell（如 mydumper 周边）
}


# ============================================================
# 白名单内核 repo（SOP 5.1 —— 固定追踪核心 repo，topics 为空的靠此补采）
# ⚠️ 必须手工确认是官方源而非镜像/撞名
# ============================================================
WHITELIST_REPOS = [
    # 国际主流关系库
    "mysql/mysql-server",
    "postgres/postgres",
    "MariaDB/server",
    "sqlite/sqlite",
    # NewSQL
    "pingcap/tidb",
    "tikv/tikv",
    "oceanbase/oceanbase",
    "cockroachdb/cockroach",
    # 嵌入式 / 分析
    "duckdb/duckdb",
    # 国产-PG系（⚠️ 官方源，非 math-inc/OpenGauss 撞名 Python 项目）
    "opengauss-mirror/openGauss-server",
    # 国产-阿里
    "polardb/PolarDB-for-PostgreSQL",
    "polardb/polardbx-engine",
    # ⚠️ 待确认（Oracle闭源/TDSQL/YashanDB/GoldenDB/GBase/DM 部分在 Gitee）
    # 确认后追加到此处
]


# ============================================================
# 展示相关性兜底（filters.is_display_relevant 用）
# ============================================================
# 已知本身是数据库但 description 无强技术词的项目（靠业务定位词描述，如 nocodb=Airtable alternative）。
# 这类靠 topic 命中进候选池，展示过滤会误剔除，故手工兜底。
# 后期发现新的"真 DB 但 description 不含技术词"项目，追加到此即可。
EXTRA_DB_REPOS = [
    "nocodb/nocodb",          # 无代码数据库表（description: Airtable alternative）
    "etcd-io/etcd",           # 分布式 KV 存储（基础设施）
    "revoltapi/revolt",       # （如未来发现类似项目）
]

# 展示精确黑名单（filters.is_display_relevant 用，对称于 EXTRA_DB_REPOS 白名单）。
# 个别项目靠 topic 命中进候选池，description 既无 DB 身份短语也无业务黑名单词，
# 纯靠"产品名锚点 + 当技术栈列出"溜进展示榜（如背单词网站 desc 只写 postgresql）。
# 这类无法用关键词层零误杀地过滤，故精确到 repo 兜底。发现新的追加到此即可。
DISPLAY_BLOCK_REPOS = [
    "SteveSuv/remix-words-funny",  # 背单词网站，desc 只把 postgresql 当技术栈列出
]


# ============================================================
# Org 扫描清单（SOP 5.2 / 数据源6 —— 补 topics 为空的内核漏采）
# 走 Core API 5000/小时，不占 Search 限流
# ============================================================
ORG_SCAN_LIST = [
    "mysql",            # mysql/mysql-server 等 24 个（topics 为空的内核在此）
    "polardb",          # PolarDB 全家桶（topic:polardb 只有4个，org 补全）
    "ApsaraDB",         # 阿里云数据库工具生态
    "oceanbase",        # OceanBase 内核 + 工具
    "opengauss-mirror", # openGauss 系（topics 为空，靠 org）
    "pingcap",          # TiDB 生态
    "tikv",             # TiKV 生态
]


# ============================================================
# 周报生产参数（SOP 第四章"每周一次" + 第三章栏目口径 + ④信号分 + 6评分卡）
# ============================================================

# ----- 数据源3 Release（SOP 4.2 / 4.3 每周采，按需）-----
# 只对"白名单 + 上涨榜前 N"项目拉 release（SOP 4.3）。候选池很大，
# 默认按 star 降序取头部，避免对 15000 项目全量调 releases。
RELEASE_LOOKBACK_DAYS = 7        # published_at > N 天前 才算"本周发版"
RELEASE_PER_PAGE = 30            # 单 repo 取多少条（近 N 天量小）
RELEASE_MAX_REPOS = 200          # 安全上限：候选池按 star 截断后最多采这么多 repo

# ----- 数据源5 License 变更检测（SOP 4.2 / 4.3 每周采，按需）-----
LICENSE_LOOKBACK_DAYS = 7        # LICENSE 文件 since=N 天前
LICENSE_MAX_REPOS = 200          # 同 release，候选池按 star 截断

# ----- ④本周重点 信号分（SOP ④，权重为初值，每周跑完按 SOP 提示校准）-----
SIGNAL_WEIGHTS = {
    "major_version": 40,         # 当周发布主版本号变更（如 18→19）
    "star_anomaly": 30,          # 当周 star 净增进入快速上涨榜前 3
    "first_entry":   25,         # 首次入榜 / star 破阈值
    "license_change": 25,        # 当周 license 发生变化
    "activity_spike": 15,        # commit/PR 量较前周显著上升
}
# 影响面加权系数（SOP ④：现有 star 越高，同样事件影响越多人）
# 分档乘数：star < 1k ×1.0 / 1k-10k ×1.2 / 10k-50k ×1.5 / ≥50k ×2.0
SIGNAL_STAR_MULTIPLIER = [
    (1_000, 1.0),
    (10_000, 1.2),
    (50_000, 1.5),
    (float("inf"), 2.0),
]
# 每周取信号分最高的前 N 个项目作"本周重点"（SOP：最多 2 个）
FOCUS_MAX_ITEMS = 2

# ----- ①快速上涨榜 口径（SOP ①）-----
RISING_EXCLUDE_TOPN = 5          # 排除总榜前 N（只看腰部黑马）
RISING_TOPN = 5                  # 快速上涨榜展示条数（模板：top5）

# ----- ③活跃度 🔥 阈值（已由 COMMIT_ACTIVITY_THRESHOLD 复用，见上方数据源4）-----
# 留意：is_active 字段在采集层已打好，渲染层直接读

# ----- ⑤总榜 展示条数（SOP ⑤，背景板）-----
TOPBOARD_LIMIT = 10

# ----- ②新生项目 双档阈值（SOP ②双档展示分流）-----
NEW_RISING_STAR_MAX = 30         # 新星榜：star 3 ~ 30（下限 STAR_MIN_NEW=3）
NEW_POTENTIAL_STAR_MIN = 30      # 潜力榜：star ≥ 30
NEW_LIST_LIMIT = 5               # 每档展示条数（模板：各 top5）


# ============================================================
# 周报新架构参数（双篇：主周报 + 工具合辑周报）
# 设计依据：编辑策展型漏斗结构 + DBA 工具视角 + 数据边界（内核以厂商为准）
# ============================================================

# ----- 数据边界：数据库内核 repo 黑名单 -----
# 规则：内核库的版本/发版/活跃度以厂商官方渠道为准，周报不报。
# 这些 repo 在"快速上涨/活跃榜/版本速递/新生/Top"动态类栏目中一律剔除（Top 例外，
# 保留排名但标注品类，作全景背景板）。
KERNEL_REPOS = {
    # 国际主流关系/嵌入式
    "postgres/postgres", "mysql/mysql-server", "MariaDB/server", "sqlite/sqlite",
    "redis/redis", "mongodb/mongo", "cockroachdb/cockroach",
    # NewSQL / 分布式
    "pingcap/tidb", "tikv/tikv", "oceanbase/oceanbase",
    "yugabyte/yugabyte-db", "ydb-platform/ydb", "apache/cassandra",
    # 分析 / 列存 / 时序
    "ClickHouse/ClickHouse", "duckdb/duckdb", "taosdata/TDengine",
    "VictoriaMetrics/VictoriaMetrics", "databendlabs/databend",
    "GreptimeTeam/greptimedb", "StarRocks/starrocks", "apache/doris",
    # KV / 图 / 搜索 / 多模 / 嵌入式
    "etcd-io/etcd", "facebook/rocksdb", "arangodb/arangodb",
    "scylladb/scylladb", "dragonflydb/dragonfly", "surrealdb/surrealdb",
    "valkey-io/valkey", "dgraph-io/dgraph", "dgraph-io/badger",
    "meilisearch/meilisearch", "vesoft-inc/nebula", "FalkorDB/FalkorDB",
    "codenotary/immudb", "apache/kvrocks", "isar/isar",
    "skytable/skytable", "tursodatabase/turso", "tursodatabase/libsql",
    "get-convex/convex-backend", "couchbase/couchbase-lite-ios",
    # 国产内核（主阵地在 Gitee / 厂商官网）
    "opengauss-mirror/openGauss-server",
    "polardb/PolarDB-for-PostgreSQL", "polardb/polardbx-engine",
}

# ----- 导语 / 精选解读 阈值（编辑策展）-----
ANOMALY_RISE_STAR = 100          # star 净增 ≥ 此值 → 判为"异常上涨"（导语 + 精选候选）
DYNAMIC_STAR_MIN = 5             # star 净增 > 此值 → 算"有动态"（工具合辑体检表）
DYNAMIC_COMMIT_MIN = 1           # 近7日 commit ≥ 此值 → 算"有动态"（工具合辑体检表）

# ----- 工具合辑周报：新晋工具门槛 -----
# 不在标杆清单、但本周"有发版 或 star涨幅≥ANOMALY_RISE_STAR/2"的工具 → 纳入"新晋"
NEWCOMER_STAR_MIN = 50

# ----- 主周报 各栏条数 -----
FOCUS_DEEPDIVE_COUNT = 3         # 精选解读条数（不足时降级补发版+star头部）
TOOL_DIGEST_LIMIT = 8            # 工具动态速递条数
AI_SECTION_LIMIT = 5             # AI 能力专题条数


# ----- 主版本号变更判定（SOP ④"重大版本 +40"）-----
# 比较当周发版 tag 与上一个 tag 的主版本号（major），如 18→19 / 4.5→4.6
# 仅当 major 数值上升时计为"重大版本"

# ============================================================
# AI 配置（DeepSeek；.env 有 AI_API_KEY/AI_BASE_URL/AI_MODEL）
# ============================================================
AI_BASE_URL_DEFAULT = "https://api.deepseek.com"
AI_MODEL_DEFAULT = "deepseek-chat"
AI_TIMEOUT_SEC = 60          # DeepSeek 调用超时
AI_MAX_TOKENS = 800          # 单次解读返回上限
AI_TEMPERATURE = 0.3         # 低温度=偏保守/客观


# ============================================================
# 新 SOP 三板块周报参数（板块归属 / 8 分类 / 适用数据库 / 排除 / 选取）
# 依据：deepseek SOP 文本 §3.1（板块归属）/ §3.3（排除）/ §3.4（分类）/ §3.5（适用数据库）
#       §3.6（活跃榜）/ §3.7（新锐发现）
# 与上方"周报生产参数""周报新架构参数"并列；旧 report/toolkit 渲染逻辑已停用
# ============================================================

# ----- §3.1 三板块归属关键词（命中顺序：国产 > AI > 国外，命中即停）-----
# 国产：国产数据库产品名（ distinctive，token 匹配）。不含 "dm"（太短，命中 admin/odm）
SECTION_KEYWORDS = {
    "国产数据库": [
        "doris", "tidb", "oceanbase", "opengauss", "starrocks",
        "polardb", "gaussdb", "tdsql", "yashandb", "goldendb", "gbase",
    ],
    # 国外：DB 通用词 + 主流国外 DB 产品名（宽口径，作为非国产/AI 的残留桶；
    #       噪音由 is_display_relevant 上游过滤兜住）
    "国外数据库": [
        "database", "postgres", "postgresql", "mysql", "mariadb", "sqlite",
        "oracle", "clickhouse", "mongodb", "redis", "mssql", "sql server",
        "sql", "db", "query", "backup", "migration", "monitoring",
        "high-availability", "high availability",
        "connection-pool", "connection pool", "proxy",
    ],
}

# ----- AI 板块判定专用（§3.1 AI 支 + 防子串污染分层设计）-----
# 裸 "ai"/"rag" 子串会爆炸："ai" 命中 available/detail/main；
# "rag" 命中 storage（DB 工具最高频词）/coverage/fragile。
# 故分三层：topics 精确集合 → AI_KW_STRONG 子串 → AI_KW_TOKEN 词边界。
AI_TOPICS = {
    # topics 天然是 token，最可靠。不含裸 "ai"——实测被滥用（dbeaver/clickhouse/
    # meilisearch 都打 ai topic 做 SEO），靠下方具体范式词精确识别
    "artificial-intelligence", "llm", "large-language-models", "nlp",
    "text-to-sql", "text2sql", "nl2sql", "chat2db",
    "mcp", "model-context-protocol", "agent", "agents", "rag", "copilot",
    "gpt", "chatgpt", "openai", "langchain", "llama", "qwen", "deepseek",
}
# 强信号词：够独特，子串匹配也安全（含连字符/空格的短语走子串）
AI_KW_STRONG = [
    "llm", "mcp", "text2sql", "nl2sql", "langchain",
    "chatgpt", "openai", "deepseek", "copilot", "chat2db",
    "model-context-protocol", "ai-dba", "text-to-sql",
    "natural-language", "natural language",
]
# 弱信号词：纯单词，tokenize 后匹配独立词（防子串污染：rag→storage/coverage，
#   agent→pgagent/sqlagent 调度器，glm→统计学广义线性模型）。
#   不含裸 "ai"（"AI-powered" 等 AI washing 词会 tokenize 出 ai，误收面太大）
AI_KW_TOKEN = {
    "rag", "glm", "gpt", "agent", "llama", "qwen",
}

# ----- §3.4 八分类枚举（固定值，不可新增；多命中取最先；无命中→其他）-----
CATEGORY_KEYWORDS = {
    "高可用": ["ha", "high availability", "high-availability", "failover",
                "cluster", "replication", "patroni", "repmgr"],
    "监控": ["monitor", "alert", "slow query", "metrics", "grafana",
              "prometheus", "observability"],
    "备份": ["backup", "restore", "pitr", "wal", "pgbackrest", "xtrabackup"],
    "管理": ["manage", "governance", "sql review", "audit", "compliance",
              "access control", "bytebase"],
    "迁移": ["migrate", "sync", "cdc", "etl", "debezium", "replicate",
              "schema change"],
    "连接/代理": ["pool", "proxy", "load balance", "pgbouncer", "connection",
                  "gateway"],
    "平台": ["platform", "dbaas", "cloud", "managed", "supabase",
              "dashboard", "console"],
    # "其他" 不在此表 —— 由 infer_category 兜底返回
}

# ----- §3.5 适用数据库推断（从 topics/description 提取产品名）-----
# 注：子串匹配。"pg" 不收（命中 upgrade/padding）；用 postgresql/postgres。
APPLICABLE_DB_KEYWORDS = {
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "ClickHouse": ["clickhouse"],
    "Oracle": ["oracle"],
    "SQLite": ["sqlite"],
    "SQL Server": ["mssql", "sql server", "sqlserver"],
    "MariaDB": ["mariadb"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
}
DATABASE_MULTI_HINTS = ["40+", "multiple databases", "multi-database", "various databases"]

# ----- §3.3 排除规则（叠加在 filters.is_display_relevant 之上）-----
# 不放裸 "platform"/"deploy"/"cloud"（会误杀 DB 平台/监控类工具）；
# 只收无歧义的强信号：ORM 产品名、通用 PaaS 产品名、纯应用业务、教程模板。
SOP_EXCLUDE_KEYWORDS = {
    "orm_framework": ["prisma", "sequelize", "typeorm", "gorm"],
    "paas_deploy": ["vercel", "heroku", "netlify", "coolify", "paas",
                     "self-hostable", "deployment platform"],
    "app_layer": ["cms", "blog", "e-commerce", "ecommerce", "admin panel",
                   "admin-panel", "shopping cart"],
    "tutorial": ["tutorial", "boilerplate", "starter", "template",
                  "example", "examples", "demo", "learn",
                  "awesome list", "course"],
}

# ----- §3.6 / §3.7 选取条数 -----
SECTION_TOP_N = 3          # 各板块活跃榜 TopN（按 weekly_growth 降序）
NEWSTAR_DAYS = 7           # 新锐发现：created_at 或 pushed_at 在 N 天内
NEWSTAR_TOP_N = 3          # 新锐发现 TopN
TOPBOARD_TOP = 5           # 附录·总榜 TopN（历史 star 总数）
