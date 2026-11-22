# -*- coding: utf-8 -*-
"""list_pages.py -- /projects/ 总览分页 + /cat/<slug>/ 类目分页（P7.14 旧版排版；P9.2 浏览页改版）

/projects/ 浏览页（P9.2，用户裁定 11-21）：
  去冠军矩阵；fzone 五行筛选（搜索/数据库/语言/属性/功能——筛选集照抄旧 pool.js 版 projects.html，
  属性=维护健康/疑似停维+官方/社区+有安全通告+AI+Star 下限；「弃用/归档」砍掉=归档仓已被卡管线
  挡在站外，恒 0 结果；「高危」改「有安全通告」=severity 已不在管线，宽口径老实标）；
  结果=卡片网格（默认）+ table.rows 清单双静态直出，纯 CSS 单选切换（零 JS 可用）；
  JS 增强层（assets/browse.js + assets/browse-{指纹}.json 瘦索引）异步接管筛选/排序/客户端翻页——
  与旧 pool.js 的本质区别：数据不进 HTML、异步取、指纹长缓存，无 JS/爬虫拿到完整静态清单。
/cat/ 类目分页维持 P7.14 原样（fzone 两行导航 chips + table.rows + 旧式 .pager）。
解耦：只认数据契约（site/data/*.json + urls.json），页数由分片文件数决定，本模块零统计逻辑。
"""
import glob, gzip, hashlib, io, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

# ---------- 旧版页内补充样式（原样搬自 projects.html <style>，只留用到的） ----------

FZONE_CSS = """\
.card-head { align-items: center; }
.fzone { background: var(--bg); border-radius: 10px; padding: 8px 12px 10px;
         display: grid; gap: 8px; margin-top: 10px; }
.divider { border: 0; border-top: 1px solid var(--line); margin: 14px 0 10px; }
.grp-sep { align-self: stretch; border-left: 1px solid var(--line); margin: 0 2px; }
.fzone .grp-mark { display: inline-flex; align-items: center; font-size: 12px;
  font-weight: 400; color: var(--accent); padding: 2px 10px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--card);
  cursor: default; margin: 0 2px 0 4px; letter-spacing: 0; }
.chip.plain { background: var(--card); }
.statline { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 12px 0 0; }
.statline .big { font-size: 16px; font-weight: 700; color: var(--ink); cursor: help; }
.statline .sub { font-size: 12px; color: var(--muted); cursor: help; }
a.chip { color: var(--muted); } a.chip:hover { border-color: var(--accent); color: var(--accent); }
a.chip.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
"""

# ---------- 浏览页补充样式（P9.2：JS 行渐进显示 / 纯 CSS 视图切换 / 卡片网格自适应） ----------

BROWSE_CSS = """\
html:not(.js) .jsonly { display: none !important; }       /* 增强行：JS 跑起来才出现，无 JS 不见空控件 */
.vh { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.fzone button.chip { color: var(--muted); font: inherit; }
.ctl#q { height: 28px; max-width: 340px; flex: 1 1 220px; }
.seg label.vl { padding: 2px 12px; font-size: 12px; cursor: pointer; color: var(--muted); }
.seg label.vl + label.vl { border-left: 1px solid var(--line); }
.seg label.vl:hover { color: var(--accent); }
#bv-card:checked ~ .vtools label[for="bv-card"],
#bv-list:checked ~ .vtools label[for="bv-list"] { background: var(--accent-soft); color: var(--accent); }
#bv-card:checked ~ #listwrap { display: none; }            /* 视图切换纯 CSS（无 JS 可用） */
#bv-list:checked ~ .pcgrid { display: none; }
.pcgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; margin-top: 12px; }
a.pcard { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; min-width: 0;
  border: 1px solid var(--line); border-radius: 10px; background: var(--card);
  color: var(--ink); text-decoration: none; }
a.pcard:hover { border-color: var(--accent); }
.pc-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; min-width: 0; }
.pc-name { font-weight: 600; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
a.pcard:hover .pc-name { color: var(--accent); }
.pc-stars { font-size: 12px; color: var(--muted); flex: none; }
.pc-ol { font-size: 12px; color: var(--muted); line-height: 1.5; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 36px; }
.pc-meta { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-top: auto; }
.pc-lang { font-size: 11px; color: var(--muted); margin-left: auto; padding-left: 8px; white-space: nowrap; }
"""

