# 数据库开源周报 · 每日采集「地基」(v2)

> 本目录是《数据库开源周报》SOP 第四章采集架构的工程实现 —— **每日采集地基**。
> 规范文档：[`数据库开源周报-SOP.md`](./数据库开源周报-SOP.md)、[`采集策略清单.md`](./采集策略清单.md)
> 与旧脚本 `../db_trending.py` **完全隔离**，不接管其 CI（`../.github/workflows/daily.yml`），新旧并存。

---

## 它做什么

按 SOP 4.3「每日凌晨」跑完全部 4 个数据源，产出**去重合并后的候选池**（周报一切榜单的地基）：

| 数据源 | 模块 | 产出 |
|---|---|---|
| 1️⃣ 项目全量快照 | `collectors/topic.py` | `topics/{topic}.json` |
| 1️⃣ 白名单补采（topics 为空的内核） | `collectors/whitelist.py` | `whitelist/whitelist.json` |
| 6️⃣ Org 全量扫描（补盲区） | `collectors/org_scan.py` | `orgs/{org}.json` |
| 2️⃣ 新生项目池（30 天窗） | `collectors/new_projects.py` | `new_projects/{topic}.json` |
| 4️⃣ Commit 活跃度（候选池合并后） | `collectors/commit_activity.py` | `meta/commit_activity.json` |
| — 去重合并 | `storage.merge_dedupe` | `merged/all_projects.json` |

**不在本次范围**（后续模块）：数据源 3（release）、5（license 变更）、AI 翻译、10 栏目榜单、周报 Markdown。

