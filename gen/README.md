# gen/ 站点生成器（解耦架构约定）

## 数据流（单向，只认文件契约）

```
dbhub_collect                    dbhub_page/gen                产物
─────────────                    ─────────────                 ────
daily_cards.py（数据+卡）
build_site.py ──> site/ 契约 ──> build.py 编排 ──> dist/ ──> gh-pages 分支部署
  data/*.json（分片）              ├ list_pages.py（/projects/ /cat/）
  sitemap.xml / robots.txt        ├ db_pages.py（/db/×17）
  urls.json（URL 模式唯一权威）     ├ vs_pages.py（/vs/×545）
                                  ├ weekly_pages.py（/weekly/{n}/ + archive.html，源=仓内 data/weekly.js）
[内容源·不进数据契约]              ├ home.py（门面首页 /）
  weekly.js ─────────────────────┤ compare_pages.py（/compare/ 自选对比：索引 + 富字段分桶 assets/cmp/{指纹}/）
                                  ├ cards.py（卡→p/owner/repo/index.html 物理布局）
                                  └ platform.py（cf/gh 差异仅此一处）
```

> legacy.py 已于 P7（2026-11-17）退役：四旧页全静态化后无旧资产可搬。
> 内容源边界：weekly.js 是「内容」不是「数据」——期数由本仓内容决定，
> 不进 collect 的 site/ 契约；sitemap 里这些 URL 由 build.py merge_sitemap() 在 gen 侧并入。
> compare_deep.json（AI 对比长文源）自 P11（2026-11-24）起不再使用：用户令删「AI 对比解读」板块，
> deep 长文页下线；文件保留未删。
> /compare/ 的对比数据 = 浏览瘦索引（画像 15 键）+ site/data/cmp/ 富字段分桶（build_site 产，256 桶，
> 浏览器按 fn 的 FNV-1a 低字节取桶；分桶式三处同式：build_site.py / compare_pages.py / compare.js）。

## 七条纪律

1. **单向依赖**：gen 只读 `site/` 契约文件，禁止 import dbhub_collect 代码、禁止读其 cache/manifest 等内部文件。数据侧改字段，只改 build_site 出口格式。
2. **模板零数据，数据零样式**：页面上有什么数据由分片决定；页面长什么样只在 common.py（壳）/各页模块。改样式=改 common.py 重跑 `--only lists,db`。
3. **URL 模式唯一权威 = site/urls.json**（build_site 产）。common 不写死路径模式；gen_card 的 canonical（dbhub_collect 侧）与之同步，`build.py --verify` 交叉比对防漂移。
4. **平台差异只准出现在 platform.py**。卡 URL 用物理目录 `p/owner/repo/index.html` 而非 _redirects——换托管零改动；_headers 仅 CF 生效，GH 自动忽略。
5. **模块独立可跑**：`build.py --only lists` 只重出列表；每模块可单测；build.py 纯编排零业务逻辑。
6. **卡内容单一真源 = gen_card.py**（dbhub_collect 侧）。站点层对卡 HTML 零改写零重排，只搬运。
7. **源码与产物分离**：main 分支=生成器+旧页源码；gh-pages 分支=纯 dist 产物。main 永不放生成产物。

## 常用命令

```bash
cd gen
python -I build.py --selftest       # 14 断言（纯函数）
python -I build.py                  # 全量 -> ../dist/ + VERIFY（卡对账/内链 404/正文长度/归档混入/JS 数据文件绝迹/周刊长文对比四查）
python -I build.py --only lists,db  # 改模板后局部重出
python -I build.py --verify         # 只校验不重建
```

## 已知取舍

- 列表页第 2 页起不输出 canonical（各页内容互异，非重复页）；
- 库页封顶 500 热门（长尾走类目页，防单页过重）；
- 卡片 JSON 不进站（站上只需要 HTML；底稿留在 dbhub_collect）；
- sitemap 的绝对域名由 build_site 的 DBHUB_SITE_BASE 注入，部署定域名后重出一次再进站。
