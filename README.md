# 数据库开源生态周报（ai-db-weekly）

自动化跟踪 GitHub 开源数据库生态的周报流水线：每日采集候选池 → 富集信号 → 人群/任务分类 → 每周生成三板块周报（Markdown + 公众号版）。

> 📌 数据源：GitHub。聚焦开源工具与实验项目，不涉及厂商内核信息。生产可用性请自行评估。

## 仓库结构

| 路径 | 说明 |
|---|---|
| [`v2/`](./v2/README_v2.md) | 现行流水线全部代码与文档（入口文档） |
| `v2/数据库开源周报-SOP.md` | 规范文档：范围闸门、数据源、栏目定义 |
| `v2/采集策略清单.md` | 采集策略落地清单 |
| `v2/reports/` | 各期周报产物（`report_snapshot_*.md` / `wechat_snapshot_*.html`） |
| `v2/data/` | 永久数据湖：每日快照 zip 归档 + 近 8 天明文（供周报 7 天 diff） |
| `.github/workflows/` | CI：`v2-daily.yml` 每日采集+富集，`v2-weekly.yml` 周报生成 |

## 流水线一览（均在 `v2/` 下）

1. **每日采集** `run_daily.py` —— topic 搜索 + 白名单补采 + org 扫描 + 新生项目池 + commit 活跃度，去重合并为候选池
2. **每日富集** `run_enrich.py` —— releases 维护信号 + GHSA 安全通告（断点续采，周节奏刷新）
3. **人群分类** `run_personas.py` —— AI 把工具分为用库 / 管库 / 造库 + AI 叠加标，增量缓存
4. **任务分类** `run_categories.py` —— 三层分类的第③层 AI 兜底（topics/关键词判「其他」的兜底分类）
5. **周报生产** `run_weekly.py` —— 7 天 diff → 信号分/价值评分 → 三板块榜单 → Markdown + 公众号 HTML

详细用法、断点续采、配额说明见 [`v2/README_v2.md`](./v2/README_v2.md)。
