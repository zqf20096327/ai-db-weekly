# AI×DB 周报

聚焦「AI 与数据库结合」的开源项目周报。每天自动采集 GitHub 数据，
按**周 star 增量**排序，输出一份 Markdown，直接复制贴公众号。

> 📌 另有 **[Gitee 源周报](README_gitee.md)**（`gitee_trending.py` 采集，含国产数据库项目），与本表平行维护。

<!-- LATEST:START -->
<!-- 本区块由 v2-weekly.yml 自动维护（嵌入最新一期全文），请勿手动编辑 -->
> 📖 **本期周报**（全文如下）· [源文件](v2/reports/report_snapshot_20260907.md)
> 📚 **历史周报**：见文末[「往期周报」](#往期周报)

---

## 📋 数据库开源生态周报 · 第 5 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-09-07_

---

### 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[ETH-transactions-storage](https://github.com/Adamant-im/ETH-transactions-storage)（+573）—— Self-hosted Ethereum transaction indexer for native ETH and 
- 🇨🇳 **国产数据库**：[bytebase](https://github.com/bytebase/bytebase)（+17）—— Database governance built for humans and agents — controllin
- 🤖 **AI工具**：[dbx](https://github.com/t8y2/dbx)（+630）—— 20 MB lightweight cross-platform database client for 90+ dat



### 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

#### 🔥 活跃榜 Top3

> 🥇 **[Adamant-im/ETH-transactions-storage](https://github.com/Adamant-im/ETH-transactions-storage)** · ⭐ 573 · 本周 **+573**
> `其他` · 适用：PostgreSQL
> Self-hosted Ethereum transaction indexer for native ETH and ERC-20 transfers wit
> 🤖 **AI 解读**：该项目用Python读取以太坊节点区块，将ETH及ERC-20转账存入PostgreSQL，经PostgREST提供只读HTTP接口，供钱包

> 🥈 **[David-Crty/databasement](https://github.com/David-Crty/databasement)** · ⭐ 2.3k · 本周 **+267**
> `备份` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB
> Self-hosted database backup manager with a web UI. Schedule, backup, and restore
> 🤖 **AI 解读**：自托管数据库备份管理工具，提供Web界面，支持多种数据库的定时备份与恢复，可存储至S3等远端，并支持SSH隧道连接。

> 🥉 **[evangelosvlachos96-dotcom/booking-microservices](https://github.com/evangelosvlachos96-dotcom/booking-microservices)** · ⭐ 240 · 本周 **+240**
> `其他` · 适用：PostgreSQL
> Flight booking system built as .NET 10 microservices with Vertical Slice Archite
> 🤖 **AI 解读**：.NET 10微服务航班预订系统，采用PostgreSQL及多种非关系型存储，演示CQRS与事件溯源模式，为数据库使用者提供微服务数据架构参考。

#### 🌱 新锐发现（最多 3 个）

> ① **[LuisCarlos01/sentinel-auth-api](https://github.com/LuisCarlos01/sentinel-auth-api)** · ⭐ 9 · 本周 **+9**
> `其他` · 适用：PostgreSQL
> Production-inspired authentication API with Spring Boot, JWT, Refresh Tokens, RB
> 🤖 **AI 解读**：基于Spring Boot的认证API示例，用PostgreSQL存用户与角色，支持JWT及刷新令牌。

> ② **[el1s7/model](https://github.com/el1s7/model)** · ⭐ 5 · 本周 **+5**
> `其他` · 适用：MySQL / MariaDB
> A minimal Python ORM for MariaDB/MySQL and SQLite. Made for humans.
> 🤖 **AI 解读**：el1s7/model 是面向 MariaDB/MySQL 及嵌入式数据库的 Python ORM，支持静态类型检查、自动建表与模型生成

> ③ **[Jayavisaag/Mysql-GUI](https://github.com/Jayavisaag/Mysql-GUI)** · ⭐ 4 · 本周 **+4**
> `平台` · 适用：SQL Server / MySQL
> "MySQL Admin Pro," a Tkinter-based GUI built with mysql.connector for visual dat
> 🤖 **AI 解读**：基于Python与Tkinter的MySQL图形管理工具，支持建库建表、增删改查、SQL执行、用户权限管理及CSV导出

#### 🔍 本周解读 · ETH-transactions-storage

> 🔍 **[Adamant-im/ETH-transactions-storage](https://github.com/Adamant-im/ETH-transactions-storage)** · ⭐ 573 · 本周 **+573**
> `其他` · 适用：PostgreSQL
> Self-hosted Ethereum transaction indexer for native ETH and ERC-20 transfers with PostgreSQL and PostgREST

**解决什么**：Ethereum节点无法直接查询某地址的交易历史，此项目通过自建索引器读取区块，将原生ETH与ERC-20转账写入PostgreSQL，并提供只读HTTP接口，解决地址交易记录检索问题。

**核心亮点**：基于PostgreSQL事务写入区块与检查点，支持断点续跑；经PostgREST暴露只读API；兼容Geth、Nethermind等客户端，支持HTTP、WebSocket、IPC；可选地址过滤。

**使用场景**：适用于加密货币钱包展示账户资产与交易历史、区块浏览器与仪表盘构建地址页面、会计与财务对账工具导出转账记录，以及监控特定地址集合或需要直接SQL查询转账数据的自定义应用。



### 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

#### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+17**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access
> 🤖 **AI 解读**：Bytebase是开源数据库治理平台，为人工与AI代理提供统一控制面，管理Oracle、SQL Server、MySQL等数据库的变更、访问与合规流程

> 🥈 **[suoten/dbbridge](https://github.com/suoten/dbbridge)** · ⭐ 16 · 本周 **+15**
> `其他` · 适用：8+种数据库（MySQL / PostgreSQL / MariaDB等）
> Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持 MySQL/PostgreSQL/SQLite/OceanBase/TiDB/达
> 🤖 **AI 解读**：开源免费、零依赖的数据库迁移与SQL转换工具，支持十余种数据库互转，单文件小于30MB，双击即用，适用于异构数据库迁移场景。

> 🥉 **[tikv/pprof-rs](https://github.com/tikv/pprof-rs)** · ⭐ 1.7k · 本周 **+3**
> `其他` · 适用：TiDB
> A Rust CPU profiler implemented with the help of backtrace-rs
> 🤖 **AI 解读**：pprof-rs为Rust程序提供CPU性能分析，基于backtrace-rs实现。TiDB用户可借此定位CPU热点，优化查询执行路径，辅助性能调优。

#### 🌱 新锐发现（最多 3 个）

> ① **[tikv/.project](https://github.com/tikv/.project)** · ⭐ 0 · 近7天 1 commits
> `其他` · 适用：TiDB
> Project metadata for TiKV - CNCF .project automation
> 🤖 **AI 解读**：TiKV的CNCF元数据仓库存project.yaml与maintainers.yaml，供自动化工具校验维护，属项目治理辅助文件

#### 🔍 本周解读 · bytebase

> 🔍 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+17**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access across every major database.

**解决什么**：Bytebase 提供集中平台，整合数据库变更管理、访问控制与合规审计，覆盖 Oracle、SQL Server、MySQL、PostgreSQL 等主流数据库，解决管控分散、缺乏统一治理的问题。

**核心亮点**：支持GUI工作流与GitOps集成，实现数据库即代码。提供200余条SQL审查规则、细粒度RBAC、动态数据脱敏及完整审计日志。内置MCP服务器与文本转SQL功能，便于AI代理接入。

**使用场景**：适用于需要规范化数据库变更流程的开发团队，需统一管理多环境数据库的 DBA，以及要求列级权限控制与审计追踪的安全合规场景。支持自托管或 Kubernetes 部署。



### 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

#### 🔥 活跃榜 Top3

> 🥇 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 18.2k · 本周 **+630**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including My
> 🤖 **AI 解读**：20MB客户端支持90余种数据库，覆盖Oracle、SQL Server、DB2、MySQL、PostgreSQL等，提供桌面、Docker

> 🥈 **[TabularisDB/tabularis](https://github.com/TabularisDB/tabularis)** · ⭐ 4.8k · 本周 **+249**
> `平台` · 适用：9+种数据库（Oracle / SQL Server / DB2等）
> Open-source desktop SQL workspace for PostgreSQL, MySQL/MariaDB, SQLite and 15+ 
> 🤖 **AI 解读**：Tabularis是开源桌面SQL工作台，支持PostgreSQL、MySQL、MariaDB等十余种数据库。内置MCP服务器

> 🥉 **[Canner/WrenAI](https://github.com/Canner/WrenAI)** · ⭐ 17.5k · 本周 **+85**
> `平台` · 适用：PostgreSQL / ClickHouse
> GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL throug
> 🤖 **AI 解读**：WrenAI是开源生成式BI引擎，面向AI智能体提供受治理的text-to-SQL与语义层，通过上下文层将自然语言转为仪表盘、图表及SQL

#### 🌱 新锐发现（最多 3 个）

> ① **[CesarPetrescu/ledger](https://github.com/CesarPetrescu/ledger)** · ⭐ 4 · 本周 **+4**
> `其他` · 适用：PostgreSQL
> Self-hosted MCP project memory with OAuth 2.1, PostgreSQL full-text search, and 
> 🤖 **AI 解读**：Ledger是基于PostgreSQL的自托管MCP服务器，为AI助手提供跨会话项目记忆，支持决策记录、全文检索及任务交接，数据存于自有实例。

#### 🔍 本周解读 · dbx

> 🔍 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 18.2k · 本周 **+630**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including MySQL, PostgreSQL, SQLite, Redis, MongoDB,

**解决什么**：20MB安装包集成90余种数据库访问能力，覆盖MySQL、PostgreSQL、文件库、内存库、文档库、Oracle、SQL Server、DB2、DM等主流及国产库

**核心亮点**：跨平台桌面端、Docker、CLI 三种使用形态。内置 AI 助手辅助生成与解释查询。提供 MCP Server 接口，便于接入支持 MCP 的 AI 工具链。单文件体积小，便于分发与部署。

**使用场景**：适用于需要同时管理多种类型数据库的开发、测试及运维场景。适合在资源受限的容器环境或远程服务器上通过 CLI 或 Docker 执行数据库操作。适合作为 AI 编程工具访问数据库的中间层。



### 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.6k | 国外数据库 | 监控 | The open and composable observability and data visualization platform. |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.7k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.4k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL gen |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.1k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and SQL |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.6k | 国外数据库 | 其他 | REST API for any Postgres database |



### 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-09-07）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
<!-- LATEST:END -->

---

## 往期周报

<!-- ARCHIVE:START -->
| 期数 | 日期 | 链接 |
|------|------|------|
| 第 4 期 | 2026-08-31 | [report_snapshot_20260831.md](v2/reports/report_snapshot_20260831.md) |
| 第 3 期 | 2026-08-24 | [report_snapshot_20260824.md](v2/reports/report_snapshot_20260824.md) |
| 第 2 期 | 2026-08-17 | [report_snapshot_20260817.md](v2/reports/report_snapshot_20260817.md) |
<!-- ARCHIVE:END -->