> 📌 **周报生产层已上线**（见下方[「周报生产 run_weekly.py」](#周报生产-run_weeklypy)）：release/license 采集 + 7天diff + 信号分/价值评分/榜单归属 + 10 栏目 Markdown 渲染。AI 部分留接口占位，下一轮接 deepseek。

---

## 快速开始

```bash
cd D:/daily_github/v2

# 0. 配置 token（.env 已存在；或设环境变量 GITHUB_TOKEN）
#    GITHUB_TOKEN=ghp_xxx  （classic token，无需 scope，提限流到 Search 30/分）

# 1. 全流程（约 7-10 分钟，~194 次 Search + ~22 次 Core 调用）
python run_daily.py

# 2. 单阶段调试（推荐先这样验证）
python run_daily.py --only probe              # 探测 16 topic 规模
python run_daily.py --only topic --topics tidb,oceanbase
python run_daily.py --only whitelist
python run_daily.py --only org
python run_daily.py --only new
python run_daily.py --only merge              # 只合并（不采新数据）
python run_daily.py --only commit             # 只跑 commit 活跃度

# 3. 强制重采（忽略断点续采）
python run_daily.py --only topic --no-resume

# 4. DEBUG 日志
python run_daily.py -v
```

**断点续采**：每个阶段读已落盘结果，跑过的 topic/org 自动跳过。中途 Ctrl+C 不丢数据，重跑即可续上。

---

## 目录结构

```
v2/
├── config.py              # ⭐ 配置中心（改这里，不改代码）
├── github_client.py       # GitHub 客户端（限流/重试/分页）
├── storage.py             # 存储层（落盘/去重/标准化）
├── filters.py             # 四层漏斗（纯函数，可单测）
├── collectors/
│   ├── probe.py           # 第1步 探测
│   ├── topic.py           # 第2-3步 巨型三层拆分 + 小型全采
│   ├── whitelist.py       # 第4步 白名单（Core API）
│   ├── org_scan.py        # 第4.5步 org 扫描（Core API）
│   ├── new_projects.py    # 第5步 30 天窗
│   └── commit_activity.py # 数据源4 commit 活跃度
├── run_daily.py           # 编排入口（每日采集）
├── run_weekly.py          # 编排入口（周报生产，见下文）
├── analytics.py           # 对比/评分/信号分/榜单归属（纯函数）
├── render.py              # 10 栏目 Markdown 渲染（纯函数）
├── templates.py           # 栏目文案/Emoji/口径/禁用词常量
├── ai_client.py           # AI 调用层（本轮占位，下轮接 deepseek）
└── data/                  # 运行时生成（gitignore）
    └── snapshot_YYYYMMDD/
        ├── meta/{probe_results,commit_activity,run_summary}.json
        ├── topics/{topic}.json
        ├── whitelist/whitelist.json
        ├── orgs/{org}.json
        ├── new_projects/{topic}.json
        └── merged/all_projects.json     ← 候选池（周报地基）
```

---

## ⭐ 后期维护指南（核心）

> **设计原则：加东西改 `config.py`，修逻辑改对应模块。绝大多数日常调整不需要动业务代码。**

### 加一个 topic
`config.py` 的 `TOPICS` 列表加一行即可，采集/新生/探测全自动：
```python
TOPICS = [..., "你的新topic"]
```

### 加一个白名单内核 repo
`config.py` 的 `WHITELIST_REPOS`：
```python
WHITELIST_REPOS = [..., "owner/repo"]   # ⚠️ 先确认是官方源而非镜像/撞名
```

### 加一个 org 扫描
`config.py` 的 `ORG_SCAN_LIST`：
```python
ORG_SCAN_LIST = [..., "新org"]
```

### 调整采集阈值
`config.py`：
- `STAR_MIN_SNAPSHOT = 10` —— 快照全量下限（调高更省调用、调低更全）
- `STAR_MIN_NEW = 3` / `NEW_PROJECT_DAYS = 30` —— 新生项目口径
- `COMMIT_ACTIVITY_THRESHOLD = 10` —— 🔥 活跃标签阈值（SOP 说初值待校准）
- `COMMIT_ACTIVITY_MAX_REPOS = 2000` —— commit 采集的成本上限

> ⚠️ **commit 活跃度成本提示**：数据源4 对候选池**每个 repo** 调一次
> `/stats/participation`（Core API）。候选池经实测约 1300-1500 项目，
> 即 1300-1500 次 Core 调用（≈2 秒/次 → 全量约 **40-50 分钟**）。
> Core API 配额 5000/小时够用，但耗时较长。需要快速验证时，
> 临时改小 `COMMIT_ACTIVITY_MAX_REPOS`（如 50）只跑 star 头部。
> SOP 4.3 原意"对候选池项目采"，如后续发现只关心头部项目的🔥标签，
> 可把上限调到 500-800（覆盖总榜候选）大幅省时。

### 加黑名单关键词
`config.py` 的 `BLACKLIST_KEYWORDS`。**注意匹配规则**（见 `filters.is_blacklisted`）：
- `docs` / `site` / `mirror` / `-cn` 等 → **仅匹配 repo 名**（不碰 description，避免误杀"see docs"）
- `教程` / `tutorial` / `homework` 等 → 匹配 name + description
- 全部按**完整 token** 匹配（边界为非字母数字），不做子串匹配

### 改限流策略
`github_client.py` 的 `_wait_for_rate_limit` / `config.RATE_LIMIT`。
**千万别改回固定 `sleep(61)`**（SOP 4.5 ④ 明确：那是 ×61 倍耗时的反模式）。

### 加新的采集步骤（如未来的 release/license）
1. `collectors/` 下新建模块，接收 `GitHubClient`，调 `storage.save_*` 落盘
2. `run_daily.py` 的 `run_pipeline` 加一个 `if only in (None, "新阶段"):` 分支
3. 现有模块无需改动

---

## 关键设计决策（与 SOP 对照）

| 决策 | 依据 |
|---|---|
| 单一模块化包，不做 16 个脚本 | SOP 4.5 字面写"16 脚本"，但 16 个雷同脚本是维护噩梦；配置驱动更易维护 |
| 互斥仅限四大库（database/mysql/postgresql/oracle） | SOP 4.9.1：国产库打上游标签会被互斥误杀 |
| 互斥用减号 `-topic:xxx`，不用 `NOT` | GitHub 不支持 SQL NOT 语法（返回 422） |
| 数据源 4 排在候选池合并之后 | SOP 4.3"对候选池项目采"——依赖 merged/all_projects.json |
| participation 轮询处理 202 | SOP 4.2 数据源4 警告：首次常返回 202（异步计算中） |
| 黑名单 token 匹配 + name-only 分层 | 实测：子串匹配会误杀 `oGRAC-docs`；name-only 误杀 `opengauss-mirror/*` |
| 快照日期用 `YYYYMMDD` | SOP 4.6 存储结构；与旧脚本 `YYYY-MM-DD` 不向后兼容（新地基独立） |

---

## 验证状态（2026-08-05 实跑）

- ✅ probe：16 topic 量级与 SOP 实测表 16/16 吻合
- ✅ topic：oracle 互斥+三层拆分 327 项目（star≥10 不变量成立）
- ✅ whitelist：12/12 内核 repo（TiDB 40.4k / DuckDB 40.0k / Postgres 21.7k 与 SOP 一致）
- ✅ org：7 org 共 386 repo（opengauss-mirror 修复后 113）
- ✅ new：30 天窗 + 内容相关性过滤
- ✅ commit：oceanbase 41 候选 → 3 活跃(🔥)，participation 主路径生效
- ✅ merge：743 候选池，full_name 全唯一，白名单优先级正确

---

---

## 周报生产 run_weekly.py

> 对标 `run_daily.py`（每日采集）的独立编排，跑通 SOP 第十章「每周生产流程」。
> 流水线：采集（数据源3/5）→ 计算（7天diff/评分/归属）→ 渲染（10栏目 Markdown）。

### 它做什么

| 阶段 | 模块 | 产出（data/snapshot_*/weekly/） |
|---|---|---|
| 数据源3 Release 采集 | `collectors/releases.py` | `meta/releases.json` |
| 数据源5 License 变更检测 | `collectors/license_changes.py` | `meta/license_changes.json` |
| 7天快照 diff / 价值评分 / 信号分 / 榜单归属 | `analytics.py` | `meta/{diff,scoring,attribution}.json` |
| 10 栏目 Markdown 渲染 | `render.py` + `templates.py` + `ai_client.py` | `report.md` |

### 快速开始

```bash
cd D:/daily_github/v2

# 前置：当日候选池必须已由 run_daily.py 产出
python run_daily.py            # 每日采集（地基）

# 周报生产（全流程，含 release/license 采集）
python run_weekly.py

# 单阶段调试
python run_weekly.py --only releases           # 只采本周 release
python run_weekly.py --only license            # 只检本周 license 变更
python run_weekly.py --only compute            # 只算（diff/评分/归属，纯本地不调API）
python run_weekly.py --only render             # 只渲染（需已有 compute 结果）

# 快速验证（限制 release/license 采集只跑头部 30 个 repo，约 3 分钟）
python run_weekly.py --acquire-cap 30

# 指定快照日期 / 对比基准
python run_weekly.py --date 20260806 --prev-date 20260531

# 强制重算
python run_weekly.py --no-resume
```

### 核心概念

- **7 天对比基准自动定位**：`storage.find_prev_snapshot_date` 自动找"距 7 天前最近的已有快照"做 diff。无更早快照（首期）→ 动态栏目（①⑤）自动标注"首期无基准"，非动态栏目（②⑥⑦⑧⑨⑩）仍完整呈现。
- **榜单归属分层漏斗**（SOP 6.y）：每个项目按 ④重点→②新生→①上涨→⑧AI→⑤总榜 五选一归入唯一主榜，被舍弃的榜标"见XX榜"，防霸屏。
- **首期即可出完整周报**：②新生按 `created_at` 直接筛（不依赖 diff），⑤总榜按当前 star 排序，⑥⑦⑧⑨ 在 release/license 采集后即完整。

### 后期维护（核心）

> **延续采集层原则：改 config/templates 不动业务代码。**

| 想调整 | 改哪里 |
|---|---|
| 信号分权重 / 影响面系数 / 重点数量 | `config.py` → `SIGNAL_WEIGHTS` / `SIGNAL_STAR_MULTIPLIER` / `FOCUS_MAX_ITEMS` |
| 价值评分维度 | `config.py`（评分逻辑在 `analytics.value_score`） |
| 上涨榜排除前 N / 展示条数 | `config.py` → `RISING_EXCLUDE_TOPN` / `RISING_TOPN` |
| 总榜/新生榜条数 | `config.py` → `TOPBOARD_LIMIT` / `NEW_LIST_LIMIT` |
| 栏目文案 / Emoji / 口径说明 / 禁用词 | `templates.py` |
| 榜单归属优先级 | `analytics.assign_main_section`（一个函数集中） |
| 加新栏目 | `render.py` 加一个 `render_XXX` 函数 |
| Release/License 采集范围 | `config.py` → `RELEASE_MAX_REPOS` / `LICENSE_MAX_REPOS` |

### AI 增强（下一轮）

`ai_client.py` 本轮为**占位实现**：`summarize_release_notes` / `translate_readme_role` / `focus_four_questions` 返回字段原文/模板，不调真实 API。周报标注"本期为骨架版"。
下一轮接 deepseek：**只改 `ai_client.py` 内部**（`__init__` 读 `.env` key + 三方法改真实 chat completion），`render.py` / `templates.py` 零改动。

---

## 依赖

仅 `requests`（Python 3.x）。无其他第三方依赖。