# 17 库显示顺序（国际 7 + 国产 10，与旧版 DBS 数组同构；显示名以分片 db 字段为准）
DB_ORDER = (["postgresql", "mysql", "sqlite", "mariadb", "clickhouse", "oracle", "sql-server"]
            + ["tidb", "oceanbase", "opengauss", "polardb", "gaussdb", "goldendb",
               "dameng", "gbase", "tdsql", "yashandb"])
DB_GROUPS = [("国外数据库", DB_ORDER[:7]), ("国产数据库", DB_ORDER[7:])]
# 旧版角色分组（管库/用库/造库）；「综合」兜底接在末位（旧版「其他」已归档出站）
ROLE_GROUPS = [("管库", "运维与治理 · 备份/监控/高可用/安全/迁移/管理/平台",
                ["备份", "监控", "高可用", "安全/审计", "迁移", "管理", "平台"]),
               ("用库", "开发与应用 · 驱动/ORM/建模/代理",
                ["开发库", "建模/设计", "连接/代理"]),
               ("造库", "内核与质量 · 引擎/内核 与 测试/基准",
                ["内核/引擎", "测试/质量"])]

def load_shard(p):
    return json.load(io.open(p, encoding="utf-8"))

def shard_pages(data_root, kind, slug=None):
    """返回有序分片路径列表。kind='all' -> all-N.json；kind='cat' -> cat/{slug}-N.json"""
    if kind == "all":
        fs = glob.glob(os.path.join(data_root, "data", "all-*.json"))
    else:
        fs = glob.glob(os.path.join(data_root, "data", "cat", f"{slug}-*.json"))
    return sorted(fs, key=lambda f: int(os.path.basename(f).rsplit("-", 1)[1].split(".")[0]))

# ---------- 库×类别 组合分箱（P8.2；数据源=all 分片全量——db 分片封顶 500 热门不够切） ----------

def combo_bins(items, db_slug_of, cat_slug_of):
    """item 进 (库slug, 类别slug) 桶，每桶 Star 降序。纯函数：两个映射由调用方传入
    （{库显示名:slug}、{类别名:slug}）；类别/库名对不上的 item 跳过（数据漂移归清单页兜底，
    漏多少由 verify 对账抓）。一卡多库=进多桶（与库页口径一致）。"""
    bins = {}
    for it in items:
        c = cat_slug_of.get(it.get("cat") or "")
        if c is None: continue
        for d in it.get("dbs") or []:
            s = db_slug_of.get(d)
            if s is None: continue
            bins.setdefault((s, c), []).append(it)
    for v in bins.values():
        v.sort(key=lambda x: -(x.get("stars") or 0))
    return bins

def chunk_items(items, size):
    """组合页分页切块：与 build_site 分片同口径（cfg.page_size=100）。"""
    return [items[i:i + size] for i in range(0, len(items), size)] or [[]]

# ---------- 旧版部件：chips 行 / 清单表 / pager ----------

def db_chips(cfg, on_slug=None, via_cat=None, combos=None, browse=False):
    """数据库行：组标（管库/用库分组不可链）+ 17 库胶囊全量（旧款，含收录徽标），链 /db/{slug}/。
    on_slug=当前库高亮。via_cat+combos=钻取态（P8）：链 /db/{s}/{via_cat}/ 组合页，
    空组合回落 /db/{s}/（永不 404）；两参缺省=旧行为不变。
    browse=True（P9.2 浏览页）：全库 .on（默认全选）+ data-db=显示名（JS 筛选匹配 item.dbs 用）。"""
    out = []
    for title, slugs in DB_GROUPS:
        out.append(f'<span class="grp-mark" title="{C.esc(title)}">{C.esc(title[:2])}</span>')
        for s in slugs:
            on = " on" if (s == on_slug or browse) else ""
            href = f"/db/{s}/"
            if via_cat is not None and combos and (s, via_cat) in combos:
                href = f"/db/{s}/{via_cat}/"
            extra = f' data-db="{C.esc(DB_NAME.get(s, s))}"' if browse else ""
            out.append(f'<a class="chip plain{on}"{extra} href="{C.esc(C.url(href, cfg))}">{C.esc(DB_NAME.get(s, s))}'
                       f'<span class="n">{DB_CNT.get(s, "")}</span></a>')
    return "".join(out)

