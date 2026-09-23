# 📋 数据库开源生态周报 · 第 5 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-09-05_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[ClickBench](https://github.com/ClickHouse/ClickBench)（+1098）—— ClickBench: a Benchmark For Analytical Databases
- 🇨🇳 **国产数据库**：[dbbridge](https://github.com/suoten/dbbridge)（+10）—— Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持…
- 🤖 **AI工具**：[mcp-clickhouse](https://github.com/ClickHouse/mcp-clickhouse)（+866）—— Connect ClickHouse to your AI assistants.



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[ClickHouse/ClickBench](https://github.com/ClickHouse/ClickBench)** · ⭐ 1.1k · 本周 **+1098**
> `其他` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB / ClickHouse
> ClickBench: a Benchmark For Analytical Databases
> 🤖 **AI 解读**：ClickBench是分析型数据库基准，含真实流量数据与查询，可复现测试，供SQL Server、MySQL、PostgreSQL…

> 🥈 **[MariaDB/mariadb-docker](https://github.com/MariaDB/mariadb-docker)** · ⭐ 926 · 本周 **+926**
> `其他` · 适用：MySQL / MariaDB
> Docker Official Image packaging for MariaDB
> 🤖 **AI 解读**：MariaDB 官方 Docker 镜像打包仓库，供 MySQL/MariaDB 用户以容器方式部署数据库。

> 🥉 **[oracle/python-cx_Oracle](https://github.com/oracle/python-cx_Oracle)** · ⭐ 887 · 本周 **+887**
> `其他` · 适用：Oracle
> Obsolete Python interface to Oracle Database, now superseded by python-oracledb
> 🤖 **AI 解读**：cx_Oracle是Oracle数据库的旧Python接口，2022年由python-oracledb取代。

### 🔍 本周解读 · ClickBench

> 🔍 **[ClickHouse/ClickBench](https://github.com/ClickHouse/ClickBench)** · ⭐ 1.1k · 本周 **+1098**
> `其他` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB / ClickHouse
> ClickBench: a Benchmark For Analytical Databases

**解决什么**：提供分析型数据库的可复现基准测试，基于真实流量数据评估查询性能。

**核心亮点**：数据集源自生产流量、43条查询覆盖扫描与索引、脚本化半自动复现、支持多种SQL数据库

**使用场景**：适用于点击流与流量分析、Web分析、结构化日志与事件数据的性能评估。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[suoten/dbbridge](https://github.com/suoten/dbbridge)** · ⭐ 10 · 本周 **+10**
> `其他` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持 MySQL/PostgreSQL/SQLite/OceanBase/TiDB/达…
> 🤖 **AI 解读**：DBBridge 是开源数据库迁移与 SQL 转换工具，支持 Oracle、MySQL、PostgreSQL、TiDB、OceanBase…

> 🥈 **[DotNetNext/SqlSugar](https://github.com/DotNetNext/SqlSugar)** · ⭐ 5.8k · 本周 **+4**
> `其他` · 适用：11+种数据库（Oracle / SQL Server / DB2等）
> .Net aot ORM   SqlServer ORM Mongodb ORM MySql  瀚高 Postgresql ORM  DB2 Hana 高斯…
> 🤖 **AI 解读**：SqlSugar是.NET ORM框架，支持Oracle、SQL Server、DB2、MySQL、PostgreSQL等数据库，提供建表…

> 🥉 **[tikv/raft-rs](https://github.com/tikv/raft-rs)** · ⭐ 3.4k · 本周 **+4**
> `其他` · 适用：TiDB
> Raft distributed consensus algorithm implemented in Rust.
> 🤖 **AI 解读**：TiDB 用 Rust 实现 Raft 共识，保障节点故障时集群一致，供数据库使用者参考。

### 🔍 本周解读 · dbbridge

> 🔍 **[suoten/dbbridge](https://github.com/suoten/dbbridge)** · ⭐ 10 · 本周 **+10**
> `其他` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持 MySQL/PostgreSQL/SQLite/OceanBase/TiDB/达梦/金仓 等 10 种数据库互转。单文件 < 30MB，双击即用。

**解决什么**：DBBridge 用于异构数据库之间的结构与数据迁移，将手工改写 SQL、逐行排查语法的工作转为图形化操作，填好连接信息即可完成迁移。

**核心亮点**：开源免费、零依赖单文件运行、图形界面三步迁移、支持多数据库互转、迁移前自动备份并可回滚、内置 SQL 转换与校验工具箱。

**使用场景**：适合本地与测试环境搭建同构表结构、将备份 SQL 文件导入异构库、信创环境下关系型数据库之间的迁移，以及迁移前后的结构检查与数据校验。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[ClickHouse/mcp-clickhouse](https://github.com/ClickHouse/mcp-clickhouse)** · ⭐ 866 · 本周 **+866**
> `其他` · 适用：ClickHouse
> Connect ClickHouse to your AI assistants.
> 🤖 **AI 解读**：ClickHouse MCP服务器让AI助手连接ClickHouse，支持执行只读SQL查询、列出数据库与表，便于数据探查。

> 🥈 **[oracle/mcp](https://github.com/oracle/mcp)** · ⭐ 434 · 本周 **+434**
> `其他` · 适用：Oracle
> Repository containing MCP (Model Context Protocol) servers that provides a…
> 🤖 **AI 解读**：Oracle MCP仓库提供参考级MCP服务器，供客户端以标准化方式管理Oracle产品，含多语言示例，非生产用途。

> 🥉 **[MariaDB/mcp](https://github.com/MariaDB/mcp)** · ⭐ 200 · 本周 **+200**
> `其他` · 适用：MySQL / MariaDB
> MariaDB MCP (Model Context Protocol) server implementation
> 🤖 **AI 解读**：MariaDB MCP服务器为AI助手提供标准接口，支持查询MariaDB及向量检索。

### 🔍 本周解读 · mcp-clickhouse

> 🔍 **[ClickHouse/mcp-clickhouse](https://github.com/ClickHouse/mcp-clickhouse)** · ⭐ 866 · 本周 **+866**
> `其他` · 适用：ClickHouse
> Connect ClickHouse to your AI assistants.

**解决什么**：将 ClickHouse 数据库接入 AI 助手，通过 MCP 协议让助手执行查询、列出库表。

**核心亮点**：实现 MCP 2026-07-28 并兼容旧版握手、run_query 支持参数化与只读默认、list_tables 分页与列元数据、大整数以字符串保精度。

**使用场景**：适合在 AI 助手中查询 ClickHouse 数据、浏览库表结构、以参数化方式安全执行只读 SQL 及预估查询读取量的场景。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.6k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.7k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.4k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.1k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and… |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.6k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-09-05）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
