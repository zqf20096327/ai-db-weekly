# AI×DB 周报

聚焦「AI 与数据库结合」的开源项目周报。每天自动采集 GitHub 数据，
按**周 star 增量**排序，输出一份 Markdown，直接复制贴公众号。

<!-- LATEST:START --> 本期周报区块由脚本 update_readme() 自动维护，请勿手动编辑此段 -->
> 📖 **本期周报**：[第 4 期 · 2026-08-10](output/2026-08-10.md)
> 📚 **历史周报**：见文末[「往期周报」](#往期周报)

---

**📌 今日聚焦**

🔥 本周增长王：**Chat2DB**（📈 +285/周）
🆕 新项目：**Mekka**（⭐4）
🎯 重点解读：**Chat2DB**

---

## 🔥 本周热门 Top10

---

**1. OtterMind/Chat2DB**  ⭐27.9k · Java · 📈+285/周 · 更新 0天前
> Chat2DB是一款支持40多种数据库的AI驱动数据库客户端，提供SQL工作台和自带AI模型辅助生成、优化SQL。

🔗 https://github.com/OtterMind/Chat2DB


---

**2. bytebase/dbhub**  ⭐3.3k · TypeScript · 📈+43/周 · 更新 2天前
> DBHub 是一个极简 MCP 服务器，让 MCP 客户端通过单一接口连接并探索 PostgreSQL、MySQL 等数据库，默认仅加载两个工具，令牌消耗低至 1.4k。

🔗 https://github.com/bytebase/dbhub


---

**3. googleapis/mcp-toolbox**  ⭐16.1k · Go · 📈+31/周 · 更新 1天前
> MCP Toolbox for Databases 是一个开源 MCP 服务器，用于将 AI 代理、IDE 和应用程序直接连接到企业数据库，并提供预构建的通用工具。

🔗 https://github.com/googleapis/mcp-toolbox


---

**4. dosco/graphjin**  ⭐3.1k · Go · 📈+7/周 · 更新 1天前
> GraphJin 是一个将数据库、仓库、文件等系统统一为受治理图并通过 GraphQL 与 MCP 暴露给 AI 代理的编译器和运行时。

🔗 https://github.com/dosco/graphjin


---

**5. oracle-devrel/oracle-ai-developer-hub**  ⭐4.3k · Jupyter Notebook · 📈+6/周 · 更新 1天前
> 该仓库提供利用Oracle AI数据库和OCI服务构建AI应用、代理及系统的技术资源与参考实现。

🔗 https://github.com/oracle-devrel/oracle-ai-developer-hub


---

**6. NodeDB-Lab/nodedb**  ⭐185 · Rust · 📈+5/周 · 更新 1天前
> NodeDB是为AI代理设计的统一内存与存储引擎，支持语义、关系、情景和时间序列数据，可嵌入设备并同步至分布式服务器。

🔗 https://github.com/NodeDB-Lab/nodedb


---

**7. julien040/anyquery**  ⭐1.7k · Go · 📈+3/周 · 更新 4天前
> Anyquery是一个基于SQLite的SQL查询引擎，可通过插件查询文件、数据库和应用，并支持连接LLM访问数据。

🔗 https://github.com/julien040/anyquery


---

**8. TencentCloudBase/CloudBase-AI-Toolkit**  ⭐1.1k · TypeScript · 📈+3/周 · 更新 0天前
> CloudBase AI Toolkit 是腾讯云为 AI 编程工具提供的后端集成层，通过 MCP 在对话中操作数据库、函数和存储并部署。

🔗 https://github.com/TencentCloudBase/CloudBase-AI-Toolkit


---

**9. call518/MCP-PostgreSQL-Ops**  ⭐159 · Python · 📈+3/周 · 更新 5天前
> 这是一个基于自然语言查询的PostgreSQL运维监控MCP服务器，支持12-18版本，提供只读安全操作和智能维护建议。

🔗 https://github.com/call518/MCP-PostgreSQL-Ops


---

**10. prest/prest**  ⭐4.6k · Go · 📈+2/周 · 更新 1天前
> pREST是一个基于Go的PostgreSQL REST API工具，能在现有或新建Postgres数据库上即时提供CRUD、自定义SQL路由、认证和MCP端点。

🔗 https://github.com/prest/prest

**🆕 新锐发现**（近14天新建，早期项目）


---

**1. yiaany/Mekka** [新锐]  ⭐4 · TypeScript · 更新 1天前
> Mekka 是一个基于 Bun 和 SQLite 的一键启动本地后端基础设施，提供数据、认证、存储、实时和内置 Studio 功能。

🔗 https://github.com/yiaany/Mekka

**🎯 本周重点解读**

**OtterMind/Chat2DB**

**本周重点解读：Chat2DB（Star 27,902，周增285）**

**① 解决什么问题**  
为开发者、DBA、分析师提供跨平台（Win/macOS/Linux）的AI数据库客户端，整合SQL工作台与自带模型的AI助手，解决多数据库管理、SQL编写优化及数据可视化需求。

**② 核心亮点**  
- 支持40+数据库（MySQL、PostgreSQL、Oracle等），新JDBC库可零代码配置扩展  
- 内置SQL编辑、补全、格式化及执行历史，支持数据导入导出、仪表盘与ER图  
- AI助手可接入自有模型，实现自然语言生成/解释/优化SQL  
- 提供开源CLI并支持MCP协议

**③ 适用场景/注意事项**  
适用于本地数据库日常管理及AI辅助开发。桌面版需从GitHub Releases下载安装；Docker部署要求19.03.0+版本。AI功能需自行配置模型，数据完全本地运行。

⭐ 27.9k 📈 +285/周 ｜ Java ｜ 更新 0天前

---
💬 互动：本周你最关注哪个项目？欢迎留言。

<sub>由 ai_db_weekly 自动采集于 2026-08-10，候选池 20 个项目。介绍基于各项目 README 由 AI 生成。</sub>
<!-- LATEST:END -->

---

## 往期周报

<!-- ARCHIVE:START -->
| 期数 | 日期 | 链接 |
|------|------|------|
| 第 4 期 | 2026-08-10 | [output/2026-08-10.md](output/2026-08-10.md) |
| 第 3 期 | 2026-08-03 | [output/2026-08-03.md](output/2026-08-03.md) |
| 第 2 期 | 2026-08-02 | [output/2026-08-02.md](output/2026-08-02.md) |
| 第 1 期 | 2026-08-01 | [output/2026-08-01.md](output/2026-08-01.md) |
<!-- ARCHIVE:END -->