def cat_chips(cfg, on_slug=None, via_db=None, combos=None, browse=False):
    """类别行：全部 → /projects/，12 类别 → /cat/{slug}/（旧版角色分组标记保留）。
    on_slug=当前类别高亮。via_db+combos=钻取态（P8）：链 /db/{via_db}/{slug}/ 组合页，
    空组合回落 /cat/{slug}/；两参缺省=旧行为不变。
    browse=True（P9.2 浏览页，行标改「功能」）：全部+全类别 .on（默认全选）+ data-cat=中文类名。"""
    on_all = " on" if (on_slug is None or browse) else ""
    out = [f'<a class="chip plain{on_all}" data-cat="" href="{C.esc(C.url("/projects/", cfg))}" title="全部类别">全部</a>']
    slug_of = {name: slug for slug, name in cfg["cats"]}
    for gname, gdesc, cats in ROLE_GROUPS:
        out.append(f'<span class="grp-mark" title="{C.esc(gdesc)}">{gname}</span>')
        for c in cats:
            slug = slug_of.get(c)
            if not slug: continue                     # 该类目已归档出站（如「应用」）
            on = " on" if (slug == on_slug or browse) else ""
            href = f"/cat/{slug}/"
            if via_db is not None and combos and (via_db, slug) in combos:
                href = f"/db/{via_db}/{slug}/"
            extra = f' data-cat="{C.esc(c)}"' if browse else ""
            out.append(f'<a class="chip plain{on}"{extra} href="{C.esc(C.url(href, cfg))}">{C.esc(c)}</a>')
    return "".join(out)

def db_tags(it):
    l = it.get("dbs") or []
    shown = "".join(f'<span class="tag">{C.esc(x)}</span>' for x in l[:3])
    return shown + (f'<span class="tag gray">+{len(l)-3}</span>' if len(l) > 3 else "")

def fmt_k(n):
    if not isinstance(n, int): return "—"
    return f"{n//1000}k" if n >= 1000 else str(n)

def row_html(it, cfg):
    stars = f'{it["stars"]:,}' if isinstance(it.get("stars"), int) else "—"
    return (f'<tr><td><a class="repo" href="{C.esc(C.url(it["url"], cfg))}">{C.esc(it["fn"])}</a>'
            f'<div class="sub">{C.esc(it.get("ol") or "") or "<span class=muted>（无描述）</span>"}</div></td>'
            f'<td>{db_tags(it)}</td>'
            f'<td class="small">{C.esc(it.get("cat") or "—")}</td>'
            f'<td class="small mono">{C.esc(it.get("lang") or "—")}</td>'
            f'<td class="r mono">{stars}</td></tr>')

def pager_old(cur, pages, first_url, page_url):
    """旧版 pagerHtml 静态版：‹上一页 + 1 2 …当前±2… 末两页 + 下一页› + 页码副注行。"""
    if pages <= 1: return ""
    want = []
    if pages <= 9:
        want = list(range(1, pages + 1))
    else:
        want = [1, 2]
        if cur > 4: want.append("…")
        want += list(range(max(3, cur - 2), min(pages - 2, cur + 2) + 1))
        if cur < pages - 3: want.append("…")
        want += [pages - 1, pages]
    parts = []
    if cur > 1:
        parts.append(f'<a href="{C.esc(first_url if cur == 2 else page_url(cur - 1))}">‹ 上一页</a>')
    else:
        parts.append('<span class="gap">‹ 上一页</span>')
    for w in want:
        if w == "…":
            parts.append('<span class="gap">…</span>')
        elif w == cur:
            parts.append(f'<span class="cur">{w}</span>')
        else:
            parts.append(f'<a href="{C.esc(first_url if w == 1 else page_url(w))}">{w}</a>')
    if cur < pages:
        parts.append(f'<a href="{C.esc(page_url(cur + 1))}">下一页 ›</a>')
    else:
        parts.append('<span class="gap">下一页 ›</span>')
    return f'<div class="pager">{"".join(parts)}</div>'

