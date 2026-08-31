# 📋 数据库开源生态周报 · 第 4 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-08-31_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[ClickBench](https://github.com/ClickHouse/ClickBench)（+1092）—— ClickBench: a Benchmark For Analytical Databases
- 🇨🇳 **国产数据库**：[bytebase](https://github.com/bytebase/bytebase)（+44）—— Database governance built for humans and agents — controllin
- 🤖 **AI工具**：[dbx](https://github.com/t8y2/dbx)（+1134）—— 20 MB lightweight cross-platform database client for 90+ dat



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[ClickHouse/ClickBench](https://github.com/ClickHouse/ClickBench)** · ⭐ 1.1k · 本周 **+1092**
> `其他` · 适用：6+种数据库（SQL Server / MySQL / PostgreSQL等）
> ClickBench: a Benchmark For Analytical Databases
> 🤖 **AI 解读**：ClickBench是面向分析型数据库的基准测试项目，提供标准化数据集与查询，用于评估ClickHouse等OLAP系统的性能，支持多种SQL数据库的复现测试。

> 🥈 **[MariaDB/mariadb-docker](https://github.com/MariaDB/mariadb-docker)** · ⭐ 926 · 本周 **+926**
> `其他` · 适用：MySQL / MariaDB
> Docker Official Image packaging for MariaDB
> 🤖 **AI 解读**：MariaDB官方Docker镜像构建仓库，由MariaDB基金会维护。提供容器化部署、密码重置及初始化脚本执行方法

> 🥉 **[oracle/python-cx_Oracle](https://github.com/oracle/python-cx_Oracle)** · ⭐ 887 · 本周 **+887**
> `其他` · 适用：Oracle
> Obsolete Python interface to Oracle Database, now superseded by python-oracledb
> 🤖 **AI 解读**：cx_Oracle是Oracle数据库的Python接口，2022年停止维护，由python-oracledb取代，沿用相同API并新增功能，可通过pip安装。

### 🌱 新锐发现（最多 3 个）

> ① **[antifailure/antifailure](https://github.com/antifailure/antifailure)** · ⭐ 12 · 本周 **+12**
> `平台` · 适用：PostgreSQL
> A disposable copy of your production stack for every pull request: masked Postgr
> 🤖 **AI 解读**：Antifailure为每个PR生成一次性生产环境副本，含脱敏PostgreSQL分支、隔离API及模拟用户操作的代理，并验证脱敏效果。

> ② **[jiff3/rxrelay](https://github.com/jiff3/rxrelay)** · ⭐ 3 · 本周 **+3**
> `平台` · 适用：PostgreSQL
> Public medication-shortage intelligence platform with openFDA ingestion, RxNorm 
> 🤖 **AI 解读**：RxRelay 基于 PostgreSQL 存储 FDA 药品短缺数据，提供事件驱动监控与检索 API，供数据库使用者分析药品供应状态变化。

> ③ **[OjasKugore/Mantis](https://github.com/OjasKugore/Mantis)** · ⭐ 3 · 本周 **+3**
> `管理` · 适用：PostgreSQL
> Modern enterprise defect tracking, vulnerability scoring (CVSS v4.0), and releas
> 🤖 **AI 解读**：Mantis是基于PostgreSQL的缺陷与发布治理平台，提供CVSS v4.0计算、缺陷状态机及AI分诊。

### 🔍 本周解读 · ClickBench

> 🔍 **[ClickHouse/ClickBench](https://github.com/ClickHouse/ClickBench)** · ⭐ 1.1k · 本周 **+1092**
> `其他` · 适用：6+种数据库（SQL Server / MySQL / PostgreSQL等）
> ClickBench: a Benchmark For Analytical Databases

**解决什么**：ClickBench 面向点击流、网络分析和事件数据等典型分析负载，提供一套可复现的基准测试流程，用于评估各类数据库在即席查询和实时看板场景下的性能表现。

**核心亮点**：数据集来自真实生产流量并匿名化，保留关键分布。测试脚本覆盖安装、加载、运行和结果收集，约20分钟完成。含43条查询，覆盖全表扫描、过滤扫描、索引查找及主要关系操作。支持自管理、云托管

**使用场景**：适用于需要评估分析型数据库性能的研发团队、数据库选型决策者，以及关注硬件存储吞吐、CPU多核与单核性能、内存带宽等不同维度对查询效率影响的场景。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+44**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access
> 🤖 **AI 解读**：Bytebase是开源数据库治理平台，统一管理变更、访问与合规。支持Oracle、SQL Server、MySQL、PostgreSQL、MariaDB

> 🥈 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 376 · 本周 **+5**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It offer
> 🤖 **AI 解读**：CloudDM是开源数据库管理工具，面向团队协作，提供访问控制、数据脱敏、SQL审计及CI/CD能力，支持跨地域部署，兼容Oracle、SQL Server

> 🥉 **[tikv/raft-rs](https://github.com/tikv/raft-rs)** · ⭐ 3.4k · 本周 **+4**
> `其他` · 适用：TiDB
> Raft distributed consensus algorithm implemented in Rust.
> 🤖 **AI 解读**：raft-rs是TiKV团队用Rust实现的Raft共识算法库，支持日志复制与状态机同步，可用于构建高可用集群，在节点故障时维持数据一致性。

### 🌱 新锐发现（最多 3 个）

> ① **[suoten/dbbridge](https://github.com/suoten/dbbridge)** · ⭐ 1 · 本周 **+1**
> `其他` · 适用：8+种数据库（MySQL / PostgreSQL / MariaDB等）
> Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持 MySQL/PostgreSQL/SQLite/OceanBase/TiDB/达
> 🤖 **AI 解读**：DBBridge是开源免费的数据库迁移与SQL转换工具，支持MySQL、PostgreSQL、TiDB、OceanBase、DM等十余种数据库互转。单文件运行

### 🔍 本周解读 · bytebase

> 🔍 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+44**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access across every major database.

**解决什么**：数据库变更与访问管控分散在多个工具中，导致流程割裂、权限不清、审计缺失。Bytebase 提供一个统一控制平面，将变更管理、访问控制与合规记录集中到单一平台，覆盖主流数据库。

**核心亮点**：支持GUI与GitOps双路径变更，内置200+SQL审查规则。提供角色权限、临时授权与动态列级脱敏。具备完整审计日志，支持Terraform与API策略代码化。集成MCP协议，支持AI代理接入。

**使用场景**：适用于需规范化数据库变更流程的开发团队、集中管理多环境数据库的DBA，及要求列级权限控制与审计追踪的安全合规场景。支持Oracle、SQL Server、MySQL、PostgreSQL



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 17.5k · 本周 **+1134**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including My
> 🤖 **AI 解读**：20MB客户端支持90余种数据库，覆盖Oracle、SQL Server、DB2、MySQL、PostgreSQL等，提供桌面、Docker

> 🥈 **[ClickHouse/mcp-clickhouse](https://github.com/ClickHouse/mcp-clickhouse)** · ⭐ 862 · 本周 **+862**
> `其他` · 适用：ClickHouse
> Connect ClickHouse to your AI assistants.
> 🤖 **AI 解读**：为ClickHouse提供MCP服务，支持SQL查询、库表列举及分页，可接入AI助手。另含chDB嵌入式查询工具，支持直查文件与URL数据。

> 🥉 **[egeominotti/bunqueue](https://github.com/egeominotti/bunqueue)** · ⭐ 544 · 本周 **+544**
> `其他` · 适用：MySQL / PostgreSQL
> ⚡ High-performance job queue for Bun. SQLite by default, PostgreSQL multi-broker
> 🤖 **AI 解读**：Bunqueue是Bun运行时的任务队列，默认用嵌入式数据库存储，可扩展至PostgreSQL多代理模式，支持死信队列、定时任务及备份

### 🌱 新锐发现（最多 3 个）

> ① **[jamesdffgy-source/DBQuill](https://github.com/jamesdffgy-source/DBQuill)** · ⭐ 40 · 本周 **+40**
> `其他` · 适用：MySQL / PostgreSQL
> Open-source, local-first AI database agent for natural-language SQL, safe writes
> 🤖 **AI 解读**：DBQuill是本地优先的开源AI数据库代理，支持自然语言转SQL、安全写入与图表展示，适用于MySQL、PostgreSQL及轻量级文件数据库

> ② **[mustafaabasaran/planizer](https://github.com/mustafaabasaran/planizer)** · ⭐ 6 · 本周 **+6**
> `其他` · 适用：SQL Server / PostgreSQL
> SQL Server / T-SQL migration linter: validates and explains DDL before it runs —
> 🤖 **AI 解读**：Planizer是面向SQL Server迁移脚本的静态分析工具，输出规则ID、严重级别、位置及修复建议，可作CI校验与人工审查参考。

> ③ **[contributorai/pivotal-claw](https://github.com/contributorai/pivotal-claw)** · ⭐ 4 · 本周 **+4**
> `迁移` · 适用：PostgreSQL / ClickHouse
> Local-first Kanban for human and AI-agent work, with Postgres CDC into ClickHous
> 🤖 **AI 解读**：Pivotal Claw为本地优先看板工具，以Markdown为源，经PostgreSQL事件账本通过ClickPipe同步至ClickHouse

### 🔍 本周解读 · dbx

> 🔍 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 17.5k · 本周 **+1134**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including MySQL, PostgreSQL, SQLite, Redis, MongoDB,

**解决什么**：20 MB安装包集成90余种数据库连接能力，覆盖MySQL、PostgreSQL、轻量级文件、内存、文档、Oracle、SQL Server、DB2、达梦等主流及国产数据库

**核心亮点**：内置AI助手辅助SQL编写与运维操作。提供桌面端、Docker、CLI三种使用形态，并支持MCP Server协议接入。跨平台运行，适配Windows、macOS与Linux环境。

**使用场景**：适用于个人开发者本地管理多种异构数据库，也适合团队在Docker或CI/CD环境中集成数据库操作，以及需要通过MCP协议将数据库能力接入AI工作流的场景。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.5k | 国外数据库 | 监控 | The open and composable observability and data visualization platform. |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.6k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.3k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL gen |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.1k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and SQL |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.6k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-08-31）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
