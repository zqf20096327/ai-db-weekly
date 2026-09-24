# site_export · 站点数据聚合模块

每个模块是一个独立脚本，**只读 `data/` 下的采集数据**（目录或 zip 归档），
输出站点 JSON 到 `BLOG_SITE_DIR`（默认 `D:\db-oss-observer\blog-site\data\site`，
可用环境变量覆盖）。公共层 `site_common.py`：路径 / 快照读取 / 管道口径复用 /
历史库原子 IO / 分层门槛。

## 模块一览

| 脚本 | 频率 | 作用 | 耗时 |
|---|---|---|---|
| `backfill_history.py` | 一次性/灾备 | 从全部观察日（含 zip）重建 `history.json` | ~80 秒 |
| `aggregate_daily.py` | 每天 | 增量更新 history → `now.json` + `map.json` + `archive-{db}.json`×N | ~5 秒 |
| `export_weekly.py --date D` | 每周四 | `run_weekly` 定榜结果 → `weekly-{N}.json` + `issues-index.json` | ~2 秒 |
| `aggregate_monthly.py` | 每月 1 日 | history 锚点 + org 首末日 → `monthly-{YYYY-MM}.json` | ~2 秒 |
| `validate_site.py` | 部署前 | 全部站点 JSON 的 schema/日期/期号校验，失败退出码 1 | <1 秒 |

## 日常操作

```bash
# 每天（采集完成后）
python run_daily.py                          # 已有
python site_export/aggregate_daily.py        # 秒级

# 每周四出刊
python run_weekly.py --date YYYYMMDD         # 已有（compute→readme→select→ai→render）
python site_export/export_weekly.py --date YYYYMMDD
#   → 人工改 weekly-{N}.json 里 hooks 的文案（draft:true→false），复核榜单
python site_export/validate_site.py && bash tools/deploy.sh   # blog 仓库

# 每月 1 日
python site_export/aggregate_monthly.py

# 灾备重建（history 损坏 / 换机器）
python site_export/backfill_history.py
python site_export/aggregate_daily.py
python site_export/export_weekly.py --date <最近出刊日>
python site_export/aggregate_monthly.py
```

## 已定的口径（改动需同步前端）

- **watched 边界**：范围内 且 star≥10 ∪ 历史上榜 ∪ 历史解读对象；
- **展示默认档**（tier，纯渲染选项）：国际/AI ≥300，国产板块 ≥50；数据层不做取舍；
- **国产判定**：只用 `sections.assign_section`（token 防误命中），禁止关键词子串；
- **周锚点**：每周（ISO 周）最后一个观察日；缺照自动跳过（趋势口径已在页面声明）；
- **月窗**：滚动 26-38 天取最近基准日；单项目取值就近回退（缺照日）；
  org 基准回退到最近一个有 orgs 的观察日；
- **新面孔门槛**：star≥50 或官方组织出品（orgs 清单内 owner）；
- **文件名 slug**：`SQL Server → SQL-Server`（前端按 `db_slug` 同规则请求）。
- **任务分类（2026-09-22 定案：8+1 类）**：`备份/监控/高可用/迁移/连接代理/管理/平台/开发库 + 其他`。
  三层生成：① topics 精确集合（作者自标）→ ② 关键词词形匹配（含 management/migration 等变体）
  → ③ AI 缓存兜底（`categories.json`，v2/run_categories.py 护栏版产出：禁既有认知、
  高/中置信才采纳、增量续跑）。第 8 类「开发库」=驱动/ORM/SDK/查询构建/SQL 解析转译
  （试验证据：唯一项目 201 项、精选层 11%；SQL工具 44 项并入）。
- **范围闸门堵漏（同日）**：AliSQL→内核清单（MySQL 分支）；manticore/seekdb→范围外；
  DevOps-Bash-tools→人工排除。分类试验 `cat_trial/` 留档。

## 输出契约（前端 M2 按此消费）

- `now.json`：updated / snapshot_days / pool_total / pool_scoped / watched / map_total / db_count / tier_default_total
- `map.json`：date / total / tier_rule / cat_order / db_order / matrix{db×cat} / other{db} / dbs{统计}
- `archive-{slug}.json`：db / slug / date / total / stats / groups{任务→[记录]}（全量 ≥10，记录含 tier）
- `weekly-{N}.json`：issue_no / date / window / pool_* / with_growth / new_pool / hooks[]（draft 标）/ board_secs{三板块→[记录+review]} / focus{+three+focus_note} / newfaces[] / topboard[5] / rotated_out[]
- `monthly-{YYYY-MM}.json`：month / window / top_gain[10] / streaks[] / month_new_count / month_new_top / orgs[]
- `issues-index.json`：entries[{type, issue_no, date, status(draft/published), summary, counts}]

记录字段（record）：fn / url / desc / stars / growth / section / cat / dbs / license / lang / commit7 / pushed / archived / persona / ai / weeks_in_pool / growth_streak / spark[] / tier

**M5 富集字段（2026-09-22 起，采集侧 `v2/run_enrich.py` + `run_personas.py` 周节奏供给，
采集未覆盖的项目缺省不出现，前端按缺失静默处理）**：
- record 增加：ver（最新版本 tag）/ verd（距发布天数）/ n90（近 90 天发版次数）/
  secn（GHSA 自主披露条数，0=已扫描且无披露）/ secw（最高 severity）/ secl（最近披露日）
- `now.json` 增加：enrich{release_date, release_covered, security_date, security_covered, personas_ai}
- persona 在 AI 缓存（`personas.json`）命中时覆盖规则版结果；
- GHSA 口径：仅项目**自身披露**（依赖漏洞为私有数据不采）；API 修复版本字段不可靠，
  不产出「未修复」断言，前端以「披露 N 条 · 最高 X」如实施示。

## 输入（快照 meta，富集采集器写入）

- `snapshot_*/meta/release_state.json`：{date, count, by_repo{fn→{ver,pub,days,n90,pre}|{none}}}
- `snapshot_*/meta/security.json`：{date, count, by_repo{fn→{n,worst,last,ids[]}}}
- `personas.json`（本目录）：{fn→{p,ai,why,when}}（AI 分类缓存，增量累积）

## 防呆与安全

- 快照目录名必须 `^snapshot_\d{8}$`（曾因参数带前缀生成 `snapshot_snapshot_*` 垃圾目录）；
- history.json 原子写入 + 7 份轮转备份，损坏自动从备份恢复；
- 全部输出先写 `.tmp` 再 `os.replace`，部署中间不会出现半截文件；
- `validate_site.py` 是部署闸门：任何 schema/日期/期号问题 → 退出码 1 → deploy.sh 阻断。

## 模块 6：独立深度校验（verify_independent.py）

`validate_site.py` 查 schema；`verify_independent.py` 查**数值正确性**——绕过 site_common
从原始快照重算再对账（147 项断言）。发布重要版本前跑一次，日常部署跑 validate 即可：

```bash
python site_export/verify_independent.py
```

本模块在首次深度校验中抓出并已修复的问题（留档防回归）：
1. `snapshot_dates` 正则漏 `.zip` 后缀 → 12 个 zip-only 观察日未进历史库；
2. 无池日（08-26 / 09-07 无 merged）被当锚点 → 改为只计有效池日，无池日记 `meta.dates_no_pool`；
3. archive 记录缺 `persona`/`spark`（契约违约）；
4. 地图/档案 growth 误用日环比 → 改为「距 7 天最近」的周环比口径；
5. map.json 缺 db_slug 映射（前端无法从库名定位档案文件）。