# ---------- 冠军矩阵已下线（P9.2 用户裁定「冠军格局不要了」；180 组合页入口仍在 chips 钻取） ----------

def card_tile(it, cfg):
    """P9.2 浏览页卡片瓦片（紧凑版；网格 auto-fill 自适应铺满）。样式见 BROWSE_CSS。"""
    stars = fmt_k(it["stars"]) if isinstance(it.get("stars"), int) else "—"
    cat = f'<span class="tag">{C.esc(it["cat"])}</span>' if it.get("cat") else ""
    return (f'<a class="pcard" href="{C.esc(C.url(it["url"], cfg))}">'
            f'<div class="pc-top"><span class="pc-name" title="{C.esc(it["fn"])}">{C.esc(it["name"])}</span>'
            f'<span class="pc-stars mono">{stars}★</span></div>'
            f'<div class="pc-ol">{C.esc(it.get("ol") or "") or "&nbsp;"}</div>'
            f'<div class="pc-meta">{db_tags(it)}{cat}'
            f'<span class="pc-lang">{C.esc(it.get("lang") or "")}</span></div></a>')

# ---------- 页面 ----------

DB_NAME = {}         # build 时填：slug -> 显示名
DB_CNT = {}          # build 时填：slug -> 卡数副注

def _boot_maps(cfg):
    global DB_NAME, DB_CNT
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "db", "*.json")):
        d = load_shard(f)
        DB_NAME[d["slug"]] = d.get("db") or d["slug"]
        DB_CNT[d["slug"]] = fmt_k(d.get("count") or 0)
    assert len(DB_NAME) == len(DB_ORDER) == 17, f"库分片 {len(DB_NAME)} != 17：{sorted(DB_NAME)}"

