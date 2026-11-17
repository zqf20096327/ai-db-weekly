# -*- coding: utf-8 -*-
"""list_pages.py -- /projects/ 总览分页 + /cat/<slug>/ 类目分页（P7.14：恢复旧版项目浏览排版）

版面=旧 projects.html 原版静态直出（assets/app.css 设计令牌）：
  card 头部段 + fzone 淡底筛选段（数据库/类别 chips 行，静态版=导航链接非 JS 筛选）
  + 状态行 + table.rows 清单（项目/库/类别/语言/Star 五列——旧版 8 列中「本周/发版/安全」
  三列信号不进数据契约，静态版不出；口径注在页脚）+ 旧式 .pager。
/projects/ 第 1 页另带旧版招牌「冠军矩阵」（▦ 库 × 类别 每格 Star 冠军；⊙=通用工具垫底），
  数据=site/data/db 分片（构建期算死，替代旧 JS resolveRow 的静态近似）。
解耦：只认数据契约（site/data/*.json + urls.json），页数由分片文件数决定，本模块零统计逻辑。
"""
import glob, io, json, os, re, shutil, sys
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
.mx-cap { font-size: 12px; font-weight: 400; color: var(--ink); margin: 14px 0 4px; }
.mx-cap:first-child { margin-top: 0; }
table.mx { width: 100%; }
table.mx th, table.mx .cat-name { font-weight: 400; color: var(--muted); }
table.mx th a:hover, .mx .cat-name a:hover { color: var(--accent); text-decoration: underline; }
a.chip { color: var(--muted); } a.chip:hover { border-color: var(--accent); color: var(--accent); }
a.chip.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
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

# ---------- 旧版部件：chips 行 / 清单表 / pager ----------

def db_chips(cfg, on_slug=None):
    """数据库行：组标（管库/用库分组不可链）+ 17 库胶囊，链 /db/{slug}/。on_slug=当前库高亮。"""
    out = []
    for title, slugs in DB_GROUPS:
        out.append(f'<span class="grp-mark" title="{C.esc(title)}">{C.esc(title[:2])}</span>')
        for s in slugs:
            on = " on" if s == on_slug else ""
            out.append(f'<a class="chip plain{on}" href="{C.esc(C.url(f"/db/{s}/", cfg))}">{C.esc(DB_NAME.get(s, s))}'
                       f'<span class="n">{DB_CNT.get(s, "")}</span></a>')
    return "".join(out)

def cat_chips(cfg, on_slug=None):
    """类别行：全部 → /projects/，13 类别 → /cat/{slug}/（旧版角色分组标记保留）。"""
    on_all = " on" if on_slug is None else ""
    out = [f'<a class="chip plain{on_all}" href="{C.esc(C.url("/projects/", cfg))}" title="全部类别">全部</a>']
    slug_of = {name: slug for slug, name in cfg["cats"]}
    for gname, gdesc, cats in ROLE_GROUPS:
        out.append(f'<span class="grp-mark" title="{C.esc(gdesc)}">{gname}</span>')
        for c in cats:
            slug = slug_of.get(c)
            if not slug: continue                     # 该类目已归档出站（如「应用」）
            on = " on" if slug == on_slug else ""
            out.append(f'<a class="chip plain{on}" href="{C.esc(C.url(f"/cat/{slug}/", cfg))}">{C.esc(c)}</a>')
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

# ---------- 冠军矩阵（/projects/ 第 1 页；旧版 ▦ 视图的静态近似） ----------

def matrix_html(cfg, total):
    by_cat = {}                                          # (slug, cat) -> 冠军 item（db 分片已按星降序）
    for s in DB_ORDER:
        d = load_shard(os.path.join(cfg["data_root"], "data", "db", s + ".json"))
        for it in d["items"]:
            k = (s, it.get("cat"))
            if k not in by_cat:
                by_cat[k] = it
    out = []
    for gtitle, slugs in DB_GROUPS:
        cols = [s for s in slugs if s in DB_NAME]
        head = ("<tr><th>类别 \\ 库</th>"
                + "".join(f'<th><a href="{C.esc(C.url(f"/db/{s}/", cfg))}" title="{C.esc(DB_NAME[s])} 生态工具">'
                          f"{C.esc(DB_NAME[s])}</a></th>" for s in cols) + "</tr>")
        rows = ""
        for _, _, cats in ROLE_GROUPS:
            for c in cats:
                cells = ""
                any_cand = any((s, c) in by_cat for s in cols)
                if not any_cand: continue
                for s in cols:
                    it = by_cat.get((s, c))
                    if it:
                        gen = len(it.get("dbs") or []) > 1
                        nm = it["name"]
                        cells += (f'<td><a class="mc zf" href="{C.esc(C.url(it["url"], cfg))}" '
                                  f'title="{C.esc(it["fn"])}">'
                                  f'<span class="nm{" gen" if gen else ""}">{("⊙ " if gen else "") + C.esc(nm)}</span></a></td>')
                    else:
                        cells += '<td><span class="mc z0">·</span></td>'
                rows += (f'<tr><td class="cat-name"><a href="{C.esc(C.url("/cat/" + CAT_SLUG_OF.get(c, "misc") + "/", cfg))}"'
                         f' title="在清单查看「{C.esc(c)}」">{C.esc(c)}</a></td>{cells}</tr>')
        if not rows: continue
        out.append(f'<div class="mx-cap">{C.esc(gtitle)}（{len(cols)} 库）</div>'
                   f'<table class="mx">{head}{rows}</table>')
    if not out: return ""
    return (f'<div class="sec-title" style="margin:14px 0 8px"><h3>▦ 冠军看格局</h3><span class="line"></span>'
            f'<span class="muted small">库 × 类别 · 每格 Star 冠军 · ⊙ 通用工具（适配多库）· 点击进项目卡</span></div>'
            f'<div class="mx-wrap">{"".join(out)}</div>'
            f'<div class="mx-legend"><span><span class="sw" style="background:var(--accent-soft)"></span>冠军</span>'
            f'<span>⊙ 通用工具垫底</span><span>· 空格 = 该组合暂无收录</span>'
            f'<span class="muted">共 {total:,} 项活跃收录</span></div>')

