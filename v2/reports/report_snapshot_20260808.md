# 📋 数据库开源生态周报 · 第 1 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-08-08_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[drawdb](https://github.com/drawdb-io/drawdb)（+213）—— Free, simple, and intuitive online database diagram editor…
- 🇨🇳 **国产数据库**：[bytebase](https://github.com/bytebase/bytebase)（+6）—— Database governance built for humans and agents —…
- 🤖 **AI工具**：[WrenAI](https://github.com/Canner/WrenAI)（+301）—— GenBI (Generative BI) for AI agents, an open-source…



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** · ⭐ 38.5k · 本周 **+213**
> `其他` · 适用：Oracle / PostgreSQL / MariaDB
> Free, simple, and intuitive online database diagram editor and SQL generator.
> 🤖 **AI 解读**：浏览器端ERD编辑器，可绘制数据库关系图并生成SQL，支持Oracle、PostgreSQL、MariaDB等。

> 🥈 **[grafana/grafana](https://github.com/grafana/grafana)** · ⭐ 76.2k · 本周 **+60**
> `监控` · 适用：MySQL / PostgreSQL
> The open and composable observability and data visualization platform.…
> 🤖 **AI 解读**：Grafana 是开源可组合监控可视化平台，可查询 MySQL、PostgreSQL 等数据源并展示指标、日志与追踪，支持告警。

> 🥉 **[warp-tech/warpgate](https://github.com/warp-tech/warpgate)** · ⭐ 7.5k · 本周 **+54**
> `连接/代理` · 适用：MySQL / PostgreSQL
> Fully transparent SSH, HTTPS, Kubernetes, MySQL and Postgres bastion/PAM that…
> 🤖 **AI 解读**：Warpgate 是透明代理堡垒机，支持 MySQL 与 PostgreSQL，可审计会话，无需客户端软件。

### 🔍 本周解读 · drawdb

> 🔍 **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** · ⭐ 38.5k · 本周 **+213**
> `其他` · 适用：Oracle / PostgreSQL / MariaDB
> Free, simple, and intuitive online database diagram editor and SQL generator.

**解决什么**：浏览器端数据库ERD编辑器，通过点击操作绘制实体关系图，并导入导出SQL脚本、生成迁移，无需注册账户。

**核心亮点**：在线绘制数据库关系图、SQL导入导出、迁移生成、编辑器自定义、无需账户、支持Docker部署。

**使用场景**：数据库建模与设计、SQL脚本互转、团队共享图表、本地或容器化部署。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.4k · 本周 **+6**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and…
> 🤖 **AI 解读**：Bytebase 是开源数据库治理平台，统一管控变更、访问与合规，支持 Oracle、MySQL、PostgreSQL 等。

> 🥈 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 341 · 本周 **+4**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It…
> 🤖 **AI 解读**：CloudDM是开源数据库管理工具，支持Oracle、MySQL等，提供权限管控、脱敏与SQL审计。

> 🥉 **[dotnetcore/FreeSql](https://github.com/dotnetcore/FreeSql)** · ⭐ 4.4k · 本周 **+3**
> `其他` · 适用：7+种数据库（Oracle / SQL Server / MySQL等）
> .NET aot orm, VB.NET/C# orm, Mysql/PostgreSQL/SqlServer/Oracle orm…
> 🤖 **AI 解读**：FreeSql是.NET平台的ORM组件，支持AOT，可映射多种关系型数据库，提供数据迁移与导入功能。

### 🔍 本周解读 · bytebase

> 🔍 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.4k · 本周 **+6**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access across every major database.

**解决什么**：提供数据库变更与访问的统一管控平面，衔接人员与AI代理，使每次变更和查询可审查、可控制、可记录。

**核心亮点**：变更管理含GUI流程与GitOps集成、SQL审核规则；细粒度RBAC与即时访问、动态脱敏；审计日志与策略代码化；MCP服务与AI辅助。

**使用场景**：开发团队做模式版本控制与CI/CD部署；DBA集中管理多环境并统一SQL规范；安全团队管控列级权限与脱敏、留存审计记录。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[Canner/WrenAI](https://github.com/Canner/WrenAI)** · ⭐ 17.2k · 本周 **+301**
> `平台` · 适用：PostgreSQL / ClickHouse
> GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL…
> 🤖 **AI 解读**：WrenAI是开源生成式BI引擎，可将自然语言转为SQL与图表，支持PostgreSQL、ClickHouse等数据源。

> 🥈 **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** · ⭐ 27.8k · 本周 **+202**
> `其他` · 适用：8+种数据库（Oracle / SQL Server / DB2等）
> 🔥🔥🔥 AI-driven database tool and SQL client, The hottest GUI client, supporting…
> 🤖 **AI 解读**：Chat2DB是AI驱动的数据库客户端，支持Oracle、SQL Server、DB2等，可编写SQL并借AI辅助生成与优化。

> 🥉 **[sinaptik-ai/pandas-ai](https://github.com/sinaptik-ai/pandas-ai)** · ⭐ 23.7k · 本周 **+39**
> `其他` · 适用：待确认
> Chat with your database or your datalake (SQL, CSV, parquet). PandasAI makes…
> 🤖 **AI 解读**：PandasAI是Python库，支持用自然语言查询SQL、CSV等数据，辅助非技术用户分析数据。

### 🔍 本周解读 · WrenAI

> 🔍 **[Canner/WrenAI](https://github.com/Canner/WrenAI)** · ⭐ 17.2k · 本周 **+301**
> `平台` · 适用：PostgreSQL / ClickHouse
> GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL through an open context layer that turns…

**解决什么**：面向AI代理的自然语言问数场景，将业务问题转为受治理的SQL、图表与仪表板，并跨多种数据源统一语义。

**核心亮点**：开放AI上下文层与语义层、受治理的文本转SQL、干跑校验与结构化错误、可版本化知识文件。

**使用场景**：适合AI代理构建、跨库自助分析、需语义治理与可审查上下文的BI场景，支持PostgreSQL、ClickHouse等。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.2k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.3k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 38.5k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 27.8k | AI工具 | 其他 | 🔥🔥🔥 AI-driven database tool and SQL client, The hottest GUI client… |
| **[sinaptik-ai/pandas-ai](https://github.com/sinaptik-ai/pandas-ai)** | 23.7k | AI工具 | 其他 | Chat with your database or your datalake (SQL, CSV, parquet).… |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-08-08）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