def _browse_body(cfg, ct, d, out_dir):
    """/projects/ 浏览页（P9.2）。五行筛选（搜索/数据库/语言/属性/功能，筛选集=旧 pool.js 版照抄）
    + 卡片网格/清单双静态直出（纯 CSS 单选切换）+ 静态 pager；JS 增强层资产在页尾注入
    （browse.json 指纹名 + browse.js?v=md5），缺失时不注标签页照常静态可用。"""
    n, pages, items = d["page"], d["pages"], d["items"]
    first = ct["all_first"]; pg = lambda i: ct["all_page"].format(n=i)
    total = sum(len(load_shard(f)["items"]) for f in shard_pages(cfg["data_root"], "all"))
    a = cfg.get("browse_attr") or {}
    lang_chips = "".join(
        f'<button type="button" class="chip plain" data-lang="{C.esc(lg)}">{C.esc(lg)}'
        f'<span class="n">{fmt_k(c)}</span></button>' for lg, c in cfg.get("browse_langs") or [])
    rows = "".join(row_html(it, cfg) for it in items)
    cards = "".join(card_tile(it, cfg) for it in items)
    bj, jv = cfg.get("browse_json") or "", cfg.get("browse_js_v") or ""
    scripts = (f'\n<script>window.BR={{base:{json.dumps(cfg.get("base_path", ""))},idx:{json.dumps(bj)},pgsz:24}};</script>\n'
               f'<script src="{C.esc(C.url("/assets/browse.js", cfg))}?v={jv}" defer></script>') if bj and jv else ""
    title1 = f"项目浏览 · {total:,} 个数据库开源项目（Star 降序）"
    title = title1 if n == 1 else f"{title1}（第 {n} 页）"
    body = f"""<main>
    <script>document.documentElement.classList.add("js")</script>
    <section class="card">
      <div class="card-head" style="margin-bottom:2px"><h2>项目浏览<span class="hint">共 {total:,} 项 · 卡片 / 清单 · Star 降序</span></h2></div>
      <div class="fzone">
        <div class="tagrow jsonly" style="align-items:center"><span class="glabel">搜索</span>
          <input class="ctl" id="q" type="text" autocomplete="off" spellcheck="false"
                 placeholder="搜索项目名 / 描述…（实时过滤，与筛选叠加）" aria-label="搜索当前列表">
        </div>
        <div class="tagrow"><span class="glabel">数据库</span>{db_chips(cfg, browse=True)}</div>
        <div class="tagrow jsonly"><span class="glabel">语言</span>
          <button type="button" class="chip plain on" data-lang="">全部</button>{lang_chips}</div>
        <div class="tagrow jsonly"><span class="glabel">属性</span>
          <button type="button" class="chip plain" data-mnt="ok">健康<span class="n">{a.get("ok", 0):,}</span></button>
          <button type="button" class="chip plain" data-mnt="stale">疑似停维<span class="n">{a.get("stale", 0):,}</span></button>
          <span class="grp-sep"></span>
          <button type="button" class="chip plain" data-off="1">官方<span class="n">{a.get("off", 0):,}</span></button>
          <button type="button" class="chip plain" data-off="0">社区<span class="n">{max(total - a.get("off", 0), 0):,}</span></button>
          <span class="grp-sep"></span>
          <button type="button" class="chip plain" data-sec="1">有安全通告<span class="n">{a.get("sec", 0):,}</span></button>
          <span class="grp-sep"></span>
          <button type="button" class="chip plain" data-ai="1">AI<span class="n">{a.get("ai", 0):,}</span></button>
          <span class="grp-sep"></span>
          <select class="ctl" id="f-st" title="Star 下限">
            <option value="0">Star≥ 0</option><option value="10">Star≥ 10</option>
            <option value="100">Star≥ 100</option><option value="1000">Star≥ 1k</option>
            <option value="10000">Star≥ 10k</option>
          </select>
        </div>
        <div class="tagrow"><span class="glabel">功能</span>{cat_chips(cfg, browse=True)}</div>
        <div class="tagrow jsonly"><span class="glabel">排序</span>
          <span class="seg" id="sort-seg"><span class="on" data-sort="stars" title="按项目总 Star 排名">Star</span><span data-sort="created" title="按仓库创建时间倒序">最新创建</span><span data-sort="pushed" title="按最近推送时间倒序">最近推送</span><span data-sort="relpub" title="按最近发版时间倒序">最近发版</span></span>
        </div>
      </div>
      <div class="statline"><span class="big" id="match-n" title="JS 开启后实时筛选；无 JS 时胶囊=栏目导航">匹配 {total:,}</span>
        <span class="sub" id="match-sub">第 {n} / {pages} 页 · 本页 {len(items)} 项 · 全量 Star 降序</span></div>
      <hr class="divider">
      <input type="radio" name="bview" id="bv-card" class="vh" checked>
      <input type="radio" name="bview" id="bv-list" class="vh">
      <div class="srow vtools">
        <span class="seg vsw"><label for="bv-card" class="vl">▦ 卡片</label><label for="bv-list" class="vl">☰ 清单</label></span>
        <button type="button" class="btn jsonly" id="jreset" hidden title="恢复默认筛选（全选 · Star 降序）">↺ 重置</button>
        <span class="sp"></span>
        <span class="sub jsonly" id="jnote" hidden></span>
      </div>
      <div class="pcgrid" id="cards">
{cards}
      </div>
      <div class="tblwrap" id="listwrap"><table class="rows">
        <thead><tr><th style="min-width:250px">项目</th><th>库</th><th>类别</th><th>语言</th><th class="r">Star</th></tr></thead>
        <tbody>
{rows}
        </tbody></table></div>
      <div id="spager">{pager_old(n, pages, C.url(first, cfg), lambda i: C.url(pg(i), cfg))}</div>
      <div class="pager" id="jpager" hidden></div>
    </section>
  </main>
  <footer>清单为静态直出（可收录，无 JS 完整浏览）；卡片/清单切换与多选筛选是渐进增强。数据每日更新。</footer>{scripts}"""
    rel = first if n == 1 else pg(n)
    p = os.path.join(out_dir, *rel.lstrip("/").split("/")[:-1],
                     "index.html" if n == 1 else f"{n}.html")
    C.dump(p, C.page_legacy(cfg, title, cfg["site_desc"],
                            ct["base"] + first if n == 1 else None, body, "/projects/",
                            FZONE_CSS + BROWSE_CSS))
    return p

