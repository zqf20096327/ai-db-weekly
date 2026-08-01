# AI×DB 周报

聚焦「AI 与数据库结合」的开源项目周报。每天自动采集 GitHub 数据，
按**周 star 增量**排序，输出一份 Markdown，直接复制贴公众号。

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

- **榜单条数**：搜 `section_hot_by_delta`（Top10）、`section_emerging`（Top5）
- **采集范围**：编辑 `build_queries()` 增删方向
- **star 门槛**：查询里的 `stars:>N`
- **质量过滤**：`DESC_BLACKLIST`（关键词）和 `KNOWN_OFFTOPIC`（精确项目）

## 文件结构

```
20260729/
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

## 公众号发布

1. **链接问题**：公众号正文不能点外链，建议每条加「搜索 `owner/repo`」
2. **Markdown 转公众号**：用 [mdnice](https://mdnice.com) 美化后粘贴
3. **期数自动递增**：脚本读 `output/` 目录历史文件数 +1
