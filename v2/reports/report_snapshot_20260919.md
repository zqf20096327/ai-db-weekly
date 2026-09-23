# 📋 数据库开源生态周报 · 第 7 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-09-19_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[pgbot](https://github.com/pgrundev/pgbot)（+159）—— Postgres intelligence for ai agents & apps
- 🇨🇳 **国产数据库**：[goInception](https://github.com/hanchuanchuan/goInception)（+3）—— 一个集审核、执行、备份及生成回滚语句于一身的MySQL运维工具
- 🤖 **AI工具**：[harlequin](https://github.com/tconbeer/harlequin)（+6404）—— The SQL IDE for Your Terminal.



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[pgrundev/pgbot](https://github.com/pgrundev/pgbot)** · ⭐ 1.3k · 本周 **+159**
> `其他` · 适用：PostgreSQL
> Postgres intelligence for ai agents & apps
> 🤖 **AI 解读**：pgbot 是 PostgreSQL 只读观测工具，读取系统统计视图，输出健康报告及变化，供 AI 代理与应用使用。

> 🥈 **[databasus/databasus](https://github.com/databasus/databasus)** · ⭐ 8.6k · 本周 **+80**
> `备份` · 适用：MySQL / PostgreSQL / MariaDB
> PostgreSQL backup tool with Point-In-Time-Recovery and restore verification
> 🤖 **AI 解读**：Databasus 是自托管开源备份工具，支持 PostgreSQL 等数据库，提供时间点恢复与恢复校验。

> 🥉 **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** · ⭐ 51.8k · 本周 **+73**
> `其他` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> Free universal database tool and SQL client
> 🤖 **AI 解读**：DBeaver是免费通用数据库工具与SQL客户端，支持Oracle、SQL Server、DB2等，提供SQL编辑、数据管理与AI辅助功能。

### 🌱 新锐发现（最多 3 个）

> ① **[cumakurt/central-flow-collector](https://github.com/cumakurt/central-flow-collector)** · ⭐ 4 · 本周 **+4**
> `监控` · 适用：ClickHouse
> High-performance NetFlow, IPFIX and sFlow collector with flow analytics…
> 🤖 **AI 解读**：该工具采集NetFlow、IPFIX与sFlow，归一化后存入ClickHouse，供流量查询与容量分析。

> ② **[Sahil1337/perch](https://github.com/Sahil1337/perch)** · ⭐ 3 · 本周 **+3**
> `其他` · 适用：MySQL / PostgreSQL
> A lightweight SQL workspace for developers. Explore schemas, write and run SQL…
> 🤖 **AI 解读**：Perch 是面向开发者的轻量 SQL 工作区，支持 MySQL 与 PostgreSQL，本地运行，提供模式浏览、编辑与查询执行。

> ③ **[ClickHouse/kb2cs](https://github.com/ClickHouse/kb2cs)** · ⭐ 0 · 近7天 1 commits
> `其他` · 适用：ClickHouse
> Skill for migrating Elasticsearch and Kibana dashboards to ClickHouse and…
> 🤖 **AI 解读**：该项目用于将 Elasticsearch 与 Kibana 仪表板迁移至 ClickHouse 和 ClickStack，便于相关使用者转移可视化配置。

### 🔍 本周解读 · pgbot

> 🔍 **[pgrundev/pgbot](https://github.com/pgrundev/pgbot)** · ⭐ 1.3k · 本周 **+159**
> `其他` · 适用：PostgreSQL
> Postgres intelligence for ai agents & apps

**解决什么**：提供PostgreSQL数据库内可观测性，以只读方式读取统计视图，输出健康报告及与上次的差异。

**核心亮点**：单静态二进制、只读连接、无需代理或外部服务、findings优先报告、JSON契约版本化、支持MCP与CI集成。

**使用场景**：数据库健康巡检、性能问题排查、CI中自动化检查、AI代理调用数据库诊断工具。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.5k · 本周 **+19**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and…
> 🤖 **AI 解读**：Bytebase 是开源数据库治理平台，统一管理变更、访问与合规，支持 Oracle、MySQL、PostgreSQL 等。

> 🥈 **[suoten/dbbridge](https://github.com/suoten/dbbridge)** · ⭐ 28 · 本周 **+9**
> `其他` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> Description: 开源、免费、零依赖的数据库迁移与SQL转换工具。支持 Mssql/MySQL/PostgreSQL/SQLite/OceanBase/…
> 🤖 **AI 解读**：DBBridge 是开源数据库迁移与 SQL 转换工具，支持 Oracle、MySQL、PostgreSQL、TiDB、OceanBase、DM 等互转…

> 🥉 **[hanchuanchuan/goInception](https://github.com/hanchuanchuan/goInception)** · ⭐ 1.7k · 本周 **+3**
> `其他` · 适用：SQL Server / MySQL / PostgreSQL / TiDB
> 一个集审核、执行、备份及生成回滚语句于一身的MySQL运维工具
> 🤖 **AI 解读**：goInception 是 MySQL 运维工具，可审核、执行 SQL，备份并生成回滚语句，支持 TiDB。

### 🔍 本周解读 · goInception

> 🔍 **[hanchuanchuan/goInception](https://github.com/hanchuanchuan/goInception)** · ⭐ 1.7k · 本周 **+3**
> `其他` · 适用：SQL Server / MySQL / PostgreSQL / TiDB
> 一个集审核、执行、备份及生成回滚语句于一身的MySQL运维工具

**解决什么**：面向MySQL运维，提供SQL审核、执行、备份与回滚语句生成能力，基于自定义规则解析语法并返回审核结果。

**核心亮点**：基于TiDB SQL解析器、支持审核与执行、自动备份、生成回滚语句、可配置审核规则。

**使用场景**：适用于MySQL变更发布前的SQL审核、上线执行、数据备份及回滚方案准备等运维环节。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[tconbeer/harlequin](https://github.com/tconbeer/harlequin)** · ⭐ 6.4k · 本周 **+6404**
> `其他` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB
> The SQL IDE for Your Terminal.
> 🤖 **AI 解读**：Harlequin 是终端中的 SQL IDE，支持 SQL Server、MySQL、PostgreSQL、MariaDB 等，便于在命令行连接并操作数据库。

> 🥈 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 20.1k · 本周 **+884**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including…
> 🤖 **AI 解读**：轻量跨平台数据库客户端，支持Oracle、MySQL等，含AI助手与CLI，便于统一管理多种数据库。

> 🥉 **[Canner/WrenAI](https://github.com/Canner/WrenAI)** · ⭐ 17.7k · 本周 **+98**
> `平台` · 适用：PostgreSQL / ClickHouse
> GenBI (Generative BI) for AI agents, an open-source, governed text-to-SQL…
> 🤖 **AI 解读**：WrenAI是开源GenBI引擎，可将自然语言转为SQL，支持PostgreSQL、ClickHouse等数据源。

### 🔍 本周解读 · harlequin

> 🔍 **[tconbeer/harlequin](https://github.com/tconbeer/harlequin)** · ⭐ 6.4k · 本周 **+6404**
> `其他` · 适用：SQL Server / MySQL / PostgreSQL / MariaDB
> The SQL IDE for Your Terminal.

**解决什么**：终端中运行的SQL集成开发环境，提供图形化查询编辑与结果浏览，无需离开命令行即可操作数据库。

**核心亮点**：基于文本界面的SQL编辑器、支持嵌入式分析数据库与轻量级文件数据库内置适配器、可通过插件连接多种数据库、支持主题与快捷键自定义。

**使用场景**：适合在终端环境下编写和执行SQL、管理多种关系型数据库、进行数据查询与结果查看的场景。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.8k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.8k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.6k | AI工具 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.2k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and… |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.7k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-09-19）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