def list_body(cfg, ct, d, out_dir, first_page=False, bins=None):
    n, pages, items = d["page"], d["pages"], d["items"]
    slug = d["slug"]
    if slug == "all":
        return _browse_body(cfg, ct, d, out_dir)     # P9.2：浏览页独立版面（first_page 参数随之退役）
    else:
        first = ct["cat_first"].format(slug=slug); pg = lambda i: ct["cat_page"].format(slug=slug, n=i)
        h2, cur = f'{d["cat"]} · 项目浏览', "/projects/"
        on_slug = slug
        total = sum(len(load_shard(f)["items"]) for f in shard_pages(cfg["data_root"], "cat", slug))
    title1 = f"{d['cat']}工具与开源项目大全 · 数据库项目档案"
    title = title1 if n == 1 else f"{title1}（第 {n} 页）"
    rows = "".join(row_html(it, cfg) for it in items)
    body = f"""<main>
    <section class="card">
      <div class="card-head" style="margin-bottom:2px"><h2>{C.esc(h2)}<span class="hint">共 {total:,} 项 · Star 降序 · 静态分页</span></h2></div>
      <div class="fzone">
        <div class="tagrow"><span class="glabel">数据库</span>{db_chips(cfg, via_cat=slug, combos=bins)}</div>
        <div class="tagrow"><span class="glabel">类别</span>{cat_chips(cfg, on_slug)}</div>
      </div>
      <div class="statline"><span class="big" title="静态分页清单 · 筛选胶囊=栏目导航">匹配 {total:,}</span>
        <span class="sub">第 {n} / {pages} 页 · 本页 {len(items)} 项</span></div>
      <hr class="divider">
      <div class="tblwrap"><table class="rows">
        <thead><tr><th style="min-width:250px">项目</th><th>库</th><th>类别</th><th>语言</th><th class="r">Star</th></tr></thead>
        <tbody>
{rows}
        </tbody></table></div>
      {pager_old(n, pages, C.url(first, cfg), lambda i: C.url(pg(i), cfg))}
    </section>
  </main>
  <footer>{C.esc(d["cat"])}清单为静态分页；实时筛选请用 <a href="{C.esc(C.url("/projects/", cfg))}">项目浏览</a>。数据每日更新。</footer>"""
    rel = first if n == 1 else pg(n)
    p = os.path.join(out_dir, *rel.lstrip("/").split("/")[:-1],
                     "index.html" if n == 1 else f"{n}.html")
    C.dump(p, C.page_legacy(cfg, title, cfg["site_desc"],
                            ct["base"] + first if n == 1 else None, body, cur, FZONE_CSS))
    return p

