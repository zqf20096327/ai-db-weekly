# 📋 数据库开源生态周报 · 第 6 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-09-12_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[ivory](https://github.com/veegres/ivory)（+269）—— Ivory is a database cluster management tool that puts…
- 🇨🇳 **国产数据库**：[raft-rs](https://github.com/tikv/raft-rs)（+3）—— Raft distributed consensus algorithm implemented in Rust.
- 🤖 **AI工具**：[kiwi-mem](https://github.com/LucieEveille/kiwi-mem)（+292）—— 🥝 Self-hosted memory gateway for AI companions —…



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[veegres/ivory](https://github.com/veegres/ivory)** · ⭐ 269 · 本周 **+269**
> `平台` · 适用：不适用（数据库本身）
> Ivory is a database cluster management tool that puts control in your pocket.…
> 🤖 **AI 解读**：Ivory是开源数据库集群管理Web界面，支持PostgreSQL等，提供部署、监控、切换与查询控制。

> 🥈 **[pgrundev/pgterm](https://github.com/pgrundev/pgterm)** · ⭐ 237 · 本周 **+237**
> `其他` · 适用：PostgreSQL
> Modern Postgres Terminal
> 🤖 **AI 解读**：pgterm 是 PostgreSQL 的终端监控界面，可集中查看多个库的状态、连接与诊断信息。

> 🥉 **[libredb/libredb-studio](https://github.com/libredb/libredb-studio)** · ⭐ 638 · 本周 **+234**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> One browser tab for PostgreSQL, MySQL, Oracle, SQL Server, MongoDB, Redis…
> 🤖 **AI 解读**：LibreDB Studio 是自托管开源 SQL IDE，可在浏览器管理 Oracle、SQL Server、MySQL、PostgreSQL 等数据库…

### 🔍 本周解读 · ivory

> 🔍 **[veegres/ivory](https://github.com/veegres/ivory)** · ⭐ 269 · 本周 **+269**
> `平台` · 适用：不适用（数据库本身）
> Ivory is a database cluster management tool that puts control in your pocket. It gives you a unified UI for cluster…

**解决什么**：面向高可用数据库集群的运维管理，提供统一Web界面，支持部署、监控、故障切换与查询，可在手机端操作。

**核心亮点**：统一UI管理集群、查询构建器、容器控制、虚拟机监控、支持PostgreSQL与Patroni等、自托管单容器部署。

**使用场景**：适合DBA、SRE及后端开发者运维高可用数据库集群，进行部署、排障、切换与监控，支持移动端远程操作。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[tikv/raft-rs](https://github.com/tikv/raft-rs)** · ⭐ 3.4k · 本周 **+3**
> `其他` · 适用：TiDB
> Raft distributed consensus algorithm implemented in Rust.
> 🤖 **AI 解读**：TiDB 的 Raft 共识库，用 Rust 实现，支撑分布式事务与多副本一致性。

> 🥈 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 380 · 本周 **+3**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It…
> 🤖 **AI 解读**：CloudDM是开源数据库管理工具，支持Oracle、MySQL等12+种数据库，提供访问控制、SQL审计与CI/CD，便于团队协作。

> 🥉 **[polardb/duckdb-paimon](https://github.com/polardb/duckdb-paimon)** · ⭐ 47 · 本周 **+3**
> `其他` · 适用：PolarDB
> DuckDB extension for accessing Apache Paimon. 🦆
> 🤖 **AI 解读**：嵌入式分析数据库扩展支持直读 Apache Paimon 表，无需 ETL 或 Flink/Spark，可在 PolarDB 等环境用 SQL 分析湖数据。

### 🔍 本周解读 · raft-rs

> 🔍 **[tikv/raft-rs](https://github.com/tikv/raft-rs)** · ⭐ 3.4k · 本周 **+3**
> `其他` · 适用：TiDB
> Raft distributed consensus algorithm implemented in Rust.

**解决什么**：为分布式系统提供容错能力，使集群在部分节点故障或网络分区时仍能就值达成一致，且决定不可更改。

**核心亮点**：仅含核心共识模块、支持rust-protobuf与Prost编解码、可自定义日志与状态机及网络层、基于Rust 2018版实现。

**使用场景**：适用于需构建容错分布式系统的场景，如TiDB等分布式数据库的共识层，用户需自行实现日志、状态机与传输组件。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[LucieEveille/kiwi-mem](https://github.com/LucieEveille/kiwi-mem)** · ⭐ 292 · 本周 **+292**
> `连接/代理` · 适用：PostgreSQL
> 🥝 Self-hosted memory gateway for AI companions — OpenAI-compatible proxy with…
> 🤖 **AI 解读**：kiwi-mem 是基于 PostgreSQL 与 pgvector 的自托管 AI 记忆网关，以向量检索、热度衰减和分层摘要管理长期记忆。

> 🥈 **[turanmahmudov/masume](https://github.com/turanmahmudov/masume)** · ⭐ 67 · 本周 **+67**
> `平台` · 适用：6+种数据库（SQL Server / MySQL / PostgreSQL等）
> A database client for the terminal. Open a database, read it, and give an agent…
> 🤖 **AI 解读**：面向终端的数据库客户端，支持多种关系库，提供浏览、查询、ER图与MCP服务，便于在命令行管理数据。

> 🥉 **[fj1981/dqex](https://github.com/fj1981/dqex)** · ⭐ 106 · 本周 **+48**
> `迁移` · 适用：Oracle / SQL Server / MySQL / PostgreSQL / ClickHouse
> AI-Native, Offline-First Database Workbench — Import/Export/Migrate/Compare/Snap…
> 🤖 **AI 解读**：dqex 是离线优先的数据库工作台，单二进制运行，支持 Oracle、SQL Server、MySQL、PostgreSQL、ClickHouse 的导入导出…

### 🔍 本周解读 · kiwi-mem

> 🔍 **[LucieEveille/kiwi-mem](https://github.com/LucieEveille/kiwi-mem)** · ⭐ 292 · 本周 **+292**
> `连接/代理` · 适用：PostgreSQL
> 🥝 Self-hosted memory gateway for AI companions — OpenAI-compatible proxy with vector search, memory heat, Dream…

**解决什么**：为AI伴侣提供自托管长期记忆网关，通过OpenAI兼容代理接入，实现记忆的存储、检索与整合。

**核心亮点**：向量搜索与记忆热度衰减、Dream睡眠整合、日历层级摘要、Anthropic原生格式直连与工具按需加载。

**使用场景**：生活助理、长期情感陪伴、连载创作与角色扮演、学习辅导等需要AI记住个人习惯与经历的对话场景。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.7k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.7k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.5k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.1k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and… |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.7k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-09-12）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
