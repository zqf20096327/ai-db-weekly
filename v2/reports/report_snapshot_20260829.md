# 📋 数据库开源生态周报 · 第 4 期

> 📌 **数据源**：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

> _2026-08-29_

---

## 📌 本周 DBA 速览

- 🗄️ **国外数据库**：[node-gtfs](https://github.com/BlinkTagInc/node-gtfs)（+503）—— Import, validate, query, and export GTFS Schedule and…
- 🇨🇳 **国产数据库**：[bytebase](https://github.com/bytebase/bytebase)（+31）—— Database governance built for humans and agents —…
- 🤖 **AI工具**：[bunqueue](https://github.com/egeominotti/bunqueue)（+540）—— ⚡ High-performance job queue for Bun. SQLite by default…



## 🗄️ 板块一 · 国际主流数据库
> 范围：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse。仅收录上述数据库生态的开源工具，不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[BlinkTagInc/node-gtfs](https://github.com/BlinkTagInc/node-gtfs)** · ⭐ 503 · 本周 **+503**
> `其他` · 适用：MySQL / PostgreSQL
> Import, validate, query, and export GTFS Schedule and Realtime data with…
> 🤖 **AI 解读**：该工具可将GTFS公交数据导入MySQL或PostgreSQL，供查询与导出。

> 🥈 **[databasus/databasus](https://github.com/databasus/databasus)** · ⭐ 8.4k · 本周 **+381**
> `备份` · 适用：MySQL / PostgreSQL / MariaDB
> PostgreSQL backup tool with Point-In-Time-Recovery and restore verification
> 🤖 **AI 解读**：Databasus 是自托管开源备份工具，支持 PostgreSQL 等数据库，提供时间点恢复与恢复校验，可存至多种存储并发送通知。

> 🥉 **[AndrianBdn/oddk](https://github.com/AndrianBdn/oddk)** · ⭐ 238 · 本周 **+238**
> `备份` · 适用：PostgreSQL
> Opinionated Database Deployment Kit — locally running RDS for PostgreSQL
> 🤖 **AI 解读**：ODDK 是本地运行 PostgreSQL 的部署工具，支持快照备份至 S3 与按需恢复。

### 🔍 本周解读 · node-gtfs

> 🔍 **[BlinkTagInc/node-gtfs](https://github.com/BlinkTagInc/node-gtfs)** · ⭐ 503 · 本周 **+503**
> `其他` · 适用：MySQL / PostgreSQL
> Import, validate, query, and export GTFS Schedule and Realtime data with SQLite, PostgreSQL, and MySQL.

**解决什么**：将GTFS公交静态与实时数据导入轻量级文件数据库、PostgreSQL或MySQL，并支持查询、更新与导出。

**核心亮点**：支持静态GTFS导入、GTFS-Realtime更新、轻量级文件数据库同步查询、导出GTFS文件、可选表与索引管理。

**使用场景**：适合本地探索公交数据、在Node.js应用中查询班次、刷新实时到站信息、将数据库还原为GTFS文件。



## 🇨🇳 板块二 · 国内数据库
> 范围：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB。仅收录上述数据库生态的开源项目（内核以各厂商官方为准），不含 AI 项目。

### 🔥 活跃榜 Top3

> 🥇 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.4k · 本周 **+31**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and…
> 🤖 **AI 解读**：Bytebase是开源数据库治理平台，为人员与AI代理提供变更管理、访问控制及合规审计，支持Oracle、MySQL等数据库。

> 🥈 **[ClouGence/open-cdm](https://github.com/ClouGence/open-cdm)** · ⭐ 376 · 本周 **+6**
> `管理` · 适用：12+种数据库（Oracle / SQL Server / DB2等）
> A free and open-source database management tool, suitable for team use. It…
> 🤖 **AI 解读**：CloudDM是开源数据库管理工具，支持Oracle、MySQL等12+种数据库，提供访问控制、数据脱敏与SQL审计，便于团队协作。

> 🥉 **[gaoyuan98/dameng_exporter](https://github.com/gaoyuan98/dameng_exporter)** · ⭐ 81 · 本周 **+3**
> `监控` · 适用：DM
> 达梦数据库的exporter采集器 ，可对接prometheus+grafana 提供表盘
> 🤖 **AI 解读**：达梦数据库的Prometheus采集器，支持多实例监控，提供30余项指标，可对接Grafana展示。

### 🔍 本周解读 · bytebase

> 🔍 **[bytebase/bytebase](https://github.com/bytebase/bytebase)** · ⭐ 14.4k · 本周 **+31**
> `管理` · 适用：8+种数据库（Oracle / SQL Server / MySQL等）
> Database governance built for humans and agents — controlling changes and access across every major database.

**解决什么**：统一管理人与AI代理对多种数据库的变更与访问，替代分散的迁移脚本、SQL客户端和工单系统。

**核心亮点**：变更工作流与GitOps集成、细粒度RBAC与即时访问、动态数据脱敏、审计日志与策略代码化、MCP连接AI代理。

**使用场景**：开发团队管理数据库模式版本与CI/CD部署；DBA集中管控多环境并执行SQL规范；安全团队控制列级访问与脱敏审计。



## 🤖 板块三 · AI 工具
> 范围：板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）。

### 🔥 活跃榜 Top3

> 🥇 **[t8y2/dbx](https://github.com/t8y2/dbx)** · ⭐ 17.3k · 本周 **+1085**
> `平台` · 适用：15+种数据库（Oracle / SQL Server / DB2等）
> 20 MB lightweight cross-platform database client for 90+ databases, including…
> 🤖 **AI 解读**：轻量跨平台数据库客户端，支持多种数据库，含桌面、Docker、CLI及AI助手，便于连接与管理。

> 🥈 **[egeominotti/bunqueue](https://github.com/egeominotti/bunqueue)** · ⭐ 540 · 本周 **+540**
> `其他` · 适用：MySQL / PostgreSQL
> ⚡ High-performance job queue for Bun. SQLite by default, PostgreSQL…
> 🤖 **AI 解读**：面向 Bun 的任务队列，默认用嵌入式数据库，扩展时支持 PostgreSQL 多代理，含死信、定时与备份。

> 🥉 **[TabularisDB/tabularis](https://github.com/TabularisDB/tabularis)** · ⭐ 4.4k · 本周 **+217**
> `平台` · 适用：9+种数据库（Oracle / SQL Server / DB2等）
> Open-source desktop SQL workspace for PostgreSQL, MySQL/MariaDB, SQLite and 15+…
> 🤖 **AI 解读**：Tabularis 是开源桌面 SQL 工作台，支持多种数据库，内置 MCP 服务与 SQL 笔记本，便于查询与结构管理。

### 🔍 本周解读 · bunqueue

> 🔍 **[egeominotti/bunqueue](https://github.com/egeominotti/bunqueue)** · ⭐ 540 · 本周 **+540**
> `其他` · 适用：MySQL / PostgreSQL
> ⚡ High-performance job queue for Bun. SQLite by default, PostgreSQL multi-broker when you scale. DLQ, cron, SQLite S3…

**解决什么**：为 Bun 运行时提供作业队列，默认用 轻量级文件数据库 单文件持久化，扩展时可切换 PostgreSQL 多代理，无需 内存数据库。

**核心亮点**：支持内存与 轻量级文件数据库 持久化、PostgreSQL 多代理、死信队列与定时任务、轻量级文件数据库 备份至对象存储、原生 MCP。

**使用场景**：适合 Bun 应用的后台作业处理、AI 代理与自动化任务调度，以及需要从单机 轻量级文件数据库 平滑扩展到 PostgreSQL 多代理的部署。



## 📊 Top 总榜（历史 Star 总数）

| 项目 | 总 Star | 板块 | 分类 | 一句话定位 |
| :--- | ---: | :--- | :--- | :--- |
| **[grafana/grafana](https://github.com/grafana/grafana)** | 76.5k | 国外数据库 | 监控 | The open and composable observability and data visualization… |
| **[dbeaver/dbeaver](https://github.com/dbeaver/dbeaver)** | 51.6k | 国外数据库 | 其他 | Free universal database tool and SQL client |
| **[drawdb-io/drawdb](https://github.com/drawdb-io/drawdb)** | 39.3k | 国外数据库 | 其他 | Free, simple, and intuitive online database diagram editor and SQL… |
| **[OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB)** | 28.1k | AI工具 | 管理 | Chat2DB is a free, cross-platform, local-first database client and… |
| **[PostgREST/postgrest](https://github.com/PostgREST/postgrest)** | 27.6k | 国外数据库 | 其他 | REST API for any Postgres database |



## 💬 互动与说明

- 💬 **互动**：本周你最关注哪个项目？欢迎留言分享你的试用体验。
- 📌 **板块范围**：板块一 Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse；板块二 openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB；板块三为上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
- 📌 **说明**：由 `ai_db_weekly` 基于 GitHub 数据自动采集（截至 2026-08-29）。项目描述来自 GitHub 项目的 description 字段；AI 解读基于项目 README，由 AI 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。分类字段采用固定枚举值。


---
