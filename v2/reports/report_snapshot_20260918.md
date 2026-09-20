# 📋 数据库开源生态周报 · 第 2 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-09-18_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[libredb-studio](https://github.com/libredb/libredb-studio)（+205）—— One browser tab for PostgreSQL, MySQL, Oracle, SQL Server…
- 🇨🇳 **国产数据库**：[open-cdm](https://github.com/ClouGence/open-cdm)（+9）—— A free and open-source database management tool, suitable…
- 🤖 **AI工具**：[drawdb](https://github.com/drawdb-io/drawdb)（+169）—— Free, simple, and intuitive online database diagram editor…



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[libredb/libredb-studio](https://github.com/libredb/libredb-studio)** · ⭐ 788 · 本周 **+205**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> One browser tab for PostgreSQL, MySQL, Oracle, SQL Server, MongoDB, Redis…
> 🤖 **AI 解读**：LibreDB Studio 是自托管开源 SQL IDE，支持 Oracle、SQL Server、MySQL、PostgreSQL，提供单点登录…

> 🥈 **[grafana/grafana](https://github.com/grafana/grafana)** · ⭐ 76.8k · 本周 **+108**
> `监控` · 适用：MySQL / PostgreSQL
> The open and composable observability and data visualization platform.…
> 🤖 **AI 解读**：Grafana是开源可组合监控可视化平台，可连接MySQL、PostgreSQL等数据源，查询并展示指标、日志与追踪，支持告警。

> 🥉 **[malisper/pgrust](https://github.com/malisper/pgrust)** · ⭐ 5.1k · 本周 **+99**
> `其他` · 适用：PostgreSQL / ClickHouse
> Postgres rewritten in Rust, now faster than Postgres and Clickhouse
> 🤖 **AI 解读**：pgrust 用 Rust 重写 PostgreSQL，兼容其通信协议与 SQL 方言，通过其回归测试，供使用者评估。

### 🌱 新锐发现（最多 3 个）

> ① **[aligeek-tech/harbor-db](https://github.com/aligeek-tech/harbor-db)** · ⭐ 7 · 本周 **+7**
> `其他` · 适用：SQL Server / PostgreSQL / MariaDB
> A desktop workspace for PostgreSQL, MariaDB, and Redis. Native installers for…
> 🤖 **AI 解读**：本地Electron工具，可连接PostgreSQL、MariaDB等数据库，无需账号或后端服务。

> ② **[camuig/querycraft](https://github.com/camuig/querycraft)** · ⭐ 4 · 本周 **+4**
> `平台` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB / ClickHouse
> Fast cross-platform desktop client for MySQL, MariaDB, PostgreSQL, ClickHouse…
> 🤖 **AI 解读**：QueryCraft 是轻量桌面数据库客户端，支持 SQL Server、MySQL、PostgreSQL、MariaDB、ClickHouse 等…

> ③ **[ClickHouse/kb2cs](https://github.com/ClickHouse/kb2cs)** · ⭐ 0 · 近7天 1 commits
> `其他` · 适用：ClickHouse
> Skill for migrating Elasticsearch and Kibana dashboards to ClickHouse and…
> 🤖 **AI 解读**：ClickHouse的kb2cs可将Elasticsearch与Kibana仪表盘迁移至ClickHouse和ClickStack，供相关使用者参考。

### 🔍 本周解读 · libredb-studio

> 🔍 **[libredb/libredb-studio](https://github.com/libredb/libredb-studio)** · ⭐ 788 · 本周 **+205**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> One browser tab for PostgreSQL, MySQL, Oracle, SQL Server, MongoDB, Redis, SQLite, Couchbase, ClickHouse, Druid…

**解决什么**：浏览器中统一访问多种数据库的SQL开发工具，支持自托管部署，提供SSO、审计追踪与AI辅助查询，MIT协议开源。

**核心亮点**：多数据库统一接入、浏览器端SQL IDE、SSO与审计追踪、AI辅助查询、Docker与Kubernetes部署。

**使用场景**：适合需在数据就近环境自托管数据库管理平台的团队，用于跨多种数据库的查询、图表分析与ER图查看等日常开发运维场景。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 389 · 本周 **+9**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It…
> 🤖 **AI 解读**：CloudDM是开源数据库管理工具，支持Oracle、MySQL等12+种数据库，提供访问控制、SQL审计与CI/CD，便于团队协作。

> 🥈 **[tikv/raft-rs](https://github.com/tikv/raft-rs)** · ⭐ 3.4k · 本周 **+7**
> `其他` · 适用：TiDB
> Raft distributed consensus algorithm implemented in Rust.
> 🤖 **AI 解读**：TiDB 采用 Rust 实现的 Raft 共识库，支撑分布式事务与容错，保障多节点数据一致。

> 🥉 **[DotNetNext/SqlSugar](https://github.com/DotNetNext/SqlSugar)** · ⭐ 5.8k · 本周 **+4**
> `其他` · 适用：11+种数据库（Oracle / SQL Server / DB2等）
> .Net aot ORM   SqlServer ORM Mongodb ORM MySql  瀚高 Postgresql ORM  DB2 Hana 高斯…
> 🤖 **AI 解读**：SqlSugar是.NET ORM框架，支持Oracle、SQL Server、MySQL、PostgreSQL等多种数据库，提供建表、增删改查及分库分表功能。

### 🔍 本周解读 · open-cdm

> 🔍 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 389 · 本周 **+9**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It offers capabilities such as access control…

**解决什么**：面向团队提供数据库访问管控与变更协作，覆盖权限、脱敏、审计及CI/CD流程。

**核心亮点**：支持多类型数据库统一查询、资源与功能分离的权限模型、SQL审计与数据脱敏、多种触发的CI/CD流程。

**使用场景**：适合团队统一管理多数据库访问、规范SQL变更与审计、按角色分配权限及跨区域部署的场景。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** · ⭐ 39.6k · 本周 **+169**
> `其他` · 适用：Oracle / PostgreSQL / MariaDB
> Free, simple, and intuitive online database diagram editor and SQL generator.
> 🤖 **AI 解读**：浏览器端数据库ER图编辑器，可绘制模式、生成SQL与迁移，支持Oracle、PostgreSQL、MariaDB等。

> 🥈 **[oceanbase/powercontext](https://github.com/oceanbase/powercontext)** · ⭐ 1.1k · 本周 **+113**
> `其他` · 适用：OceanBase
> Not only memory but a full story.
> 🤖 **AI 解读**：OceanBase 的 PowerContext 为 AI 代理保存跨会话上下文，便于交接与续作，辅助数据库使用者管理任务状态。

> 🥉 **[rekursiv-ai/trackinizer](https://github.com/rekursiv-ai/trackinizer)** · ⭐ 47 · 本周 **+47**
> `其他` · 适用：PostgreSQL
> Epistemological database for agent and human efforts, beliefs, and findings.
> 🤖 **AI 解读**：面向智能体与人工研究，基于PostgreSQL记录问题、信念与发现，含三张核心表及接口。

### 🌱 新锐发现（最多 3 个）

> ① **[cfanai/dba-agent](https://github.com/cfanai/dba-agent)** · ⭐ 0 · 近7天 1 commits
> `监控` · 适用：7+种数据库（Oracle / MySQL / PostgreSQL等）
> Local-first database diagnostic and governance agent: versioned capability…
> 🤖 **AI 解读**：本地优先的数据库诊断Agent，只读默认，动作可审计，覆盖Oracle、MySQL、PostgreSQL等，供DBA排查与治理。

### 🔍 本周解读 · drawdb

> 🔍 **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** · ⭐ 39.6k · 本周 **+169**
> `其他` · 适用：Oracle / PostgreSQL / MariaDB
> Free, simple, and intuitive online database diagram editor and SQL generator.

**解决什么**：浏览器端数据库ER图编辑，支持SQL导入导出与迁移生成，无需注册账号。

**核心亮点**：在线ER图绘制、SQL脚本导入导出、迁移脚本生成、编辑器自定义。

**使用场景**：数据库建模与设计、SQL脚本转换、团队共享ER图、教学演示。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.8k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.8k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.6k | AI工具 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.1k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and… |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.7k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-09-18）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
