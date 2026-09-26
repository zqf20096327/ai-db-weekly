# 📋 数据库开源生态周报 · 第 8 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-09-26_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[BemiDB](https://github.com/pgstack-io/BemiDB)（+1533）—— Open-source Snowflake & Fivetran alternative, with Postgres…
- 🇨🇳 **国产数据库**：[tidb-in-action](https://github.com/tidb-incubator/tidb-in-action)（+711）—— TiDB In Action: based on 4.0
- 🤖 **AI工具**：[rag-api](https://github.com/LibreChat-AI/rag-api)（+908）—— ID-based RAG FastAPI: Integration with Langchain and…



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[pgstack-io/BemiDB](https://github.com/pgstack-io/BemiDB)** · ⭐ 1.5k · 本周 **+1533**
> `迁移` · 适用：MySQL / PostgreSQL
> Open-source Snowflake & Fivetran alternative, with Postgres compatibility.
> 🤖 **AI 解读**：BemiDB 是开源数据仓库与同步工具，兼容 PostgreSQL，可将 MySQL、PostgreSQL 数据同步至 S3 列式存储并查询。

> 🥈 **[pgstack-io/bemi-io](https://github.com/pgstack-io/bemi-io)** · ⭐ 402 · 本周 **+402**
> `管理` · 适用：SQL Server / PostgreSQL
> Automatic data change tracking for PostgreSQL
> 🤖 **AI 解读**：Bemi 通过解析 PostgreSQL 预写日志，自动记录数据变更，无需改动表结构，可用于审计追踪与数据版本查询。

> 🥉 **[grafana/grafana](https://github.com/grafana/grafana)** · ⭐ 76.9k · 本周 **+107**
> `监控` · 适用：MySQL / PostgreSQL
> The open and composable observability and data visualization platform.…
> 🤖 **AI 解读**：Grafana是开源可组合观测平台，可查询、可视化MySQL与PostgreSQL等数据源指标并告警。

### 🌱 新锐发现（最多 3 个）

> ① **[0xmikadzyki/ghost](https://github.com/0xmikadzyki/ghost)** · ⭐ 18 · 本周 **+18**
> `迁移` · 适用：ClickHouse
> Fund-flow pipeline for Robinhood Chain (chain 4663): full ERC-20 Transfer…
> 🤖 **AI 解读**：该项目用ClickHouse存储Robinhood Chain全量ERC-20转账，供只读资金流查询。

> ② **[hakureiyuyuko/LMBY](https://github.com/hakureiyuyuko/LMBY)** · ⭐ 7 · 本周 **+7**
> `其他` · 适用：PostgreSQL
> LMBY —— Light 的 Emby：单二进制 + PostgreSQL 的轻量媒体服务器（Go + React，纯 Web 播放、硬件转码、Emby…
> 🤖 **AI 解读**：LMBY是自托管媒体服务器，用PostgreSQL存元数据与任务队列，适合轻量部署场景。

> ③ **[avison9/cdclint](https://github.com/avison9/cdclint)** · ⭐ 6 · 本周 **+6**
> `迁移` · 适用：6+种数据库（Oracle / SQL Server / MySQL等）
> Lint the contract between your database, your Debezium connector and your sink…
> 🤖 **AI 解读**：cdclint 用于在部署前检查数据库、Debezium 连接器与下游目标间的模式一致性，支持 MySQL、PostgreSQL 等源，减少列静默丢失。

### 🔍 本周解读 · BemiDB

> 🔍 **[pgstack-io/BemiDB](https://github.com/pgstack-io/BemiDB)** · ⭐ 1.5k · 本周 **+1533**
> `迁移` · 适用：MySQL / PostgreSQL
> Open-source Snowflake & Fivetran alternative, with Postgres compatibility.

**解决什么**：将多数据源同步至对象存储，并以Postgres兼容引擎查询分析数据，替代传统数据集成与分析组合。

**核心亮点**：列式压缩存储于S3、内置多源连接器、Postgres兼容查询引擎、单镜像无状态部署。

**使用场景**：集中多源数据、用Postgres工具查询分析、运行复杂分析查询、归档历史数据。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[tidb-incubator/tidb-in-action](https://github.com/tidb-incubator/tidb-in-action)** · ⭐ 711 · 本周 **+711**
> `其他` · 适用：TiDB
> TiDB In Action: based on 4.0
> 🤖 **AI 解读**：TiDB In Action 是一本基于 TiDB 4.0 的开源电子书，由社区贡献，介绍其原理与操作，供使用者查阅。

> 🥈 **[cyq1162/cyqdata](https://github.com/cyq1162/cyqdata)** · ⭐ 683 · 本周 **+683**
> `其他` · 适用：7+种数据库（Oracle / SQL Server / DB2等）
> cyq.data is a  high-performance and the most powerful orm.（.NET…
> 🤖 **AI 解读**：cyq.data 是 .NET 的 ORM 框架，支持 Oracle、SQL Server、DB2、MySQL、PostgreSQL、DM 等…

> 🥉 **[tidb-incubator/tidis](https://github.com/tidb-incubator/tidis)** · ⭐ 527 · 本周 **+527**
> `平台` · 适用：TiDB（本体）
> A distributed transactional large-scale NoSQL database powered by TiKV
> 🤖 **AI 解读**：Tidis 是 TiKV 上的服务层，以 Rust 实现，提供兼容某内存数据库协议的分布式存储，支持多种数据类型与事务。

### 🌱 新锐发现（最多 3 个）

> ① **[openeverest/provider-tidb](https://github.com/openeverest/provider-tidb)** · ⭐ 3 · 本周 **+3**
> `平台` · 适用：MySQL / TiDB
> OpenEverest provider for TiDB - uses official operator
> 🤖 **AI 解读**：OpenEverest的TiDB提供程序，将通用实例转为TiDB Operator资源，助用户在Kubernetes上部署TiDB。

> ② **[ngclara07/tcm-explorer](https://github.com/ngclara07/tcm-explorer)** · ⭐ 0 · 近7天 1 commits
> `平台` · 适用：MySQL / TiDB
> Traditional Chinese Medicine knowledge-base explorer built with Node.js…
> 🤖 **AI 解读**：该项目基于Node.js与MySQL/TiDB，提供中药知识图谱查询，含搜索与仪表盘，供数据库使用者检索草药、成分、靶点及疾病关联。

> ③ **[tuxin-labs/trino-418-dameng](https://github.com/tuxin-labs/trino-418-dameng)** · ⭐ 0 · 近7天 0 commits
> `其他` · 适用：DM
> 基于 Trino 418 的达梦数据库(DM8)连接器发行版
> 🤖 **AI 解读**：该项目为Trino 418提供DM连接器，支持SQL查询、写入与谓词下推，便于用户联邦访问DM数据。

### 🔍 本周解读 · tidb-in-action

> 🔍 **[tidb-incubator/tidb-in-action](https://github.com/tidb-incubator/tidb-in-action)** · ⭐ 711 · 本周 **+711**
> `其他` · 适用：TiDB
> TiDB In Action: based on 4.0

**解决什么**：提供基于 TiDB 4.0 的原理与操作指南，以开源协作方式编写，帮助读者理解并使用 TiDB。

**核心亮点**：基于 TiDB 4.0 编写、社区共同贡献、重实操轻原理、涵盖工具使用与实践。

**使用场景**：适合学习 TiDB 基本原理与操作、查阅工具用法、参考部署与运维实践流程。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[LibreChat-AI/rag-api](https://github.com/LibreChat-AI/rag-api)** · ⭐ 908 · 本周 **+908**
> `其他` · 适用：Oracle / PostgreSQL
> ID-based RAG FastAPI: Integration with Langchain and PostgreSQL/pgvector
> 🤖 **AI 解读**：基于PostgreSQL/pgvector的ID级RAG接口，支持文档索引与检索。

> 🥈 **[matrixorigin/matrixone](https://github.com/matrixorigin/matrixone)** · ⭐ 2.0k · 本周 **+123**
> `平台` · 适用：MySQL / ClickHouse
> AI-native HTAP database with Git-for-Data and built-in vector search, serving…
> 🤖 **AI 解读**：MatrixOne 是兼容 MySQL 的 AI 原生 HTAP 数据库，支持 Git-for-Data 与向量检索，可为智能体提供数据与记忆支撑。

> 🥉 **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** · ⭐ 39.7k · 本周 **+120**
> `其他` · 适用：Oracle / PostgreSQL / MariaDB
> Free, simple, and intuitive online database diagram editor and SQL generator.
> 🤖 **AI 解读**：drawDB 是浏览器端 ER 图编辑器，可绘制数据库结构并生成 SQL，支持 Oracle、PostgreSQL、MariaDB 等。

### 🌱 新锐发现（最多 3 个）

> ① **[ww-1009/ob_agent](https://github.com/ww-1009/ob_agent)** · ⭐ 6 · 本周 **+6**
> `其他` · 适用：Oracle / MySQL / PostgreSQL / OceanBase
> Conversational OceanBase DBA assistant built with FastAPI, Vue 3, LangChain…
> 🤖 **AI 解读**：基于FastAPI与Vue 3的对话式OceanBase运维助手，可检索OCP元数据、诊断慢SQL并流式返回结果。

> ② **[Sajjad-rafiee/CareerOpportunityEngine](https://github.com/Sajjad-rafiee/CareerOpportunityEngine)** · ⭐ 3 · 本周 **+3**
> `其他` · 适用：PostgreSQL
> FastAPI + Postgres/pgvector backend that ingests job postings, embeds and…
> 🤖 **AI 解读**：该项目用PostgreSQL加pgvector存储职位数据，支持语义检索与资格信息提取，供数据库使用者查询分析。

> ③ **[Cyrax321/QwerySmith-1.0](https://github.com/Cyrax321/QwerySmith-1.0)** · ⭐ 3 · 本周 **+3**
> `其他` · 适用：PostgreSQL
> QwerySmith: open text-to-SQL models that answer from retrieved evidence with…
> 🤖 **AI 解读**：QwerySmith 是面向 PostgreSQL 的开源 text-to-SQL 模型，依据检索证据生成带可验证引用的 SQL 或拒答，并附训练评测工具。

### 🔍 本周解读 · rag-api

> 🔍 **[LibreChat-AI/rag-api](https://github.com/LibreChat-AI/rag-api)** · ⭐ 908 · 本周 **+908**
> `其他` · 适用：Oracle / PostgreSQL
> ID-based RAG FastAPI: Integration with Langchain and PostgreSQL/pgvector

**解决什么**：提供基于文件ID的文档索引与检索API，将Langchain与FastAPI异步集成，使用PostgreSQL/pgvector存储向量，服务于按文件粒度的查询场景。

**核心亮点**：按file_id组织嵌入、异步接口、基于令牌的属主范围校验、支持文档增删查与向量检索。

**使用场景**：适合与LibreChat等应用集成，用于按文件ID管理知识库、结合文件元数据做定向检索，以及需要多租户属主隔离的RAG服务。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.9k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.9k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.7k | AI工具 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.3k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and… |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.7k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-09-26）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
