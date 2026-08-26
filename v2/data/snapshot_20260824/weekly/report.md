# 📋 数据库开源生态周报 · 第 3 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-08-24_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[db-backup](https://github.com/nfrastack/db-backup)（+1532）—— Backup multiple database types on a scheduled basis with man
- 🇨🇳 **国产数据库**：[bytebase](https://github.com/bytebase/bytebase)（+17）—— Database governance built for humans and agents — controllin
- 🤖 **AI工具**：[dbx](https://github.com/t8y2/dbx)（+1113）—— 20 MB lightweight cross-platform database client for 90+ dat



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[nfrastack/db-backup](https://github.com/nfrastack/db-backup)** · ⭐ 1.5k · 本周 **+1532**
> `备份` · 适用：SQL Server / DB2 / MySQL / PostgreSQL / MariaDB
> Backup multiple database types on a scheduled basis with many customizable optio
> 🤖 **AI 解读**：db-backup 支持多种数据库的定时备份，可配置压缩、加密、存储及通知，并提供恢复工具，适用于需自动化备份的数据库运维场景。

> 🥈 **[janbjorge/pgqueuer](https://github.com/janbjorge/pgqueuer)** · ⭐ 1.5k · 本周 **+1517**
> `其他` · 适用：PostgreSQL
> PostgreSQL-backed background job and task queue for Python.
> 🤖 **AI 解读**：PgQueuer是Python库，将PostgreSQL用作后台任务队列。支持事务性入队、并发安全、定时调度与监控，无需额外消息服务。

> 🥉 **[pgrundev/pgbot](https://github.com/pgrundev/pgbot)** · ⭐ 597 · 本周 **+597**
> `其他` · 适用：PostgreSQL
> Postgres intelligence for ai agents & apps
> 🤖 **AI 解读**：pgbot是PostgreSQL的只读诊断工具，以静态二进制连接数据库，读取统计视图并输出健康报告及变更对比，支持CI集成与MCP调用。

### 🌱 新锐发现（最多 3 个）

> ① **[imehdiha/cardpay](https://github.com/imehdiha/cardpay)** · ⭐ 17 · 本周 **+17**
> `连接/代理` · 适用：MySQL / MariaDB
> Self-hosted card-to-card payment gateway for PHP and MySQL with HMAC API, SMS ma
> 🤖 **AI 解读**：CardPay 是自托管支付网关，基于 PHP 和 MySQL/MariaDB，通过 HMAC API 与短信匹配确认交易，提供波斯语界面。对数据库使用者

> ② **[moriyoshi/pglite-go](https://github.com/moriyoshi/pglite-go)** · ⭐ 8 · 本周 **+8**
> `其他` · 适用：PostgreSQL
> Embedded PostgreSQL for Go — no external server, no libpq, no separate process.
> 🤖 **AI 解读**：pglite-go将PostgreSQL 18编译为WebAssembly，嵌入Go进程运行，无需外部服务。通过标准database/sql接口提供事务

> ③ **[dataglotai/dataglot](https://github.com/dataglotai/dataglot)** · ⭐ 8 · 本周 **+8**
> `管理` · 适用：Oracle / MySQL / PostgreSQL
> Rust-native federated SQL query engine with governance enforced in the query pla
> 🤖 **AI 解读**：Rust联邦SQL查询引擎，以PostgreSQL协议为入口，支持跨Oracle、MySQL、PostgreSQL联合查询，查询计划阶段实施列掩码与行过滤治理。

### 🔍 本周解读 · db-backup

> 🔍 **[nfrastack/db-backup](https://github.com/nfrastack/db-backup)** · ⭐ 1.5k · 本周 **+1532**
> `备份` · 适用：SQL Server / DB2 / MySQL / PostgreSQL / MariaDB
> Backup multiple database types on a scheduled basis with many customizable options

**解决什么**：解决多类型数据库定时备份与集中管理问题，支持自定义调度、压缩、加密及多存储目标，降低备份运维复杂度。

**核心亮点**：支持MySQL、PostgreSQL、MariaDB、SQL Server及多种非关系型数据库定时备份。提供cron、间隔调度，支持S3与Azure存储，具备GPG加密、压缩及失败通知功能。

**使用场景**：适用于需要统一管理多种数据库备份策略的运维团队，或对备份调度、存储位置、加密及监控有定制化需求的生产环境。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.4k · 本周 **+17**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access
> 🤖 **AI 解读**：Bytebase 是开源数据库治理平台，为人工与AI代理提供统一控制面，管理变更、访问与合规。支持多种数据库，提供GUI工作流

> 🥈 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 371 · 本周 **+10**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It offer
> 🤖 **AI 解读**：开源数据库管理工具，面向团队协作，提供访问控制、数据脱敏、SQL审计、CI/CD及跨地域部署，支持Oracle、MySQL、PostgreSQL、TiDB

> 🥉 **[polardb/langchain-polardb-pg](https://github.com/polardb/langchain-polardb-pg)** · ⭐ 10 · 本周 **+10**
> `其他` · 适用：PostgreSQL / PolarDB
> 🤖 **AI 解读**：langchain-polardb-pg是阿里云PolarDB for PostgreSQL的LangChain集成包，支持库内嵌入、向量存储与模型管理

### 🔍 本周解读 · bytebase

> 🔍 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.4k · 本周 **+17**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access across every major database.

**解决什么**：数据库变更与访问管控分散在多个工具中，导致流程割裂、权限失控且难以审计。Bytebase将变更管理、访问控制与合规记录统一到一个平台，为数据库操作提供单一控制面。

**核心亮点**：支持Oracle、SQL Server、MySQL、PostgreSQL、TiDB、OceanBase等十余种数据库；提供GUI变更工作流与GitOps集成；具备细粒度RBAC、临时授权与动态脱敏

**使用场景**：适用于需要规范化数据库变更流程的开发团队，需集中管理多环境数据库的DBA，以及要求列级权限控制与审计追踪的安全合规场景。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 16.4k · 本周 **+1113**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including My
> 🤖 **AI 解读**：20MB客户端支持90余种数据库，覆盖MySQL、PostgreSQL、SQL Server、DM等，提供桌面、Docker、CLI界面

> 🥈 **[TabularisDB/tabularis](https://github.com/TabularisDB/tabularis)** · ⭐ 4.2k · 本周 **+91**
> `平台` · 适用：9+种数据库（Oracle / SQL Server / DB2等）
> Open-source desktop SQL workspace for PostgreSQL, MySQL/MariaDB, SQLite and 15+ 
> 🤖 **AI 解读**：Tabularis是开源桌面SQL工作台，支持Oracle、SQL Server、DB2、MySQL、PostgreSQL、MariaDB

> 🥉 **[Canner/WrenAI](https://github.com/Canner/WrenAI)** · ⭐ 17.4k · 本周 **+84**
> `平台` · 适用：PostgreSQL / ClickHouse
> GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL throug
> 🤖 **AI 解读**：WrenAI是开源生成式BI引擎，经语义层将自然语言转SQL，支持20余种数据源，供AI代理生成受治理的仪表盘与图表。

### 🌱 新锐发现（最多 3 个）

> ① **[fj1981/dqex](https://github.com/fj1981/dqex)** · ⭐ 5 · 本周 **+5**
> `迁移` · 适用：Oracle / MySQL / PostgreSQL
> AI-Native, Offline-First Database Workbench — Import/Export/Migrate/Compare/Snap
> 🤖 **AI 解读**：dqex为跨平台数据库工作台，单文件分发，支持离线。提供MySQL、PostgreSQL、Oracle的导出、导入、迁移、比对及AI辅助SQL编写

> ② **[lilee-LI/database-langchain-gaussdb-sync](https://github.com/lilee-LI/database-langchain-gaussdb-sync)** · ⭐ 0 · 近7天 8 commits
> `迁移` · 适用：GaussDB
> GaussDB vector store and chat message history integrations for LangChain.
> 🤖 **AI 解读**：该工具为LangChain提供GaussDB向量存储与聊天历史集成，支持集中式部署的稠密、BM25及混合检索，分布式部署支持稠密检索。

### 🔍 本周解读 · dbx

> 🔍 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 16.4k · 本周 **+1113**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including MySQL, PostgreSQL, SQLite, Redis, MongoDB,

**解决什么**：20MB安装包支持90余种数据库连接，涵盖MySQL、PostgreSQL、文件库、内存库、文档库、分析库、SQL Server、达梦等，提供桌面端、Docker、CLI三种形态

**核心亮点**：内置AI助手辅助生成与解释查询语句；集成MCP Server供外部AI调用；单文件分发，支持桌面端、Docker、命令行；覆盖Oracle、SQL Server、DB2、MySQL

**使用场景**：适用于需同时管理多种数据库的开发运维人员，可在资源受限容器或远程服务器中通过Docker或CLI操作，支持将查询能力经MCP Server接入AI工作流，也适合桌面端日常多库巡检与数据浏览。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.4k | 国外数据库 | 监控 | The open and composable observability and data visualization platform. |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.5k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.2k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL gen |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.0k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and SQL |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.6k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-08-24）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
