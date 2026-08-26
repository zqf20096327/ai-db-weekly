# 数据库开源技术周报 · 生产 SOP

> **文档性质**：周报生产操作手册（Standard Operating Procedure）
> **版本**：v1.0（首版，2026-08-05）
> **适用**：每周生产一期《数据库开源技术周报》公众号内容
> **状态**：流程定稿，采集架构规范已写入（供后期脚本化），本期不含脚本代码

---

## 目录

- [一、核心原则与内容红线](#一核心原则与内容红线)
- [二、Topic 范围](#二topic-范围)
- [三、栏目结构（10 个固定栏目）](#三栏目结构10-个固定栏目)
- [四、采集架构与数据清单（核心章节）](#四采集架构与数据清单核心章节)
- [五、信源体系（三轨制）](#五信源体系三轨制)
- [六、筛选规则（四层漏斗）](#六筛选规则四层漏斗)
- [七、安全合规红线](#七安全合规红线)
- [八、公众号排版模板](#八公众号排版模板)
- [九、完整样板（填真实数据）](#九完整样板填真实数据)
- [十、每周生产流程（SOP 执行步骤）](#十每周生产流程sop-执行步骤)

---

## 一、核心原则与内容红线

### 1.1 总原则

**全周报"零主观判断"，仅「本周重点分析」栏目开一个受控口子，允许 AI 辅助理解。**

周报的定位是 **GitHub 数据的中文搬运工 + AI 翻译员**，不替读者下任何技术判断。这样做既规避法律/合规风险（尤其内核技术、性能、安全等领域），又降低生产门槛（无需深入内核知识）。

### 1.2 三种内容类型

| 内容类型 | 适用栏目 | 做法 | 风险 |
|---|---|---|---|
| 客观数据 | 榜单 / 版本 / License | 直接搬运 GitHub 数据 + 标出处 | 零 |
| AI 翻译 | 生态工具 / AI 板块 | 忠实翻译 README/release notes 的作用，不延伸 | 低 |
| AI 理解（受控） | 仅「本周重点分析」 | 回答"做什么 / 解决什么 / 突出点 / 为什么解读"，禁评判对比 | 中（需人审） |

### 1.3 全周报红线

**禁止行为（全周报适用，无一例外）：**

- ❌ 不点评好坏（"优秀""很差""值得上车"）
- ❌ 不做性能对比（"A 比 B 快""比 XX 强"）
- ❌ 不预测趋势（"必将取代""未来主流""颠覆"）
- ❌ 不解读内核技术原理（不擅长的领域，风险高）
- ❌ 不解读法律条款（license 只报字段，不解读法律含义）

**禁用词清单（出现即违规）：**

`最强 / 最快 / 颠覆 / 必将 / 重大 / 震惊 / 碾压 / 革命性 / 王者 / 神器 / 吊打`

**免责声明（文末必带）：**

> 数据来自 GitHub 公开 API，采集时间为本周期对应日期。所有版本特性、license 信息以各项目官方文档及 LICENSE 文件为准。

### 1.4 周报的核心价值（靠什么吸引读者，而不靠主观点评）

- **价值①：聚合省时间** —— 把分散在 GitHub 的信息整理成"5 分钟读完"
- **价值②：中文翻译友好** —— release notes 是英文，AI 忠实翻译成准确中文
- **价值③：数据排名可视化** —— star 榜、上涨榜、活跃榜，客观排名本身就有吸引力

**一句话：护城河是"聚合 + 翻译 + 排名可视化"，不是"点评/判断"。**

---

## 二、Topic 范围

### 2.1 16 个 Topic（不区分大小写）

```
database
oracle
mysql
postgresql
mariadb
sqlserver
opengauss
tidb
oceanbase
tdsql
polardb
polardb-x
yashandb
goldendb
gbase
dm
```

### 2.2 两类处理策略

| 类型 | 包含 | 特点 | 处理策略 |
|---|---|---|---|
| **泛 topic** | database / oracle / sqlserver | 命中量大（database 单独命中数万）、噪音重 | 必须叠加过滤（语言 + star 阈值 + 黑名单） |
| **产品名 topic** | tidb / opengauss / polardb / polardb-x / yashandb / goldendb / gbase / dm / oceanbase / tdsql / mysql / postgresql / mariadb | 精准，用于顺藤摸瓜找生态 | 直接搜索，但要注意同名校验 |

> ⚠️ **撞名提醒**：产品名 topic 容易搜到无关项目（如实测发现 `opengauss` 会搜到 NeurIPS 论文 `OpenGaussian`）。必须用第 6 章黑名单过滤，并人工抽查。

---

## 三、栏目结构（10 个固定栏目）

栏目顺序 = 读者阅读顺序。**①②④三个动态栏目是焦点，总榜是背景板（③活跃度已并入总榜为🔥标签）。**

### ① ⭐ 快速上涨榜（动态焦点之一）

- **口径**：7 日 star 净增排序，排除总榜前 5（只看腰部黑马）
- **数据依赖**：当日快照 − 7 天前快照（必须有日快照才能算）
- **负值处理**：净增可能为负（项目掉粉）。负值项目不上榜；如某重要项目大幅掉粉，可在④本周重点或单独"异动提示"如实记录
- **纯客观数据**
- **首期限制**：第一周无对比基准，此栏标注"首期，无净增数据"，第二周起完整

### ② 🆕 新生项目（动态焦点之二）

- **设计思想**：宽进严出。**发现要宽（不漏真新项目），展示要克制（不噪）。** 数据库是慢热赛道，7 天窗太苛刻，30 天才能看到真实苗头。
- **发现池口径**：30 天内创建 + star ≥ 3 + 工程语言 + 有 README + 有实质代码
- **关键过滤：内容相关性** —— description 必须含数据库核心词，且项目"本身是数据库相关"（而非"只是用了数据库"），挡伪相关（如记账 app 打了 postgresql 标签）
- **双档展示分流**：
  - 🆕 **新星榜**：star 3 ~ 30 —— "先露脸，早期观察"
  - 🌟 **潜力榜**：star ≥ 30 + 近 30 天有 push（用 `pushed_at` 判断，数据源2已采） —— "已发酵，值得关注"
  - 📌 注：潜力榜用 `pushed_at`（近 30 天有 push 即算活跃）而非 commit_count，因为数据源2不采 commit，避免字段依赖断裂
- **纯客观数据**
- **降噪**：去重（同作者批量建库只取 1 个）+ 内容相关性过滤 + 工程语言 + 代码质量 + 黑名单

### ③ 🔥 活跃度（不单独成榜，作为⑤总榜的标签）

- **设计变更**：活跃度不再单独占一个榜单（避免与其他榜重叠），而是作为⑤总榜上的一列**标签**
- **口径**：近 7 天 `commit_count_7d`（数据源4）达阈值 → 打 🔥 标
- **数据依赖**：用 `commit_count_7d`（数据源4）判断，不是用 `pushed_at`
- **⚠️ 字段陷阱**：
  - `pushed_at` 只记"最后一次 push 时间点"，不记次数，只能判断"是否活跃"，不能排序"谁更活跃"
  - 且 `pushed_at` 包含 tag/分支创建，不完全等于 commit
  - 正确做法：`pushed_at` 用于"近 7 天是否活跃"过滤；`commit_count_7d` 用于判断是否打 🔥
- **呈现方式**：在⑤总榜加一列，活跃项目标 🔥，读者一眼看到"谁在真写代码"
- **纯客观数据**

### ④ ⭐ 本周重点分析（动态焦点之三，唯一允许 AI 理解的栏目）

- **入选机制**：客观信号分驱动（见下"信号分计算"），取总分最高 1 个（最多 2 个）
- **内容框架**：固定四问（见下"内容框架"），AI 辅助理解，需人工审核
- **仍受统一红线约束**（禁对比/评判/预测）

#### 信号分计算（权重可校准）

| 信号维度 | 触发条件 | 分值 |
|---|---|---|
| 重大版本 | 当周发布大版本（主版本号变更，如 18→19 / 4.5→4.6） | +40 |
| star 异动 | 当周 star 净增进入快速上涨榜前 3 | +30 |
| 首次入榜 | 新冒出、首次进总榜或 star 破阈值 | +25 |
| License 变更 | 当周 license 发生变化 | +25 |
| 活跃度突变 | commit/PR 量较前周显著上升 | +15 |
| 影响面加权 | 该项目现有 star 越高，同样事件影响越多人 | × 系数 |

> 📌 **权重为初值，需每周校准**：第一周跑完，检查选出的重点项目是否"真的值得解读"。如果不是，调权重。SOP 不写死成真理。

#### 内容框架（固定四问）

每周重点项目，按这四个问题写，AI 辅助生成初稿，人工审核：

1. **这个项目做什么** —— 基于官方 README/description 客观陈述
2. **解决什么问题** —— 基于官方文档说明它面向的场景
3. **有哪些突出点** —— 基于 release notes / 官方特性列表，转述而非评判
4. **为什么解读它** —— 用信号分回答（"本周发布主版本 + star 净增进前3"，所以入选）

> ✅ 允许：解释"这个变更是什么意思" / "为什么值得注意" / 翻译技术概念
> ❌ 禁止：性能对比 / 好坏评判 / 趋势预测 / 绝对断言 / 内核原理断言
> 📌 必须标注："以下为 AI 辅助解读，以官方文档为准"

### ⑤ 📊 Top 总榜（背景板，非焦点）

- **口径**：所有项目（内核 + 工具 + AI）**统一按 star 降序**，不分类
- **候选池**：内核白名单 + 搜索发现的工具/AI（避免内核因无 topic 标签而漏掉）
- **展示**：排名 / 项目 / 品类 / star / 本周变化（↑/↓/新入榜）
- **定位**：满足"全景认知"，但**每周首屏焦点放在①②③④**，总榜排在焦点之后
- **首期限制**：第一周无"本周变化"对比基准，此列标注"首期"，第二周起完整

### ⑥ 📦 版本速递（拆为两个子栏）

版本号本身作为标题，内容按两类拆分（呼应"全周报不割裂内核/工具"原则）：

#### 6a 🛠️ 生态工具版本
- 本周发版的工具类项目

#### 6b 🤖 AI 板块版本
- 本周发版的 AI 类项目

**每条内容**：
- 版本号（标题）+ 日期 + 官方 release notes 要点 + 出处链接
- 英文 notes 用 AI **忠实摘要**（不延伸、不评判）
- 标注"信息来自官方 Release Notes"

### ⑦ 🛠️ 生态工具（常态展示）

- **发现方式**：topic（16 个）+ **工具关键词**
- **工具关键词**：`proxy / pooler / ha / migration / backup / client / operator / orm / etl / sync`
- **四类归类**（归类依据项目 README 自述，非主观判断）：
  - ① 中间件 / 代理（proxy / pooler）
  - ② 高可用 / 编排（ha / operator）
  - ③ 管控 / 治理（client / orm）
  - ④ 迁移 / 备份（migration / backup / etl / sync）
- **每个工具**：AI 翻译"做什么用的"（基于 README），不点评好坏

### ⑧ 🤖 AI 能力专题（AI 单独板块，不分类）

- **发现方式**：topic（16 个）+ **AI 关键词**
- **AI 关键词（8 个）**：`llm / agent / skill / mcp / text2sql / nl2sql / copilot / ai-dba`
- **展示方式**：**不分类，直接按 star 展示 top**
- **每个项目**：AI 翻译作用（基于 README/description），不主观判断
- AI 项目不混入通用工具板块（第⑦栏），单独成栏

### ⑨ ⚖️ License 雷达（变更才详报）

- **常态周**：只一行"本期无 license 变更"
- **变更周**：展开变更项目 + 影响（选型提示）
- **全景表**：放文末附录，不每周占正文
- **数据来源**：GitHub 结构化数据（license 字段 + NOASSERTION 标记 + LICENSE 文件 commit 历史）
- **只报**：当前 license 字段 + 变更事件 + 选型提示（建议读 LICENSE 原文）
- **不解读法律条款**

### ⑩ 📌 统计口径 + 来源说明 + 纠错声明（文末）

- **统计口径**：公开每个榜单的计算方式（净增怎么算、新生口径、活跃度定义）
- **来源说明**：统一格式 `📎 来源:[xxx](链接)`
- **纠错声明**：如有上期错误，开头加「更正」栏说明（详见 7.5）

---

## 四、采集架构与数据清单（核心章节）

### 4.1 核心思想

**周报的动态信号（净增 / 新入榜 / 变化）必须靠时间序列对比，不能靠一次查询。**

→ **每天采一次快照，7 天后汇总对比。** 这是周报能成立的技术地基。

**定时任务由用户外部系统触发**，采集逻辑内置在每个 topic 脚本中（共 16 个脚本）。

### 4.2 六类数据源（从 10 个栏目倒推，归并而成）

#### 数据源 1️⃣ 项目全量快照（每日全量采，核心地基）

- **用途**：支撑 ①②④⑤ 所有"对比 / 排序"类栏目（③活跃度已并入⑤总榜为🔥标签）
- **endpoint**：
  - 搜索：`GET /search/repositories?q={topic}+{关键词}&sort=stars&order=desc`
  - 白名单：`GET /repos/{owner}/{repo}`
- **字段最小集**：

| 字段 | 用途 |
|---|---|
| `full_name` | 项目唯一标识 |
| `description` | 生成周报文案 / AI 翻译源 |
| `html_url` | 来源链接 |
| `stargazers_count` | ⑤总榜 / ①净增计算 |
| `forks_count` | 生态活跃度参考 |
| `open_issues_count` | 社区健康度参考 |
| `watchers_count` | 关注度 |
| `language` | 筛选（工程语言）/ 降噪 |
| `license.spdx_id` | ⑨ License 雷达 |
| `created_at` | ②新生项目判断（30 天内） |
| `pushed_at` | ⑤总榜 🔥 活跃标签判断 |
| `updated_at` | 元数据变化 |
| `default_branch` | 跋 release 查询用 |
| `topics[]` | 分类参考 |
| `homepage` | 官方链接 |

- **自加字段**：`snapshot_date`（采集日期，对比用）/ `search_topic`（哪个 topic 搜到的，溯源用）

#### 数据源 2️⃣ 新生项目池（每日采，量小）

- **用途**：②新生项目榜（30 天内创建 + star ≥ 3 + 内容相关性过滤）
- **endpoint**：`GET /search/repositories?q=topic:{词}+created:>{30天前}+stars:>=3&sort=stars&order=desc`
- **字段**：`full_name / created_at / stargazers_count / pushed_at / description / language / html_url / topics[]`
- **⚠️ 关键**：topic 标签由作者自填，**不可靠**（记账 app 也会打 postgresql 标签）。必须客户端做**内容相关性二次过滤**：
  - description 含数据库核心词：`database / sql / query / postgres / mysql / mongo / redis / OLAP / OLTP / DBA / migration / schema / vector` 等
  - 判定项目"本身是数据库相关"，而非"只是用了数据库"
- **逻辑**：快照的特殊切片，只采"30 天内新建的"，量小，每天采记录新冒出的项目

#### 数据源 3️⃣ Release 事件（每周采，按需）

- **用途**：⑥版本速递
- **endpoint**：`GET /repos/{owner}/{repo}/releases?per_page=N`
- **⚠️ 重要**：Releases API **不支持 `since` 参数**（`since` 是 Commits/Issues 的参数）。API 默认按 `published_at` 倒序返回全部 release，**必须客户端用 `published_at > 7天前` 过滤**本周发布。
- **范围**：只对白名单 + 上涨榜前 N 项目拉
- **字段**：

| 字段 | 用途 |
|---|---|
| `tag_name` | 版本号（标题） |
| `published_at` | 发布日期（**客户端按此过滤近 7 天**） |
| `name` | 版本标题 |
| `body` | release notes 原文（AI 摘要源） |
| `html_url` | 链接（出处） |
| `prerelease` | 是否预览版（可用于过滤 beta/RC） |
| `draft` | 是否草稿（`draft:true` 的不展示） |

#### 数据源 4️⃣ Commit 活跃度（每日采或按需）

- **用途**：⑤总榜 🔥 活跃标签 + ④重点信号（活跃度突变）
- **endpoint**（推荐轻量）：
  - `GET /repos/{owner}/{repo}/stats/participation`（52 周每日 commit 数）
  - 或 search 算近 7 天总数：`GET /search/commits?q=repo:{owner}/{repo}+committer-date:>{7天前}`
- **⚠️ 异步计算坑**：`/stats/participation` 是 GitHub **异步计算**的统计接口，第一次调用常返回 `202 Accepted`（还在算，无数据体）。脚本需**轮询**（间隔几秒重试，或多次调用直到返回 200），或**兜底用 commits search 算总数**。不要把首次 202 当成"无 commit"。
- **范围**：只对"已入候选池"项目采，不全员
- **字段**：`commit_count_7d`（近 7 天提交数，算出来）/ `top_contributors`（近 7 天主要提交者，可选）

#### 数据源 5️⃣ License 变更检测（每周采，按需）

- **用途**：⑨License 雷达
- **endpoint**：`GET /repos/{owner}/{repo}/commits?path=LICENSE&since={7天前}`
- **字段**：`license_changed`（bool）/ `changed_at` / `changed_by`
- **逻辑**：不用采 license 全文，只检测"本周 LICENSE 文件是否动过"，动了才进雷达详报

#### 数据源 6️⃣ Org 全量扫描（每日采，补盲区）

- **用途**：**解决内核 repo topics 为空导致 topic 搜索漏采**（实测发现 mysql-server、openGauss-server 的 topics 为空，topic 搜索完全搜不到）
- **endpoint**：`GET /orgs/{org}/repos?sort=stars&direction=desc&per_page=100&type=public`
- **配额**：走 **Core API**（5000/小时），**不占 Search 限流**
- **范围**：白名单里的 org 清单（见 5.1），实测每个 org 的 repo 数很少（mysql org 24 个、polardb org 小），调用成本极低
- **字段**：同数据源1（项目快照字段集）
- **逻辑**：拉取每个 org 的全部 public repo，与 topic 搜索结果合并去重（按 full_name）

### 4.3 采集节奏总表（定时任务的触发依据）

```
【每日凌晨】（外部定时器触发，每 topic 一个脚本）
  ├─ 数据源 1  项目全量快照     全量采（地基，不可省）
  ├─ 数据源 2  新生项目池       全量采（量小）
  ├─ 数据源 4  Commit 活跃度    对候选池项目采
  └─ 数据源 6  Org 全量扫描     对白名单 org 扫描（Core API，不占 Search 限流）

【每周一次】（周报生产前）
  ├─ 数据源 3  Release 事件     对白名单 + 上涨榜前 N 采
  └─ 数据源 5  License 变更检测 对候选池采
```

### 4.4 全量 vs 按需分离（控制成本与限流）

- **每日全量采**（便宜且必需）：
  - 数据源 1（项目快照：轻量元数据）
  - data-source 2（新生项目池：量小）
  - 数据源 6（Org 全量扫描：走 Core API 不占 Search 限流）

- **按需采**（只对候选池，避免重查询拖垮限流）：
  - 数据源 3（release 全文）
  - 数据源 4（commit 历史）
  - 数据源 5（license 变更）

> 判断依据：全量采的是"便宜且必需的元数据"；按需采的是"重查询"。

### 4.5 每个 Topic 脚本的标准结构（供后期脚本化）

```
每个 topic 一个独立脚本（共 16 个），架构统一：

① GITHUB_TOKEN 认证（提高限流到 30 次/分钟）
② 先查总数（per_page=1 探 total_count），判断 topic 量级
③ 按 4.9 的分级策略决定采法：
   - 巨型/中型(database/mysql/pg/oracle)：
     互斥去重(-topic:xxx) → star≥10 → star三档 → star10-99按created拆
   - 小型(tidb/dm/oceanbase)：直接 base 全采
   - 微型(tdsql/polardb等)：直接 base 全采，一次取完
④ ⚠️ 动态限流（不是固定休眠 61 秒！）：
   - 每次调用后读取响应头 X-RateLimit-Remaining
   - 剩余 > 5：间隔 2 秒继续
   - 剩余 ≤ 5：sleep 到 X-RateLimit-Reset 时间再继续
   - 实测：优化后每次快照约 194 次调用，限流 30/分 → 约 7 分钟
   - ❌ 固定休眠 61 秒会导致 ×61 倍耗时，完全不可行
⑤ ⚠️ GitHub Search 1000 条硬限制：
   - 单次查询(per_page=100)最多翻 10 页 = 1000 条
   - 超过的必须拆分查询(star档位/created日期),否则只能拿到前1000条
   - 脚本需检测 total_count > 1000 → 自动触发再拆分
⑥ 每次结果立即写入文件（落盘不丢数据）
⑦ 文件按 topic 命名：result_{topic}.json
⑧ 目标：尽可能覆盖全部项目（star≥10 部分）
```

> ⚠️ **互斥语法注意**：GitHub Search 用**减号**做排除（`-topic:mysql`），不支持 SQL 的 `NOT` 语法（`NOT topic:mysql` 会返回 422 错误）。

### 4.6 存储结构

```
data/
├── snapshot_20260805/          ← 每天一份快照
│   ├── database.json
│   ├── mysql.json
│   ├── tidb.json
│   ├── opengauss.json
│   └── ...
├── snapshot_20260804/
│   └── ...
└── snapshot_20260729/          ← 7 天前的快照（对比基准）
    └── ...
```

每天一个目录，每个 topic 一个文件。**7 天对比 = 直接 diff 两个目录的对应文件。**

### 4.7 快照文件格式标准（单个项目条目示例）

```json
{
  "full_name": "pingcap/tidb",
  "description": "TiDB is built for agentic workloads...",
  "html_url": "https://github.com/pingcap/tidb",
  "stargazers_count": 40385,
  "forks_count": 16320,
  "open_issues_count": 6732,
  "watchers_count": 1120,
  "language": "Go",
  "license": { "spdx_id": "Apache-2.0", "name": "Apache License 2.0" },
  "created_at": "2015-09-06T05:53:33Z",
  "pushed_at": "2026-08-05T02:17:25Z",
  "updated_at": "2026-08-05T03:00:00Z",
  "default_branch": "master",
  "topics": ["go", "database", "mysql", "distributed-database", "tidb"],
  "homepage": "https://www.pingcap.com",
  "snapshot_date": "2026-08-05",
  "search_topic": "tidb"
}
```

### 4.8 关键说明（写入 SOP）

1. **快照存"原始全量"**，不只存变化（未来可算任意天数变化，如 30 天趋势）
2. **第一周无对比基准** → 首期只能报绝对值（总榜 / 活跃度），①快速上涨、⑤总榜"本周变化"等动态栏目留白并如实标注"首期，无对比数据"，第二周起完整
3. **Search API 有索引延迟** → 新建仓库可能几天后才被索引，新生项目可能滞后；文末如实说明
4. **目标**：尽可能覆盖全部项目（用户明确要求）

### 4.9 分级采集策略（基于实测优化，避免浪费）

**实测发现**（2026-08-05 真实 token 验证）：

1. **16 个 topic 规模极度分化**：mysql 102k / postgresql 106k / database 49k 占 95%；tdsql(3)、polardb(4) 等微型 topic 拆关键词几乎全是 0
2. **巨型 topic 高度重叠**：database/mysql/postgresql 互相重叠，原始合计 26 万，去重后大幅缩小
3. **star<10 占 94% 是噪音**：mysql 的 star<10 有 8.6 万条，全是玩具/作业/废弃，本就要被黑名单过滤
4. **GitHub Search 硬限制**：单次查询最多返回 1000 条（per_page=100 × 10 页），超过的拿不到
5. **关键词拆分覆盖率仅 8.5%**：18 个关键词只能覆盖 topic:mysql 的 8.5%，91.5% 的项目描述里不带这些词 → 关键词拆分会大量漏采

**结论：巨型 topic 不能用关键词拆分（会漏），要用"互斥去重 + star 阈值 + star 档位"三层组合。**

#### 4.9.1 巨型/中型 topic 的三层拆分方案（核心）

适用于：database / mysql / postgresql / oracle（实测这四个量级大，需互斥去重 + 拆分）

> ⚠️ **互斥仅限这四大泛 topic**。国产库 topic（polardb/opengauss/dm/tidb/oceanbase 等）**不做互斥**——它们量小直接全采，且国产库常打上游标签（如 PolarDB 打了 database+postgresql），互斥会误杀。mariadb/sqlserver 也不互斥，仅按 star 档位拆分。

```
第①层 互斥去重（仅四大库之间,解决重叠）
  每个 topic 排除其他三个,语法用减号(GitHub 不支持 NOT):
    database 互斥 = topic:database  -topic:mysql  -topic:postgresql -topic:oracle   → 37k
    mysql    互斥 = topic:mysql     -topic:database -topic:postgresql -topic:oracle  → 91k
    postgresql互斥= topic:postgresql -topic:database -topic:mysql  -topic:oracle    → 98k
    oracle   互斥 = topic:oracle    -topic:database -topic:mysql  -topic:postgresql  → 4k
  效果:去掉 12% 重叠
  ⚠️ 不对国产库 topic 做互斥(实测 polardb 只有4个,直接全采)

第②层 star≥10 砍噪音（解决量级）
  互斥 + stars:>=10
  效果:砍掉 94% 的 star<10 噪音(它们本就要被黑名单过滤)
  实测结果:
    database 互斥+star≥10 = 5,425
    mysql    互斥+star≥10 = 4,909
    pg       互斥+star≥10 = 4,590
    oracle   互斥+star≥10 = 405 ✓ 一次采完

第③层 star 三档拆分（解决 1000 条硬上限,仅 star≥10 部分需要）
  对 star≥10 的部分再拆三档:
    stars:10..99     (实测 3000-4000,仍超1000,需第④层)
    stars:100..999   (实测 700-1200,基本可采)
    stars:>=1000     (实测 100-400,可采)

第④层 star10-99 按日期拆（仅此档需要,解决仍超1000）
  star10-99 + created:>=2025-01-01     (今年)
  star10-99 + created:2024-01-01..2024-12-31  (去年)
  star10-99 + created:<=2023-12-31     (更早)
  每段降到 1000 以内
```

#### 4.9.2 各级 topic 的完整采集策略

```
┌─ 巨型 topic（base > 1万）：database / mysql / postgresql
│    策略：四层组合（互斥 + star≥10 + star三档 + star10-99按日期拆）
│    实测：263k → 15k（砍94%），约 161 次分页调用
│
├─ 中型 topic（base 1千-1万）：oracle / mariadb / sqlserver
│    策略：互斥去重 + star≥10 + star档位
│    oracle 实测：互斥+star≥10 = 405,一次采完 ✓
│
├─ 小型 topic（base 10-1千）：tidb(248) / dm(207) / oceanbase(54)
│    策略：直接 base 全采（量小,不拆关键词不拆star）
│    预估：3 topic × 1次 + 分页 = 约 10 次调用
│
└─ 微型/空 topic（base < 10）：opengauss(22)/polardb(4)/tdsql(3)/
                                  polardb-x(6)/gbase(3)/yashandb(0)/goldendb(0)
     策略：直接 base 全采，一次取完
     特殊：yashandb/goldendb 为 0,如实记录"GitHub 无项目"
```

#### 4.9.3 优化后的调用数与耗时（实测）

| 指标 | 原方案(全拆关键词) | 优化后(三层组合+分级) |
|---|---|---|
| 巨型topic项目数 | 263,090(含重叠+噪音) | **15,329**(互斥+star≥10) |
| API 探测调用(Search) | 288 | 16(探 base) |
| 巨型/中型三层拆分(Search) | ~700 | ~150(互斥+star档位+日期拆) |
| 小型/微型全采(Search) | — | ~12 |
| 新生项目30天窗(Search) | — | 16 |
| 白名单+Org扫描(Core) | — | ~22(走5000/小时,不占Search限流) |
| 合计 Search 调用 | ~1000 | **~194** |
| 耗时(限流30/分,间隔2秒) | ~33 分钟 | **~7 分钟** |
| 数据质量 | 含9.4万噪音 | 噪音已前置过滤 |

#### 4.9.4 关键词的用途重新定义

**实测发现关键词拆分覆盖率仅 8.5%，不能用来"采全集"，但仍有价值：**

- ❌ 不能用关键词做"主拆分维度"（会漏采 91.5%）
- ✅ 关键词用于**采集后的分类标注**：采回的项目，检查 description/topics 是否含工具关键词(proxy/ha/migration...)或 AI 关键词(llm/mcp/copilot...)，据此归入⑥生态工具栏或⑧AI 板块
- 即：**采集用互斥+star，分类用关键词**

> 📌 **分层探测逻辑**：脚本先对每个 topic 跑 `per_page=1` 的 base 查询拿 total_count，再按量级决定采法。这一步只花 16 次调用，却省掉 200+ 次空查询。

---

## 五、信源体系（三轨制）

> ⚠️ **为什么是三轨**：实测发现单一信源都会漏——topic 搜索漏掉 topics 为空的内核（如 mysql-server），白名单漏掉生态项目，互斥拆分误杀打上游标签的国产库。必须三轨互补 + 去重合并。

### 5.1 白名单（固定追踪核心 repo + org）

手工确认的官方 repo 和 org 清单，**固定不变**，每日纳入快照。

**repo 白名单（核心内核，直接采）：**

| 品类 | 项目（repo） | 备注 |
|---|---|---|
| 国际主流关系库 | mysql/mysql-server、postgres/postgres、MariaDB/server、sqlite/sqlite | ⚠️mysql-server/openGauss topics 为空,靠白名单+org补采 |
| Oracle 生态 | （Oracle 闭源，无官方 GitHub 内核） | oracle topic 主要抓生态工具/驱动，**无内核白名单** |
| NewSQL | pingcap/tidb、oceanbase/oceanbase、cockroachdb/cockroach、tikv/tikv | |
| 嵌入式 / 分析 | duckdb/duckdb | |
| 国产开源-PG系 | opengauss-mirror/openGauss-server（⚠️确认官方源） | topics 为空,靠 org 扫描 |
| 国产开源-阿里 | polardb/PolarDB-for-PostgreSQL、polardb/polardbx-engine | ⚠️PolarDB 打了 database+postgresql 标签,互斥会误杀,靠白名单+org |
| 国产开源-腾讯(TDSQL) | （待确认 Tencent org 下的 repo） | ⚠️需确认 |
| 国产开源-其他 | yashandb / goldendb / gbase / dm（⚠️部分在 Gitee） | 需逐个确认 |

**org 扫描清单（数据源6，拉取 org 下全部 repo）：**

| org | 包含 | 备注 |
|---|---|---|
| mysql | mysql/mysql-server 等 24 个 | topics 为空的内核在此 |
| polardb | PolarDB 全家桶 | topic:polardb 只有4个,org 补全 |
| ApsaraDB | 阿里云数据库工具 | PolarDB 生态周边 |
| oceanbase | OceanBase 内核+工具 | |
| opengauss-mirror | openGauss 系 | topics 为空,靠 org |
| pingcap | TiDB 生态 | |
| tikv | TiKV 生态 | |

> ⚠️ **白名单维护要点**：
> 1. 每个 repo 必须手工确认是"官方源"而非镜像/撞名（如 opengauss 搜索结果中排第一的 `math-inc/OpenGauss` 是 Python 项目，非官方）
> 2. **Oracle/TDSQL/YashanDB/GoldenDB/GBase/DM 这几个需逐个确认**：部分闭源、部分在 Gitee、部分无官方 repo
> 3. **org 清单是白名单的关键补充**：内核 repo topics 常为空，靠 org 扫描兜底
> 4. 这是地基，错误会污染所有榜单。建议首期前花半天逐个核对

### 5.2 Org 全量扫描（每日采，补 topic 搜索盲区）

- **用途**：解决内核 repo topics 为空（如 mysql-server、openGauss-server）导致 topic 搜索漏采
- **方式**：对 5.1 的 org 清单，调用 `GET /orgs/{org}/repos` 拉取全部 public repo
- **配额**：走 Core API（5000/小时），不占 Search 限流
- **实测**：mysql org 24 个、polardb org 小，调用成本极低

### 5.3 搜索发现（每日跑，工具/AI 项目）

- **通用工具**：topic + 工具关键词（proxy / pooler / ha / migration / backup / client / operator / orm / etl / sync）
- **AI 项目**：topic + AI 关键词（llm / agent / skill / mcp / text2sql / nl2sql / copilot / ai-dba）
- 按 4.5 的脚本标准结构跑，每 topic 一脚本
- ⚠️ **关键词用于采集后分类，不用于主拆分**（实测覆盖率仅 8.5%，详见 4.9.4）

### 5.4 搜索查询语句模板（供脚本用）

```
# 通用工具（示例：tidb 的 proxy 类）
GET /search/repositories?q=topic:tidb+proxy+stars:>10+pushed:>2026-07-29&sort=stars&order=desc

# AI 项目（示例：mysql 的 copilot 类）
GET /search/repositories?q=topic:mysql+copilot+stars:>10+pushed:>2026-07-29&sort=stars&order=desc

# 新生项目（示例：database 30天内新建 + star≥3）
GET /search/repositories?q=topic:database+created:>2026-07-05+stars:>=3&sort=stars&order=desc
```

---

## 六、筛选规则（四层漏斗）

### 第 0 层：范围圈定

- 泛 topic（database / oracle / sqlserver）：必须叠加过滤（语言 + star 阈值）
- 产品名 topic：顺藤摸瓜，但校验撞名

### 第 1 层：准入闸门（全部满足才进候选池）

```
✅ 准入条件：
  ① 数据库相关（内核 / 工具 / AI，任一）
  ② 有版本管理（release 或 tag）或有实质代码
  ③ 仍活跃（近 90 天有 commit，或近 7 天有 push）
  ④ 有 README（非空、非占位）
  ⑤ fork 处理：fork 项目默认剔除（只保留原创源）
     - 判断：API 返回的 fork 字段为 true，或 repo 是已知项目的 fork
     - 例外：fork 已独立发展、star 远超原项目（如 MariaDB fork 自 MySQL）→ 保留并标注"源自 XX"
```

### 第 2 层：黑名单关键词（命中任一即剔除）

```
【教程 / 学习类】
  教程、学习、笔记、面试、面试题、awesome、course、
  tutorial、learning、guide、handbook、cookbook、实战、课件

【作业 / 培训类】
  educoder、experiment、homework、lab、高校、大学、训练、比赛、race、contest、exam

【工具类（不进"数据库内核榜"，但分流到⑦生态工具栏，不剔除）】
  注意：ORM / driver / connector / migration / sync / backup / proxy / pooler / ha / operator 等
  这些不是噪音，是工具栏的素材。黑名单这里只挡"纯教程化的工具介绍"，不挡工具本身。
  判断：工具本身有代码、有 release → 进工具栏；纯文档介绍工具 → 剔除。

【镜像 / 搬运类】
  mirror、fork、docs、site、website、homepage、blog、-cn

【撞名 / 无关】
  star < 10 且 description 无数据库关键词 → 弃
  OpenGaussian 这类带尾字母的撞名 → 人工核对
```

### 第 3 层：价值评分卡（仅用于排序，不做主观判断）

| 维度 | 满分条件 |
|---|---|
| 真实性（25） | 官方 org / 核心内核（15）+ 有论文/规范背书（10） |
| 活跃度（25） | 近 7 天有 commit（10）+ 近 90 天有 release（10）+ contributor > 5（5） |
| 趋势（20） | star 7 日净增进品类 TOP（15）+ 非一次性爆点（5） |
| 稀缺性（15） | 填补品类空白 / 国产首个 / 唯一支持某特性 |
| 决策相关（15） | license 变更 / 重大架构调整 / 跨厂商对比点 |

> 📌 评分卡只用来给候选项目排序（决定谁上榜），**不写进周报正文**（正文零主观判断）。

### 6.x 新生项目专用过滤（针对 30 天 + star ≥ 3 的宽口径）

新生项目是"宽进严出"栏，过滤分四层：

**第①层：宽口径发现（保证不漏）**
- 30 天内创建 + star ≥ 3 + 工程语言 + 有 README + 有实质代码

**第②层：黑名单挡明显噪音**
- 教程 / 作业 / 镜像 / 撞名 / 纯脚本

**第③层：内容相关性二次过滤（关键，挡伪相关）**
- topic 标签由作者自填，不可靠（记账 app 也会打 postgresql 标签）
- description 必须含数据库核心词：`database / sql / query / postgres / mysql / mongo / redis / OLAP / OLTP / DBA / migration / schema / vector` 等
- 判定标准：项目"**本身是数据库相关**"，而非"只是用了数据库"
  - ❌ 记账 app（用了 PG 存储）→ 挡
  - ❌ 任务工作区（用了数据库）→ 挡
  - ✅ 跨库表迁移工具 → 留
  - ✅ 数据库加密备份工具 → 留
  - ✅ schema 审查 / N+1 检测 → 留

**第④层：双档展示分流**
- 🆕 新星榜：star 3 ~ 30（先露脸）
- 🌟 潜力榜：star ≥ 30 + 近 30 天有 push（用 `pushed_at`，已发酵）

**通用降噪**
- 去重：同一作者批量建库只取 1 个
- 语言过滤：主语言非工程语言的剔除
- 内容过滤：无 README 或 README 占位的剔除
- 性质过滤：纯模板 / 纯脚本的剔除

### 6.y 榜单归属规则与栏目分工（分层漏斗，防止霸屏）

一个项目可能同时符合多个榜单/栏目的入选条件。必须分两层处理：**榜单归属（防霸屏）** + **信息栏分工（防内容重复）**。

#### 第一层：榜单归属——分层漏斗（每个项目归入唯一主榜）

**问题**：star 越高、越活跃的项目，越容易同时命中多个榜单（如 Chat2DB 发版 → 同时进快速上涨/活跃/AI/总榜/本周重点），读者翻来覆去看同一个项目，周报显得空洞。

**根因**：5 个榜单从同一候选池选，排序依据高度相关（star 高的往往净增也高、commit 也活跃），数学上必然重叠。

**规则：每个项目按固定优先级判断，归入唯一主榜，命中即停。**

```
判断顺序（从上到下，命中一个就停，不再进下一判断）：

  Step 1：是④本周重点选中?
           → 是 → 归入④，其他所有榜单只列名+链接+"见本周重点"
           → 否 → 继续

  Step 2：30 天内创建?
           → 是 → 归入②新生项目榜
           → 否 → 继续

  Step 3：本周 star 净增进入 TOP?
           → 是 → 归入①快速上涨榜
           → 否 → 继续

  Step 4：AI 类项目且 star 头部?
           → 是 → 归入⑧AI 能力专题
           → 否 → 继续

  Step 5：都不命中
           → 归入⑤总榜（兜底，star 排名背景板）

活跃度（③）不作为归属榜：
  → 降级为⑤总榜上的 🔥 标签（commit 达阈值打标）
  → 信息不丢，但不单独占榜
```

**为什么是这个顺序（逻辑自洽）**：

| 顺序 | 榜单 | 理由 |
|---|---|---|
| Step1 | ④本周重点 | 单项目深度解读，选中即"本期主角"，其他只能列名 |
| Step2 | ②新生项目 | "新冒出"比"涨得快"更稀缺，读者最想发现新东西 |
| Step3 | ①快速上涨 | 本周异动，时效性强 |
| Step4 | ⑧AI 专题 | 分类榜，若 AI 项目同时涨快，优先讲"涨"（更有时效） |
| Step5 | ⑤总榜 | 兜底，无动态信号的项目在此 star 排名 |

**边界情况**：

| 情况 | 处理 |
|---|---|
| ④选中项目也命中①②⑧ | ④独占，①②⑧里它只列名+"见本周重点" |
| 新生项目(30天)同时是AI类 | 归入②新生榜（Step2 先命中），⑧AI 专题不收 |
| AI 项目同时净增进 TOP | 归入①快速上涨（Step3 先命中），⑧AI 专题不收 |
| 项目无任何动态 | 只在⑤总榜 + 可能打 🔥 标 |
| 项目连续几周都涨 | 每周都进①快速上涨，直到不再净增进 TOP |
| 项目活跃但没进动态榜 | ⑤总榜打 🔥 标，读者知道它活跃 |

**完整举例**：

```
假设某周数据：
  Chat2DB    27.6k  本周发版+净增进TOP+commit活跃+AI类 → 信号分最高
  pgvector   22.5k  commit活跃，但没净增进TOP
  xxx-new     85    30天内创建，star 3-30
  ProxySQL    6.9k  本周发版，其他无动态
  TiDB       40.4k  无任何动态

归属结果（分层漏斗）：
  Chat2DB  → Step1 命中(④本周重点) → ④独占，其他榜只列名
  xxx-new  → Step2 命中(30天内)   → ②新生榜
  pgvector → Step1-4 不命中        → ⑤总榜 + 🔥活跃标
  ProxySQL → Step1-4 不命中        → ⑤总榜（无🔥）+ ⑥版本速递（发版）
  TiDB     → Step1-5，Step5 兜底   → ⑤总榜

读者看到：零重复，每个项目只讲一个故事
```

#### 第二层：信息栏分工（防同一项目在信息栏内容重复）

| 情况 | 处理 |
|---|---|
| 项目被④本周重点选中 | 其他所有栏目只列名 + 链接，不展开 |
| 工具/AI 项目本周发版 | 在⑥版本速递展开（版本号+notes）；当周它在⑦生态工具/⑧AI 板块的条目改为"见版本速递" |
| 项目既上榜又发版 | 上榜归榜单（数据）；版本归⑥版本速递（notes）；内容不重叠 |
| 通用原则 | 数据归数据（榜单），事件归事件（版本/变更），作用归作用（工具/AI 栏），三者分开 |

> 📌 **发布前检查清单**：
> - 每个项目只归入一个主榜（④②①⑧⑤ 五选一）
> - 被舍掉的榜单有"见XX榜"标注
> - 没有项目在两个信息栏重复展开同样内容
> - ⑤总榜的 🔥 标签准确反映 commit 活跃度

---

## 七、安全合规红线

### 7.1 分层风险控制

| 层 | 处理方式 | 风险 |
|---|---|---|
| 数据 / 版本层 | 只报官方事实 + 链接，零解读 | 零 |
| 工具 / AI 层 | AI 翻译作用，不延伸判断 | 低 |
| License 层 | 只报字段 + 选型提示，不解读法律 | 低 |
| 重点分析层 | AI 理解受控，禁对比 / 评判 / 预测 | 中（需人审） |

### 7.2 禁用词清单

`最强 / 最快 / 颠覆 / 必将 / 重大 / 震惊 / 碾压 / 革命性 / 王者 / 神器 / 吊打`

### 7.3 禁止的高风险话术

- ❌ 技术诽谤："PG 19 的异步 IO 有严重性能问题"
- ❌ 未授权解读：把厂商未公开的内部设计当事实陈述
- ❌ 安全漏洞误报："这个版本有 RCE 漏洞，千万别用"（描述失实会引发恐慌）
- ❌ 性能对比误导："OceanBase 比 TiDB 快 3 倍"（无可信基准）
- ❌ 版权问题：大段复制 changelog / release notes（只摘要 + 标出处）

### 7.4 免责声明（文末必带）

> 数据来自 GitHub 公开 API，采集时间为本周期对应日期。所有版本特性、license 信息以各项目官方文档及 LICENSE 文件为准。

### 7.5 纠错机制（必备）

- 如某期发布了错误信息（版本号抄错、AI 翻译出错等），**下一期开头加「更正」栏**
- 模板：

  > **更正（上期纠错）**
  > 上期第 X 栏"XX 项目"版本号有误，应为 vX.X.X（非 vX.X.Y）。已更新，感谢读者指正。

- 这是技术媒体的基本规范，有法律顾虑更要有纠错通道。

---

## 八、公众号排版模板

### 8.1 整体结构（栏目顺序）

```
【开头】
  Slogan + 本期重点（1-2 句话点出本周最值得看的事）

【动态焦点】（首屏焦点）
  ① ⭐ 快速上涨榜
  ② 🆕 新生项目
  ④ ⭐ 本周重点分析（四问）

【背景参考】
  ⑤ 📊 Top 总榜（含 🔥 活跃标签，活跃度不再单独成榜）

【生态信息】
  ⑥ 📦 版本速递（6a 工具版本 / 6b AI 版本）
  ⑦ 🛠️ 生态工具
  ⑧ 🤖 AI 能力专题

【治理信息】
  ⑨ ⚖️ License 雷达

【结尾】
  ⑩ 📌 统计口径 + 来源说明 + 免责声明 + 引导关注
  + 📎 附录：License 全景表（常态）
```

### 8.2 Emoji 栏目标识体系（长期固定，形成品牌记忆）

```
⭐ 快速上涨    🆕 新生项目    🔥 活跃度
⭐ 本周重点    📊 Top 总榜    📦 版本速递
🛠️ 生态工具    🤖 AI 专题     ⚖️ License 雷达
📌 统计口径    📎 附录
```

> 📌 全篇 emoji 类型 ≤ 10 种，每个栏目固定一个，像"频道台标"。

### 8.3 三层信息结构（每条项目报道的视觉规范）

```
【标题行】 🔵 项目名 vX.X.X  ｜ 日期 ｜ ⭐ XXk     ← 事实层（客观数据）
【正文】   • 特性 1（AI 翻译 release notes）         ← 内容层（AI 翻译）
          • 特性 2
📎 来源:[官方 Release Notes](链接)                  ← 来源层（出处）
```

- 观点层（如有，仅限本周重点栏）用引用块视觉隔离
- 统一来源标注格式：`📎 来源:[xxx](链接)`

### 8.4 表格规范

- 列数 ≤ 4
- 每格 ≤ 8 字（手机端折行会丑）
- 对比类内容优先用表格（读者最爱截图转发）

### 8.5 信息密度控制

- 一期：5-6 个项目报道 + 1 个本周重点 + 榜单若干
- 宁少勿多，控制在 5 分钟阅读量
- 超量 → 读者"收藏了等于看了"，下周就不打开

### 8.6 固定开头结尾

**开头**：

```
> 每周 5 分钟，看懂 GitHub 上数据库开源生态的一手动态。
> 本期重点：{一句话点出最值得看的事}
```

**结尾**：

```
📊 统计说明
  • star 数据取自 GitHub API，截至 {日期}
  • "快速上涨" = 7 日 star 净增排序，排除总榜前 5
  • "新生项目" = 30 天内创建且 star ≥ 3，经内容相关性过滤后分双档展示
  • "活跃度"（⑤总榜🔥标签）= 近 7 天 commit 达阈值
  • 覆盖范围：关系型数据库 + 生态工具 + AI 能力

📎 数据来自 GitHub 公开 API，以官方文档及 LICENSE 文件为准。
  Search API 存在索引延迟，新建项目可能滞后数天被索引。

🗂️ 往期回顾 ｜ 👍 点赞 + 在看 ｜ 🔔 关注，下周见
```

---

## 九、完整样板（填真实数据）

> 以下为「第 01 期」完整样板，使用本对话已验证的真实 GitHub 数据（采集日 2026-08-05）。
> **首期说明**：因无 7 天前快照对比基准，①快速上涨、⑤总榜"本周变化"等动态栏目如实标注"首期"，第二周起完整。

---

# 🔖 数据库开源周报 · 第 01 期

> **每周 5 分钟，看懂 GitHub 上数据库开源生态的一手动态。**
> **本期重点：PostgreSQL 19 进入 Beta2，关系库生态年度里程碑。**

---

## ① ⭐ 快速上涨榜

> 📌 **首期说明**：本期为创刊号，尚无 7 天前快照对比基准，快速上涨榜自第 02 期起完整。本栏暂以"近 7 日有重大版本发布"的项目代替排序。

| 项目 | 近况 | 备注 |
|---|---|---|
| PostgreSQL | 发布 19 Beta2 | 主版本号变更 |
| OceanBase | 发布 4.6.0 CE | 新增向量检索 |

---

## ② 🆕 新生项目

> 口径：30 天内创建 + star ≥ 3，经内容相关性过滤后分双档展示
> 📌 本栏目不依赖快照对比（按 created_at 直接筛），首期即可完整呈现。

### 🌟 潜力榜（star ≥ 30，已发酵）

| 项目 | 作用（AI 翻译 README） | Star | 创建日 |
|---|---|---:|---|
| apitap/apitap-lib | 跨数据库快速迁移整张表，支持 Postgres/MySQL/ClickHouse/BigQuery，Rust 引擎 | 45 | 7月11日 |
| LunarDump（indhifarhandika） | 轻量级零信任 CLI，自动化加密并流式备份数据库到多云存储 | 35 | 7月29日 |
| django-orm-lens | Django schema 审查工具，检测 schema 漂移、N+1、ER 图，含 MCP server | 53 | 7月12日 |

### 🆕 新星榜（star 3 ~ 30，早期观察）

> 📌 本档为早期观察信号，仅作记录，不代表成熟可用。

| 项目 | 作用 | Star |
|---|---|---:|
| （本周新星榜样本较少，下期随采集积累补全） | — | — |

> 📌 **说明**：topic 标签由作者自填不可靠，本周已过滤掉打 postgresql 标签但与数据库无关的项目（如任务工作区、记账 app）。仅保留"本身是数据库相关"的项目。

---

> 📌 **③ 活跃度**已并入⑤总榜的 🔥 标签列，不再单独成榜（避免与其他榜重叠）。

---

## ④ ⭐ 本周重点分析

> 📌 本栏目为 AI 辅助解读，以官方文档为准。

**本周重点项目：PostgreSQL 19 Beta2**
（信号分：主版本号变更 +40 + 现有 star 影响面加权 → 本周最高）

### 1️⃣ 这个项目做什么

PostgreSQL 是开源的关系型数据库管理系统，采用 SQL 标准并支持复杂查询、外键、触发器、视图等特性。

### 2️⃣ 解决什么问题

面向需要事务一致性、复杂查询、数据完整性的应用场景，是众多数据库（含部分国产库）的内核基础。

### 3️⃣ 有哪些突出点（基于官方 release notes 转述）

- 进入 Beta2，意味着特性冻结（Feature Freeze），后续专注修复与稳定
- 正式版预计 2026 年 9-10 月（据 PostgreSQL 官方发布周期）
- 官方提及的方向：异步 I/O 改进、增量备份、SQL/JSON 增强

### 4️⃣ 为什么解读它

本周信号分最高：发布主版本号变更（Beta2，年度大版本里程碑）+ 现有 21.7k star 的影响面。PostgreSQL 是开源关系库生态的根基，其大版本动向值得关注。

📎 来源:[PostgreSQL 官方](https://www.postgresql.org) ｜ [GitHub postgres/postgres](https://github.com/postgres/postgres)

---

## ⑤ 📊 Top 总榜（含 🔥 活跃标签）

> 口径：所有项目统一按 star 降序。🔥 = 近 7 天 commit 活跃（达阈值）。
> 📌 **首期**：本周变化列暂缺，自第 02 期起标注 ↑/↓/新入榜。

| 排名 | 项目 | 品类 | Star | 活跃 |
|:--:|---|---|---:|:--:|
| 1 | TiDB | 分布式 NewSQL | 40.4k | |
| 2 | DuckDB | 嵌入式分析 | 40.0k | |
| 3 | PostgreSQL | 关系型 | 21.7k | 🔥 |
| 4 | OceanBase | 分布式关系库 | 10.2k | |
| 5 | MySQL | 关系型 | 12.4k | 🔥 |
| 6 | MariaDB | 关系型 | 8.0k | 🔥 |

📎 来源:GitHub API，采集日 2026-08-05

---

## ⑥ 📦 版本速递

> 口径：本周发版的、进候选池的项目。版本号作标题，notes AI 忠实摘要。
> 📌 首期说明：版本数据需数据源3（Releases API）周采集，本期为流程演示，版本号标"待采集"。正式期起每条为具体版本号 + 官方 notes 要点 + 出处。

### 6a 🛠️ 生态工具版本

| 工具 | 版本 | 日期 | 要点 |
|---|---|---|---|
| ProxySQL | （待采集） | — | MySQL/PG 高性能代理 |
| Patroni | （待采集） | — | PostgreSQL 高可用模板 |
| Bytebase | （待采集） | — | 跨库变更/权限治理 |
| mydumper | （待采集） | — | MySQL 多线程备份 |

> 正式期格式示例：`ProxySQL v2.7.x ｜ 8月4日 ｜ 要点：xxx`，📎 来源:[Release Notes](链接)

### 6b 🤖 AI 板块版本

| 项目 | 版本 | 日期 | 要点 |
|---|---|---|---|
| MCP Toolbox for Databases | （待采集） | — | AI agent 操作数据库的 MCP server |

> 正式期同上格式。

---

## ⑦ 🛠️ 生态工具

> 发现方式：topic + 工具关键词。归类依据项目 README 自述。以下为 AI 翻译的项目作用，不点评。

### 中间件 / 代理
- **ProxySQL** ⭐ 6.9k —— MySQL 与 PostgreSQL 的高性能代理。
- **PgBouncer** ⭐ 4.3k —— PostgreSQL 轻量连接池。

### 高可用 / 编排
- **Patroni** ⭐ 8.6k —— PostgreSQL 高可用模板，基于 Etcd/Consul/K8s。
- **postgres-operator** ⭐ 5.2k —— 在 Kubernetes 上创建和管理 PostgreSQL 集群。

### 管控 / 治理
- **Bytebase** ⭐ 14.4k —— 跨数据库的变更与访问权限治理平台。

### 迁移 / 备份
- **mydumper** ⭐ 3.2k —— MySQL 高性能多线程逻辑备份工具。

📎 来源:各项目 GitHub 仓库 README

---

## ⑧ 🤖 AI 能力专题

> 发现方式：topic + AI 关键词（llm/agent/skill/mcp/text2sql/nl2sql/copilot/ai-dba）。不分类，直接按 star 展示 top。

| 排名 | 项目 | 作用（AI 翻译 README） | Star |
|:--:|---|---|---:|
| 1 | Chat2DB | AI 驱动的多数据库 SQL 客户端，支持 MySQL/Oracle/PG/SQL Server 等 | 27.6k |
| 2 | WrenAI | 开源的 Text2SQL / GenBI，自然语言转 SQL 查询 | 16.8k |
| 3 | MCP Toolbox for Databases | AI agent 操作数据库的开源 MCP server | 16.1k |
| 4 | SQLBot（dataease） | 基于大模型和 RAG 的中文问数系统 | 6.5k |
| 5 | sqlchat | Chat 式 SQL 客户端与编辑器 | 5.8k |

📎 来源:GitHub Search API + 各项目 README

---

## ⑨ ⚖️ License 雷达

> 本期无 license 变更事件。

📎 附录：License 全景表见文末。

---

## 📌 统计口径与说明

**📊 统计口径**
- star 数据取自 GitHub API，截至 2026-08-05
- "快速上涨" = 7 日 star 净增排序，排除总榜前 5（首期无对比基准，自第 02 期起）
- "新生项目" = 30 天内创建且 star ≥ 3，经内容相关性过滤后分双档展示
- "活跃度" = 近 7 天 push/commit 频率
- 覆盖范围：关系型数据库 + 生态工具 + AI 能力

**📎 数据说明**
- 数据来自 GitHub 公开 API
- Search API 存在索引延迟，新建项目可能滞后数天被索引
- 所有版本特性、license 信息以各项目官方文档及 LICENSE 文件为准

**🗂️ 往期回顾 ｜ 👍 点赞 + 在看 ｜ 🔔 关注「数据库开源周报」，下周见**

---

## 📎 附录：License 全景表（数据：GitHub API，2026-08-05）

| 项目 | License | 类型 |
|---|---|---|
| MySQL | NOASSERTION | GPL + 商业双协议（非 OSI 标准开源） |
| MariaDB | GPL-2.0 | OSI 开源 |
| PostgreSQL | PostgreSQL License | OSI 开源（类 BSD） |
| TiDB | Apache-2.0 | OSI 宽松开源 |
| OceanBase | Apache-2.0 | OSI 宽松开源 |
| DuckDB | MIT | OSI 宽松开源 |
| CockroachDB | NOASSERTION | BSL（源码可见，非 OSI 开源） |

> 选型提示：NOASSERTION 表示该仓库采用非 OSI 认证的自定义协议，生产商用前建议阅读 LICENSE 原文确认限制条款。以上为 GitHub 仓库字段读取，详情以各项目 LICENSE 文件为准。

---

## 十、每周生产流程（SOP 执行步骤）

### 10.1 每日（外部定时器自动触发，无需人工）

```
凌晨：
  ├─ 16 个 topic 脚本各自跑（数据源 1 + 2 + 4）
  ├─ 结果落盘到 data/snapshot_{YYYYMMDD}/{topic}.json
  └─ 人工无需介入（除非告警）
```

### 10.2 每周（周报生产日，建议周四）

```
步骤 1：数据准备（30 分钟）
  ├─ 跑周报采集任务（数据源 3 release + 数据源 5 license 变更）
  ├─ diff 本周快照 vs 上周快照 → 算净增 / 新入榜 / 变化
  └─ 输出候选池 + 各榜单原始数据

步骤 2：筛选与排序（20 分钟）
  ├─ 四层漏斗过滤候选池
  ├─ 各榜单按规则排序
  └- 计算本周重点信号分 → 选出 1-2 个重点项目

步骤 3：内容生产（1-2 小时）
  ├- 榜单 / 版本 / License：直接套模板填数据
  ├- 工具 / AI 板块：AI 翻译 README 作用，人工核对
  └- 本周重点：AI 辅助生成四问初稿，人工审核（重点把关）

步骤 4：排版与发布（30 分钟）
  ├- 套公众号排版模板
  ├- 检查禁用词、来源标注、免责声明
  └- 发布

预估每周总工时：2.5-3.5 小时（首期更长，熟练后缩短）
```

### 10.3 质量检查清单（发布前必过）

```
□ 禁用词检查（最强/最快/颠覆/必将/重大/震惊...）
□ 来源标注检查（每条都有 📎 来源）
□ 免责声明在文末
□ 口径说明完整
□ 首期/特殊期的"如实说明"在位（如无对比数据）
□ 本周重点的 AI 解读已人工审核
□ 表格未折行（列数≤4，每格≤8 字）
□ 上期纠错（如有）已放开头
□ 榜单归属：每个项目只归入一个主榜（④②①⑧⑤ 五选一）
□ 被舍掉的榜单有"见XX榜"标注
□ ⑤总榜的 🔥 标签准确反映 commit 活跃度
```

---

## 附录 A：本 SOP 的演进记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-08-05 | 首版：定位、10 栏目、双层采集架构、6 类数据源、三轨信源（白名单 + org 扫描 + 搜索发现）、筛选规则、安全红线、排版模板、完整样板 |

---

## 附录 B：关键决策记录（供后期回溯）

1. **定位**：关系型数据库开源生态，国际主流为主线
2. **内容原则**：全周报零主观判断，仅本周重点栏开受控 AI 理解口子
3. **总榜**：统一 star 排序不分类，但作为背景板（动态焦点在前 4 栏）
4. **新生项目**：30 天 + star ≥ 3，内容相关性过滤，双档展示（新星榜 3-30 / 潜力榜 ≥30）
5. **版本速递**：不限内核，拆为生态工具版本 / AI 板块版本
6. **AI 板块**：不分类，直接 star top
7. **采集**：双层架构（日快照 + 周汇总），6 类数据源（含 org 全量扫描），三轨信源，全量/按需分离
8. **脚本**：每 topic 一个独立脚本，查总数→分级拆分(互斥+star档位)→动态限流→落盘
9. **License**：用 GitHub 结构化数据，只报选型影响，不解读法律
10. **信创/合规**：暂不单设栏目（用户决定）

---

**文档结束。**

> 本 SOP 将随实际生产持续迭代。建议每 4 周回顾一次：栏目是否需调整、阈值是否需校准、信号分权重是否需修正。