def gen_lists(cfg, ct, out_dir):
    _boot_maps(cfg)
    for d in ("projects", "cat"):                                    # 全量重写前清场（分片数变了旧页会残留）
        shutil.rmtree(os.path.join(out_dir, d), ignore_errors=True)
    data_root = cfg["data_root"]; n_pages = 0
    items_all = load_all_items(cfg)
    bins = combo_bins(items_all, {v: k for k, v in DB_NAME.items()},
                      {name: slug for slug, name in cfg["cats"]})    # P8.4：类目页库行钻取（矩阵已下线）
    write_browse(cfg, items_all, out_dir)                            # P9.1：浏览索引（数据同源一次摊平）
    lc = {}                                                          # P9.2：语言 Top8 + 属性计数（chips 服务端算死）
    for it in items_all:
        if it.get("lang"): lc[it["lang"]] = lc.get(it["lang"], 0) + 1
    cfg["browse_langs"] = sorted(lc.items(), key=lambda x: (-x[1], x[0]))[:8]
    ab = {"ok": 0, "stale": 0, "off": 0, "sec": 0, "ai": 0}
    for it in items_all:
        ab[it.get("mnt") or "ok"] += 1; ab["off"] += it.get("off") or 0
        ab["sec"] += it.get("sec") or 0; ab["ai"] += it.get("ai") or 0
    cfg["browse_attr"] = ab
    _js = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "browse.js"))
    cfg["browse_js_v"] = hashlib.md5(io.open(_js, "rb").read()).hexdigest()[:8] if os.path.exists(_js) else ""
    shards = shard_pages(data_root, "all") + [f for s, _ in cfg["cats"]
                                              for f in shard_pages(data_root, "cat", s)]
    for f in shards:
        d = load_shard(f)
        list_body(cfg, ct, d, out_dir, bins=bins); n_pages += 1
    assert n_pages == len(shards)
    print(f"OK list_pages: {n_pages} 页（/projects/ 浏览页五行筛选+双视图；/cat/ 维持旧版两行）")
    return n_pages

# ---------- 库×类别 组合页（P8.3：/db/{库}/{类别}/，10 条/页，chips 旧款全量+钻取回落） ----------

COMBO_PAGE_SIZE = 10     # 用户裁定（11-20）：组合清单每页最多 10 条，后面翻页

def load_all_items(cfg):
    """all 分片全量摊平（组合分箱数据源；db 分片封顶 500 热门不够切）。"""
    items = []
    for f in shard_pages(cfg["data_root"], "all"):
        items += load_shard(f)["items"]
    return items

def _combo_page(cfg, ct, ds, cs, db_disp, cname, chunk, n, pages, total, out_dir, bins):
    first = f"/db/{ds}/{cs}/"
    rows = "".join(row_html(it, cfg) for it in chunk)
    body = f"""<main>
    <section class="card">
      <div class="card-head" style="margin-bottom:2px"><h2>{C.esc(db_disp)} · {C.esc(cname)}<span class="hint">共 {total:,} 项 · Star 降序 · 静态分页</span></h2></div>
      <div class="fzone">
        <div class="tagrow"><span class="glabel">数据库</span>{db_chips(cfg, on_slug=ds, via_cat=cs, combos=bins)}</div>
        <div class="tagrow"><span class="glabel">类别</span>{cat_chips(cfg, on_slug=cs, via_db=ds, combos=bins)}</div>
      </div>
      <div class="statline"><span class="big" title="{C.esc(db_disp)}{C.esc(cname)}组合清单">匹配 {total:,}</span>
        <span class="sub">第 {n} / {pages} 页 · 本页 {len(chunk)} 项</span></div>
      <hr class="divider">
      <div class="tblwrap"><table class="rows">
        <thead><tr><th style="min-width:250px">项目</th><th>库</th><th>类别</th><th>语言</th><th class="r">Star</th></tr></thead>
        <tbody>
{rows}
        </tbody></table></div>
      {pager_old(n, pages, C.url(first, cfg), lambda i: C.url(f"/db/{ds}/{cs}/{i}.html", cfg))}
    </section>
  </main>
  <footer>{C.esc(db_disp)} {C.esc(cname)}工具清单 · 一卡可跨多库（计入多库组合）· 数据每日更新。</footer>"""
    title1 = f"{db_disp} {cname}工具大全 · {total} 个开源项目"
    title = title1 if n == 1 else f"{title1}（第 {n} 页）"
    segs = (first if n == 1 else f"/db/{ds}/{cs}/{n}.html").lstrip("/").split("/")
    p = os.path.join(out_dir, *segs[:-1], "index.html") if n == 1 else os.path.join(out_dir, *segs)
    C.dump(p, C.page_legacy(cfg, title, f"{db_disp} {cname}开源项目清单 {total} 个：Star 降序，含开发、管理与运维工具。",
                            ct["base"] + first if n == 1 else None, body, "/projects/", FZONE_CSS))

