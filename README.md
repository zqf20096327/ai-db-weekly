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

- 🗄️ **国外数据库**：[databasement](https://github.com/David-Crty/databasement)（+267）—— Self-hosted database backup manager with a web UI. Schedule,
- 🇨🇳 **国产数据库**：[bytebase](https://github.com/bytebase/bytebase)（+17）—— Database governance built for humans and agents — controllin
- 🤖 **AI工具**：[dbx](https://github.com/t8y2/dbx)（+630）—— 20 MB lightweight cross-platform database client for 90+ dat



### 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

#### 🔥 活跃榜 Top3

> 🥇 **[David-Crty/databasement](https://github.com/David-Crty/databasement)** · ⭐ 2.3k · 本周 **+267**
> `备份` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB
> Self-hosted database backup manager with a web UI. Schedule, backup, and restore
> 🤖 **AI 解读**：自托管数据库备份管理工具，提供Web界面，支持多种数据库的定时备份与恢复，可存储至S3、SFTP等，并支持SSH隧道连接。

> 🥈 **[pgrundev/pgbot](https://github.com/pgrundev/pgbot)** · ⭐ 984 · 本周 **+159**
> `其他` · 适用：PostgreSQL
> Postgres intelligence for ai agents & apps
> 🤖 **AI 解读**：pgbot是PostgreSQL只读诊断工具，静态连接数据库，读取统计视图并输出健康报告及变更对比。支持PostgreSQL 14至18

> 🥉 **[TableProApp/TablePro](https://github.com/TableProApp/TablePro)** · ⭐ 5.8k · 本周 **+149**
> `其他` · 适用：7+种数据库（Oracle / SQL Server / MySQL等）
> Free and open source database client built natively for developers
> 🤖 **AI 解读**：TablePro是面向开发者的免费开源数据库客户端，原生支持多类SQL及NoSQL数据库，提供SQL编辑、数据管理等功能，并集成AI辅助与MCP服务。

#### 🌱 新锐发现（最多 3 个）

> ① **[el1s7/model](https://github.com/el1s7/model)** · ⭐ 5 · 本周 **+5**
> `其他` · 适用：MySQL / MariaDB
> A minimal Python ORM for MariaDB/MySQL and SQLite. Made for humans.
> 🤖 **AI 解读**：el1s7/model 是面向 MariaDB/MySQL 及嵌入式数据库的 Python ORM，支持静态类型检查、自动建表与模型生成

> ② **[Jayavisaag/Mysql-GUI](https://github.com/Jayavisaag/Mysql-GUI)** · ⭐ 4 · 本周 **+4**
> `平台` · 适用：SQL Server / MySQL
> "MySQL Admin Pro," a Tkinter-based GUI built with mysql.connector for visual dat
> 🤖 **AI 解读**：基于Python与Tkinter构建的MySQL图形管理工具，提供建库建表、增删改查、SQL执行、用户权限管理及CSV导出功能，适用于MySQL日常运维操作。

> ③ **[oscarbol09/branchbase](https://github.com/oscarbol09/branchbase)** · ⭐ 3 · 本周 **+3**
> `其他` · 适用：MySQL / PostgreSQL
> Zero-config, Git-native local database branching for PostgreSQL, MySQL, and SQLi
> 🤖 **AI 解读**：BranchBase 为 PostgreSQL、MySQL 等数据库提供 Git 原生分支能力，可随代码分支切换本地库状态，减少手动重建或回滚迁移的操作。

#### 🔍 本周解读 · databasement

> 🔍 **[David-Crty/databasement](https://github.com/David-Crty/databasement)** · ⭐ 2.3k · 本周 **+267**
> `备份` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB
> Self-hosted database backup manager with a web UI. Schedule, backup, and restore MySQL, PostgreSQL, MariaDB, Microsoft S

**解决什么**：自托管数据库备份管理工具，通过Web界面统一调度备份任务，解决多类型数据库备份分散、恢复流程复杂的问题，并提供集中化的存储与监控能力。

**核心亮点**：支持MySQL、PostgreSQL、MariaDB、SQL Server及文档数据库的定时备份与恢复。提供SSH隧道和远程代理访问隔离网络。支持S3、SFTP、Samba及本地存储。

**使用场景**：适用于需要统一管理多种数据库备份的中小团队或运维人员。适合数据库位于私有网络、需通过跳板机访问的环境。适合对备份安全性与自动化恢复流程有要求的自托管部署场景。



### 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

#### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+17**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access
> 🤖 **AI 解读**：Bytebase是开源数据库治理平台，为人工及AI代理提供统一控制面，管理变更、访问与合规。支持十余种数据库及多种集成，具备GUI工作流、GitOps

> 🥈 **[suoten/dbbridge](https://github.com/suoten/dbbridge)** · ⭐ 16 · 本周 **+15**
> `其他` · 适用：8+种数据库（MySQL / PostgreSQL / MariaDB等）
> Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持 MySQL/PostgreSQL/SQLite/OceanBase/TiDB/达
> 🤖 **AI 解读**：DBBridge是一款开源免费的数据库迁移与SQL转换工具，支持十余种数据库间的数据互转。其单文件免安装，通过图形界面操作，适用于需要跨数据库迁移数据的用户。

> 🥉 **[tikv/pprof-rs](https://github.com/tikv/pprof-rs)** · ⭐ 1.7k · 本周 **+3**
> `其他` · 适用：TiDB
> A Rust CPU profiler implemented with the help of backtrace-rs
> 🤖 **AI 解读**：pprof-rs是Rust编写的CPU分析器，基于backtrace-rs实现。TiDB等数据库开发者可集成它定位CPU热点，生成调用栈报告，辅助性能调优。

#### 🔍 本周解读 · bytebase

> 🔍 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+17**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access across every major database.

**解决什么**：数据库变更与访问管控分散在多个工具中，导致流程割裂且难以审计。Bytebase 提供一个统一控制平面，将变更管理、权限控制和合规记录整合，覆盖主流数据库。

**核心亮点**：支持GUI与GitOps双模式变更流程，内置200+SQL审查规则。提供基于角色的细粒度权限、临时授权及动态列级脱敏。具备完整审计日志，可通过MCP协议接入AI代理执行操作。

**使用场景**：适用于需要规范化数据库变更流程的开发团队，需集中管理多环境数据库的 DBA，以及要求敏感数据访问可控、操作可追溯的安全合规场景。支持自托管或 Kubernetes 部署。



### 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

#### 🔥 活跃榜 Top3

> 🥇 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 18.2k · 本周 **+630**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including My
> 🤖 **AI 解读**：20MB客户端支持90余种数据库，含Oracle、SQL Server、DB2、MySQL等，提供桌面、Docker、CLI界面

> 🥈 **[TabularisDB/tabularis](https://github.com/TabularisDB/tabularis)** · ⭐ 4.8k · 本周 **+249**
> `平台` · 适用：9+种数据库（Oracle / SQL Server / DB2等）
> Open-source desktop SQL workspace for PostgreSQL, MySQL/MariaDB, SQLite and 15+ 
> 🤖 **AI 解读**：Tabularis为开源桌面SQL工作台，支持十余种数据库，含PostgreSQL、MySQL/MariaDB及轻量级文件数据库。内置MCP服务器

> 🥉 **[Canner/WrenAI](https://github.com/Canner/WrenAI)** · ⭐ 17.5k · 本周 **+85**
> `平台` · 适用：PostgreSQL / ClickHouse
> GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL throug
> 🤖 **AI 解读**：WrenAI为开源生成式BI引擎，提供受治理的text-to-SQL与语义层，支持20余种数据源，可将自然语言转为SQL、图表及仪表盘。

#### 🌱 新锐发现（最多 3 个）

> ① **[CesarPetrescu/ledger](https://github.com/CesarPetrescu/ledger)** · ⭐ 4 · 本周 **+4**
> `其他` · 适用：PostgreSQL
> Self-hosted MCP project memory with OAuth 2.1, PostgreSQL full-text search, and 
> 🤖 **AI 解读**：Ledger 是一款自托管MCP服务器，基于PostgreSQL存储数据，为AI助手提供跨对话的项目记忆与上下文检索功能。

#### 🔍 本周解读 · dbx

> 🔍 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 18.2k · 本周 **+630**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including MySQL, PostgreSQL, SQLite, Redis, MongoDB,

**解决什么**：20MB安装包集成90余种数据库访问能力，覆盖MySQL、PostgreSQL、文件、内存、文档、Oracle、SQL Server、DB2、达梦等，提供统一桌面端、Docker与命令行入口

**核心亮点**：内置AI助手辅助查询与排错，集成MCP Server便于接入外部AI编排工具。支持桌面端、Docker、CLI三种运行形态，适配不同部署环境。安装包约20MB，资源占用低，便于分发与携带。

**使用场景**：适用于需同时管理多种数据库的开发运维人员；适合资源受限设备常驻，Docker快速搭建临时环境，命令行或脚本执行操作，及通过MCP协议接入AI工作流。



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
