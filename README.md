# 数据库开源生态观测（周刊形态）

**在线站点**：<https://zqf20096327.github.io/ai-db-weekly/>

数据库开源生态观测站（周刊 + 工具）—— 基于 [dbhub_collect](https://github.com/zqf20096327/dbhub_collect)
采集数据构建的纯静态站点，为部署到 GitHub Pages 而设计。

## 产品结构：编辑层制造访问理由，数据层承接访问意图

| 页面 | 角色 | 内容 |
|---|---|---|
| `index.html` 周刊 | **读**（每周一个访问高峰） | 组织原则：**只报变化（事件），状态查工具页**。导读（编辑观点+数字注入）→ 3 篇深读 → 本周速览 4 卡：🔴风险预警（近7天**新披露**高危通告 + 停维/归档预警）/ 📦版本动态（近7天发版·内核优先）/ 📈增星榜 / 🌱新项目 → 💬一句话情报（自动候选）→ 本期数字 → 工具入口 |
| `mystack.html` 我的关注 | **盯**（留存的发动机） | 勾选我在用的数据库 + ☆ 关注工具 → 收件箱式事件流（安全>停维>发版>增星）、我的库本期新工具、关注列表管理。全 localStorage，无账户；**🔗 分享链接**（`#stack=` 编码，跨设备迁移/分享选型）与 **⬇ 导出 / ⬆ 导入** JSON 备份 |
| `projects.html` 项目浏览 | **查** | 一套筛选 · 两种看法：▦ 矩阵看格局（库 × 类别 · 每格冠军=本土优先、⊙=缺口信号）/ ☰ 清单查项目（全量 · 可搜可排）。筛选五行平铺（数据库/类别/属性五组/语言/视图）+ GitHub 式全局搜索（建议面板 / `/` 聚焦 / Enter=全局新查询）；同一结果集切换视图零丢失 |
| `compare.html` 项目对比 | **选** | 选 2-4 个同类项目：信号并排表（17 个维度，首列粘性）+ **AI 对比解读**（构建期离线生成：定位差异/数据信号/风险观察 + 按场景推荐）。对比篮从项目抽屉「⇄ 加入对比」，或页内同类推荐；内置两组样例（PG 备份双雄 / 客户端三国杀） |

## 设计规范（维护约束）

- **字体三角色制**：拉丁与数字使用自托管 **Inter**（`assets/fonts/InterVariable.woff2`，OFL 许可，woff2 可变字重 352KB），中文回退系统栈（PingFang/微软雅黑）；等宽 `--mono` **只用于字面量**——项目名（`.repo`）、版本号、GHSA/CVE、`<code>`、矩阵格徽章。数字对齐靠全局 `tabular-nums`，不要给纯数字加 `.mono`。
- **字重只许 4 档**：400 / 600 / 700 / 800。
- **色彩语义**：红=风险、蓝=品牌/版本、绿=增长、青=新项目、琥珀=国产板块/中危。速览四卡左边条按此映射。
- **导读为固定模板**：亮点/风险/规模三行结构，数字与项目名自动注入，每行 ≤45 字避免折行。
- **首页纵向顺序**：期号 → 标题+右侧主 CTA（我的关注）→ 副标语 → 本期数字条 → 导读 → 一句话情报 → 深读 → 速览 → 工具行（行动入口与规模背书前置，编辑内容居后）。

## 查看方式

```bash
python -m http.server 8123     # 或直接双击 index.html（file:// 可用）
```

## 交互约定

- 点击筛选，状态实时写入地址栏 hash（`#db=PostgreSQL&cat=备份&sort=gro`），可分享可收藏；
- 跨页跳转：首页卡片/统计格/深读卡 → 预筛选的项目浏览器；矩阵行头列头同理；
- 详情抽屉：维护状态横幅、提交/发版/安全/贡献者、许可证、官网、README 摘录、分类依据；
- 行内徽章：`已归档` / `疑似停维` / `新`；暗色主题 🌗；加载进度条。

## AI 对比解读的生产方式

GitHub Pages 是纯静态站，**AI 只在构建期离线运行**，产物固化进 `data/comparisons.js`（无运行时调用、无数据上传）：

```bash
# 预览会生成哪些组合与提示词（不花钱）
python build/ai_compare.py --dry-run

# 实际生成（需智谱 API Key，组合清单见 data/compare_pairs.json，也可自动推荐）
DBHUB_AI_KEY=xxx python build/ai_compare.py --max 10
```

增量生成（已有组合不重复调用）；样例中两组解读即该管线的产物示例。

## 深读的选稿与生产方式（第 1 期样刊已内置）

选稿由数据信号驱动，"为什么是它"用数字回答：增星异动（dbx +1103/周）、生态缺口、重大发版。
正文当前为人工样稿；正式版走 dbhub_v2 的 AI 解读管线（带 README 原文证据引用）初稿 + 人工把关。

## 重建数据

```bash
python build/build.py --collect-dir D:/dbhub_collect --out . --report
```

构建为模块化流水线（`build/` 下一个模块一个脚本，职责单一）：
`sources`（装载 M2b 新数据形态）→ `taxonomy`（17 库口径）→ `classify`（规则分类）+
`interp`（AI 解读护栏）→ `assemble`（归属并集主流水线）→ `emit`（输出）→ `report`（报告）。

数据源：`data/live/pool*.ndjson`（NDJSON 活文件）+ `state/interp_cache_shards/`、
`state/enrich_cache_shards/`（256 分片缓存，含安全披露日期 `sec_last`、发版日期
`rel_pub`）+ `config/overrides.json`（人工签发认领）+ git 历史池快照差分（周增星，
7 天窗；过渡期回退 M2b 前旧快照）。输出 `data/pool.js`、`data/detail.js`、
`build/audit_wide_dbs.json`（≥10 库宽归属人工周检底册）。

重构等价性验收已于 2026-10-09 完成（新旧输出 0 差异）；验收脚本
`verify_equivalence.py` 已随旧脚本一同归档于 `_backup_build_20261009/`
（其对比前提——增星基准通道②——自 10-14 通道①接棒后不再成立，不再可复跑）。

## 口径说明（诚实性）

- 类别为**规则推导**（topic/名称/描述关键词，附置信度与依据串）；
- 维护状态：`已归档`=GitHub Archived；`疑似停维`=★≥100 且 7 天零提交（首页预警卡口径 ★≥1k、仅工具类、仅 17 库归属）；
- `x/12 类工具覆盖`：12 个工具类别中有收录项目的类别数，空缺即选型信号；
- 活跃度指数公式公开：`c7×2 + 近30天发版×15 + 贡献者档(≤20)` 封顶 100；
- 周增星覆盖 45%（新入库项目无基线显示 —）；
- 未归类（~5.1k）带规则提示（如「范围外:redis」），后续手工认领（`classify/overrides.json`）。

## 部署（GitHub Pages）

纯静态、全相对路径、`<script>` 加载数据（无 fetch/CORS）、`.nojekyll` 已就位、总体积 ~11MB：

```bash
git init && git add . && git commit -m "数据库开源生态观测 demo"
git remote add origin https://github.com/<you>/dbhub_page.git && git push -u origin main
# 仓库 Settings → Pages → Deploy from branch → main / (root)
```

## 正式版路线

GitHub Actions 每晚自动重建（collect 仓库本来就每晚采集：数据日更 + 编辑周更）、
RSS/公众号推送、`overrides.json` 认领、深读 AI 初稿管线。