def gen_combo_pages(cfg, ct, out_dir, bins=None):
    """180 组合 → /db/{库}/{类别}/（10 条/页）。由 gen_db_pages 尾部调用：rmtree db/ 在其开头，
    清场免费（独立 step 会有页数收缩残留死页）。bins 可由调用方传入免重算。"""
    if bins is None:
        bins = combo_bins(load_all_items(cfg), {v: k for k, v in DB_NAME.items()},
                          {name: slug for slug, name in cfg["cats"]})
    n_pages = 0
    for ds in DB_ORDER:
        db_disp = DB_NAME.get(ds, ds)
        for cs, cname in cfg["cats"]:
            v = bins.get((ds, cs))
            if not v: continue
            pages = chunk_items(v, COMBO_PAGE_SIZE)
            for i, chunk in enumerate(pages, 1):
                _combo_page(cfg, ct, ds, cs, db_disp, cname, chunk, i, len(pages), len(v), out_dir, bins)
                n_pages += 1
    assert n_pages == sum(len(chunk_items(v, COMBO_PAGE_SIZE)) for v in bins.values())
    print(f"OK combo_pages: {len(bins)} 组合 {n_pages} 页（{COMBO_PAGE_SIZE} 条/页）-> /db/{{库}}/{{类别}}/")
    return n_pages

COMBO_SITEMAP_MIN = 10   # 用户裁定（11-20）：组合 ≥10 项才进 sitemap；小组合照常生成、chips 可达，防薄内容稀释

# ---------- 浏览索引（P9.1：/projects/ JS 增强层的数据源，独立于组合分箱） ----------

BROWSE_FIELDS = ("fn", "stars", "lang", "cat", "dbs", "ol", "mnt", "off", "sec", "ai",
                 "created", "pushed", "relpub")   # name/url 客户端从 fn 推导，不重复携带省体积

def write_browse(cfg, items, out_dir):
    """合并全量 items → assets/browse-{指纹前10}.json（紧凑单行数组；指纹文件名天然长缓存）。
    与组合分箱同源（gen_lists 里 load_all_items 算一次两用）；写前清旧指纹防堆积。
    性质≠旧 pool.js：本文件只被 /projects/ 的增强 JS 异步 fetch，任何页面不阻塞、不进正文。"""
    import hashlib, gzip as _gz
    data = json.dumps([{k: it.get(k) for k in BROWSE_FIELDS} for it in items],
                      ensure_ascii=False, separators=(",", ":"))
    fp = hashlib.md5(data.encode("utf-8")).hexdigest()[:10]
    adir = os.path.join(out_dir, "assets"); os.makedirs(adir, exist_ok=True)
    name = f"browse-{fp}.json"
    io.open(os.path.join(adir, name), "w", encoding="utf-8", newline="\n").write(data)
    for old in glob.glob(os.path.join(adir, "browse-*.json")):
        if os.path.basename(old) != name: os.remove(old)
    cfg["browse_json"] = name
    print(f"OK browse: {len(items)} 项 -> assets/{name}"
          f"（{len(data) // 1024} KB / gzip {len(_gz.compress(data.encode('utf-8'))) // 1024} KB）")
    return name

def combo_sitemap_urls(cfg):
    """组合首页 URL 清单（P8.5，给 build.merge_sitemap 并入）：与盘上页面同源同序，≥10 项门槛。"""
    _boot_maps(cfg)
    bins = combo_bins(load_all_items(cfg), {v: k for k, v in DB_NAME.items()},
                      {name: slug for slug, name in cfg["cats"]})
    return [f"/db/{ds}/{cs}/" for ds in DB_ORDER for cs, _ in cfg["cats"]
            if len(bins.get((ds, cs)) or []) >= COMBO_SITEMAP_MIN]