# ---------- 页面 ----------

CAT_SLUG_OF = {}     # build 时填：类别名 -> slug
DB_NAME = {}         # build 时填：slug -> 显示名
DB_CNT = {}          # build 时填：slug -> 卡数副注

def _boot_maps(cfg):
    global CAT_SLUG_OF, DB_NAME, DB_CNT
    CAT_SLUG_OF = {name: slug for slug, name in cfg["cats"]}
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "db", "*.json")):
        d = load_shard(f)
        DB_NAME[d["slug"]] = d.get("db") or d["slug"]
        DB_CNT[d["slug"]] = fmt_k(d.get("count") or 0)
    assert len(DB_NAME) == len(DB_ORDER) == 17, f"库分片 {len(DB_NAME)} != 17：{sorted(DB_NAME)}"

def list_body(cfg, ct, d, out_dir, first_page=False):
    n, pages, items = d["page"], d["pages"], d["items"]
    slug = d["slug"]
    if slug == "all":
        first = ct["all_first"]; pg = lambda i: ct["all_page"].format(n=i)
        h2, cur = "项目浏览", "/projects/"
        on_slug = None
        total = 0
        for f in shard_pages(cfg["data_root"], "all"):
            total += len(load_shard(f)["items"])
    else:
        first = ct["cat_first"].format(slug=slug); pg = lambda i: ct["cat_page"].format(slug=slug, n=i)
        h2, cur = f'{d["cat"]} · 项目浏览', "/projects/"
        on_slug = slug
        total = sum(len(load_shard(f)["items"]) for f in shard_pages(cfg["data_root"], "cat", slug))
    title1 = (f"项目浏览 · {total:,} 个数据库开源项目（Star 降序）" if slug == "all"
              else f"{d['cat']}工具与开源项目大全 · 数据库项目档案")
    title = title1 if n == 1 else f"{title1}（第 {n} 页）"
    mx = matrix_html(cfg, total) if (first_page and slug == "all") else ""
    rows = "".join(row_html(it, cfg) for it in items)
    body = f"""<main>
    <section class="card">
      <div class="card-head" style="margin-bottom:2px"><h2>{C.esc(h2)}<span class="hint">共 {total:,} 项 · Star 降序 · 静态分页</span></h2></div>
      <div class="fzone">
        <div class="tagrow"><span class="glabel">数据库</span>{db_chips(cfg)}</div>
        <div class="tagrow"><span class="glabel">类别</span>{cat_chips(cfg, on_slug)}</div>
      </div>
      <div class="statline"><span class="big" title="静态分页清单 · 筛选胶囊=栏目导航">匹配 {total:,}</span>
        <span class="sub">第 {n} / {pages} 页 · 本页 {len(items)} 项</span></div>
      <hr class="divider">
{mx}
      <div class="tblwrap"><table class="rows">
        <thead><tr><th style="min-width:250px">项目</th><th>库</th><th>类别</th><th>语言</th><th class="r">Star</th></tr></thead>
        <tbody>
{rows}
        </tbody></table></div>
      {pager_old(n, pages, C.url(first, cfg), lambda i: C.url(pg(i), cfg))}
    </section>
  </main>
  <footer>清单为静态分页（旧版交互筛选已随 pool.js 退役）；「本周增星 / 最近发版 / 安全」等实时信号见各项目卡。数据每日更新。</footer>"""
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
    shards = shard_pages(data_root, "all") + [f for s, _ in cfg["cats"]
                                              for f in shard_pages(data_root, "cat", s)]
    for f in shards:
        d = load_shard(f)
        list_body(cfg, ct, d, out_dir, first_page=(d["page"] == 1 and d["slug"] == "all")); n_pages += 1
    assert n_pages == len(shards)
    print(f"OK list_pages: {n_pages} 页（/projects/ + /cat/，旧版排版；projects 首页带冠军矩阵）")
    return n_pages
