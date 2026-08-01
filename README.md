# AI×DB 周报

聚焦「AI 与数据库结合」的开源项目周报。每天自动采集 GitHub 数据，
按**周 star 增量**排序，输出一份 Markdown，直接复制贴公众号。

> 📖 **本期周报**：[第 1 期 · 2026-08-01](output/2026-08-01.md)
> 📚 **历史周报**：见文末[「往期周报」](#往期周报)

---

## 📋 本期周报 · 第 1 期（2026-08-01）

**📌 今日聚焦**

🔥 最受关注：**Chat2DB**（⭐27.6k）
🎯 重点解读：**OtterMind/Chat2DB**

### 🔥 本周热门 Top10

| # | 项目 | ⭐ | 语言 | 简介 |
|---|------|-----|------|------|
| 1 | [OtterMind/Chat2DB](https://github.com/OtterMind/Chat2DB) | 27.6k | Java | 免费跨平台 AI 数据库客户端，连接 30+ 数据库，集成 AI 助手生成/解释/优化 SQL |
| 2 | [googleapis/mcp-toolbox](https://github.com/googleapis/mcp-toolbox) | 16.1k | Go | 开源 MCP 服务器，将 AI 代理连接到企业数据库，支持 NL2SQL 等工具 |
| 3 | [t8y2/dbx](https://github.com/t8y2/dbx) | 12.9k | Rust | 20MB 桌面客户端，支持 70+ 数据库，内置 AI 助手与 MCP Server |
| 4 | [prest/prest](https://github.com/prest/prest) | 4.6k | Go | 在 PostgreSQL 上即时生成 REST 和 MCP API，无需手写后端 |
| 5 | [bytebase/dbhub](https://github.com/bytebase/dbhub) | 3.3k | TypeScript | 零依赖 MCP 服务器，统一连接 PG/MySQL/SQLServer/SQLite |
| 6 | [mayneyao/eidos](https://github.com/mayneyao/eidos) | 3.2k | TypeScript | SQLite 个人数据框架，离线 Notion 风格 + LLM 集成 |
| 7 | [dosco/graphjin](https://github.com/dosco/graphjin) | 3.1k | Go | GraphQL + MCP 数据访问层，为 AI 代理提供治理与审计 |
| 8 | [matrixorigin/matrixone](https://github.com/matrixorigin/matrixone) | 1.9k | Go | MySQL 兼容的 AI 原生云数据库，引入 Git 式版本控制 |
| 9 | [julien040/anyquery](https://github.com/julien040/anyquery) | 1.7k | Go | SQLite 上的 SQL 引擎，查询文件/App/数据库，支持 LLM |
| 10 | [designcomputer/mysql_mcp_server](https://github.com/designcomputer/mysql_mcp_server) | 1.3k | Python | MySQL 的 MCP 服务组件，安全交互与 SQL 执行 |

> 💡 数据积累中：需连续运行 7 天后展示真实「周 star 增量」，本期暂按 star 绝对值排序。

### 🎯 本周重点解读 · OtterMind/Chat2DB

**① 解决什么问题**：为开发者、DBA、分析师提供跨平台 AI 数据库客户端，将 SQL 工作台与 AI 助手结合，支持 30+ 数据库类型，解决多数据库管理及 SQL 编写优化效率问题。

**② 核心亮点**：完全本地运行（Windows/macOS/Linux）；完整 SQL 编辑、补全、格式化及执行历史；可接入自有 AI 模型生成/解释/优化 SQL；支持数据导入导出、仪表盘图表、ER 图；附带支持 MCP 的开源 CLI。

**③ 适用场景/注意事项**：适合需统一管理多数据库的团队或个人。桌面版从 GitHub Releases 下载；Docker 部署需 2 核 CPU + 4GB 内存，首次需配置加密密钥。

📖 **完整本期内容**：[output/2026-08-01.md](output/2026-08-01.md)

---

## 关于本项目

## 定位

不做关系型数据库引擎榜单（太稳定，不适合周报），也不做独立向量数据库。
**只关注 AI 如何操作、理解、查询数据库的工具和项目。**

## 采集范围：5 大方向

| 方向 | 查询 | 覆盖 |
|------|------|------|
| Agent / Skill | `db-agent OR sql-agent OR db-skill ... in:name` | AI 智能体操作数据库 |
| MCP 服务 | `db-mcp OR sql-mcp ... in:name` | 数据库 MCP server |
| Text2SQL | `text2sql OR nl2sql ... in:name` | 自然语言转 SQL |
| 自然语言查询 | `natural-language-sql ... in:name` | 对话式查数据库 |
| ChatDB | `chatdb OR chat2db ... in:name` | AI 数据库工具 |

**明确排除**：向量扩展、独立向量库、关系型库引擎、RAG 框架、通用 AI agent 框架、游戏/调试器 MCP 等噪音。

约 76 个候选项目，详见 `db_trending.py` 的 `build_queries()`。

## 榜单结构

```
📋 AI×DB 周报 · 第 N 期

📌 今日聚焦          ← 增量最高的项目
---
🔥 本周热门 Top10    ← 按周 star 增量排序（核心）
🆕 新锐发现 Top5     ← star<100 但活跃
🎯 本周重点解读(1个) ← 带AI三段式深度分析
---
💬 互动
```

## 快速开始

### 1. 配置 .env

```
GITHUB_TOKEN=ghp_xxx          # 必填，申请：github.com/settings/tokens/new（不勾权限）
AI_API_KEY=xxx                # 选填，用于中文介绍（智谱GLM/DeepSeek等）
AI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
AI_MODEL=glm-4-flash
```

### 2. 每天运行

```bash
python db_trending.py
```

- 产出 `output/YYYY-MM-DD.md`（复制贴公众号）
- 产出 `output/YYYY-MM-DD.json`（原始数据备份）
- 自动存 `cache/snapshot_YYYY-MM-DD.json`（算周增量用，别删）

### 3. 每日工作流（约 5 分钟）

```
python db_trending.py              # 1分钟：采集+生成
打开 output/今天.md                # 3分钟：填 __点评__
粘进 mdnice.com 美化 → 发公众号    # 1分钟
```

## 重要：周增量需要历史快照

「本周热门 Top10」的核心是**周 star 增量**。这依赖历史快照：
- **前 7 天**：无历史，按 star 绝对值排序（兜底），栏头会提示「数据积累中」
- **第 8 天起**：自动展示真实的周增量

**请每天坚持跑一次**，7 天后才有增量数据。快照存在 `cache/` 目录。

## 配置项

所有可调参数集中在 `db_trending.py` 顶部的 **CONFIG 区**（约第 25–101 行），改这里就够了：

- **采集范围**：`SEARCH_KEYWORD` / `SEARCH_MODE`（搜索关键词和方式）
- **star 门槛**：`MAIN_STARS_MIN`（主轨）、`EMERGING_STARS_MIN`（副轨）
- **榜单条数**：`HOT_TOP_N`（热门榜，默认 10）、`EMERGING_TOP_N`（新锐榜，默认 5）
- **关键词词表**：`DB_KEYWORDS`（数据库名信号词）、`AI_KEYWORDS`（AI 信号词）
- **README 精筛门槛**：`README_AI_MIN_HITS`（默认 ≥3 次命中）
- **质量过滤**：`DESC_BLACKLIST`（关键词黑名单）、`KNOWN_OFFTOPIC`（精确项目黑名单）

## 文件结构

```
ai-db-weekly/
  db_trending.py            # 主脚本（零依赖，仅 Python 标准库）
  .env                      # 配置（token + AI key）
  README.md
  cache/
    snapshot_YYYY-MM-DD.json  # 每天快照（算增量用，别删）
    ai_desc_YYYY-MM-DD.json   # AI 介绍缓存（省钱）
  output/
    YYYY-MM-DD.md             # 每日成品 → 贴公众号
    YYYY-MM-DD.json           # 原始数据备份
```

## GitHub Actions 自动化（推荐）

配好后每天北京时间 08:00 自动采集，快照和成品自动提交回仓库，**无需本地运行**。
工作流配置见 `.github/workflows/daily.yml`。

### 配置 Secrets

仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**：

| Secret 名 | 必填 | 值 | 说明 |
|-----------|------|-----|------|
| `AI_API_KEY` | 选填 | 你的智谱 key | 用于生成中文介绍。不配则用英文描述 |
| `AI_BASE_URL` | 选填 | `https://open.bigmodel.cn/api/paas/v4` | AI 服务地址 |
| `AI_MODEL` | 选填 | `glm-4-flash` | 模型名 |
| `FEISHU_WEBHOOK` | 选填 | 飞书机器人 webhook | 配后自动推送周报到飞书群 |

> `GITHUB_TOKEN` **不需要手动配**——Actions 自动注入，且已在 workflow 里声明了 `contents: write` 权限用于提交快照。

### 手动验证一次

仓库 → **Actions → AI×DB 周报采集 → Run workflow**，等 5 分钟看是否绿勾。
绿勾 = 采集成功 + 快照已自动提交回仓库（会看到一个 `auto: YYYY-MM-DD 采集` 的 commit）。

### 自动化行为说明

- **定时**：每天 UTC 00:00（北京 08:00）跑一次
- **快照持久化**：`cache/snapshot_YYYY-MM-DD.json` 每天自动 commit 回仓库，**这就是周增量的数据来源**，连续跑满 7 天后才会有真实增量
- **失败排查**：Actions 报红时点进去看日志，常见原因——AI key 过期（429 限流）、GitHub 搜索 API 限流（每小时 30 次，正常够用）

---

## 公众号发布

1. **链接问题**：公众号正文不能点外链，建议每条加「搜索 `owner/repo`」
2. **Markdown 转公众号**：用 [mdnice](https://mdnice.com) 美化后粘贴
3. **期数自动递增**：脚本读 `output/` 目录历史文件数 +1

---

## 往期周报

| 期数 | 日期 | 链接 |
|------|------|------|
| 第 1 期 | 2026-08-01 | [output/2026-08-01.md](output/2026-08-01.md) |
