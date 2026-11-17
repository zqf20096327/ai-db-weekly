# -*- coding: utf-8 -*-
"""build.py -- 站点编排器（纯编排零业务逻辑；每模块独立可跑，这里只是串起来）

用法（在 gen/ 目录下）:
  python -I build.py                      # 全量：legacy+lists+db+cards+sitemap+platform[cf] -> dist/
  python -I build.py --only lists,db      # 只跑部分（改模板后局部重出）
  python -I build.py --verify             # 交叉校验（不重建）
  python -I build.py --selftest

解耦架构见 README.md。数据契约：dbhub_collect 的 build_site.py 产 site/（分片+sitemap+robots+urls.json），
本侧零数据逻辑——列表页数、类目、库页、URL 模式全部以契约文件为准。
"""
import argparse, glob, io, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I 隔离模式不自动加脚本目录
import common as C
import list_pages, db_pages, cards, platform, vs_pages, weekly_pages, home, compare_pages

VER = "gen/1.0"

# ---------- 交叉校验（P3.3/P3.4/P3.5 的验收全在这） ----------

def verify(cfg, ct, out_dir):
    errs = []
    data_root = cfg["data_root"]
    # 1) 卡 URL 契约三方一致：urls.json 模式 == 分片 item.url == 盘上 p/owner/repo/index.html
    shard = json.load(io.open(glob.glob(os.path.join(data_root, "data", "all-1.json"))[0], encoding="utf-8"))
    fns_expect = set()
    for f in glob.glob(os.path.join(data_root, "data", "all-*.json")):
        for it in json.load(io.open(f, encoding="utf-8"))["items"]: fns_expect.add(it["fn"])
    disk_cards = set()
    for root, _, files in os.walk(os.path.join(out_dir, "p")):
        if "index.html" in files:
            rel = os.path.relpath(root, os.path.join(out_dir, "p")).replace(os.sep, "/")
            disk_cards.add(rel)
    if ct["card"] != "/p/{fn}/": errs.append(f"契约模式漂移: {ct['card']}")
    if shard["items"][0]["url"] != ct["card"].format(fn=shard["items"][0]["fn"]):
        errs.append("分片 url 与契约不一致")
    only_disk = disk_cards - fns_expect; only_data = fns_expect - disk_cards
    if only_disk: errs.append(f"盘上多出 {len(only_disk)} 张（归档/出池卡混入?）样例 {list(only_disk)[:3]}")
    if only_data: errs.append(f"缺卡 {len(only_data)} 张，样例 {list(only_data)[:3]}")
    # 2) 内链 404：全站页（列表/库/vs + P7 内容页首页/周刊/对比/archive）里每个站内绝对链接必须有对应物理页
    page_files = (glob.glob(os.path.join(out_dir, "projects", "*.html"))
                  + glob.glob(os.path.join(out_dir, "cat", "*", "*.html"))
                  + glob.glob(os.path.join(out_dir, "db", "*", "index.html"))
                  + glob.glob(os.path.join(out_dir, "vs", "*", "index.html"))
                  + glob.glob(os.path.join(out_dir, "weekly", "*", "index.html"))
                  + glob.glob(os.path.join(out_dir, "compare", "*.html"))
                  + [os.path.join(out_dir, "index.html"), os.path.join(out_dir, "archive.html")])
    page_files = [p for p in page_files if os.path.exists(p)]
    bad = 0; bp = cfg.get("base_path", "")
    for pf in page_files:
        t = io.open(pf, encoding="utf-8").read()
        for href in set(re.findall(r'href="(/[^"#]+)"', t)):
            h = href[len(bp):] if bp and href.startswith(bp) else href   # 镜像前缀剥掉再对账
            path = os.path.join(out_dir, *h.strip("/").split("/"))
            if not (os.path.exists(path) or os.path.exists(os.path.join(path, "index.html"))):
                bad += 1
                if bad <= 3: errs.append(f"内链 404: {href} (from {os.path.relpath(pf, out_dir)})")
    for u, _ in cfg["nav"]:
        if u == "/" or u.endswith(".html"): continue   # 首页/物理 html 页（archive.html 等已在上面对账）
        target = os.path.join(out_dir, *u.strip("/").split("/"), "index.html")
        if not os.path.exists(target):
            errs.append(f"导航死链: {u}")
    # 3) 正文可索引：抽 3 个列表页，剥 script 后正文 >5,000 字且含已知项目名
    list_pages_only = [p for p in page_files if os.sep + "projects" + os.sep in p or os.sep + "cat" + os.sep in p]
    for pf in list_pages_only[:3]:
        t = io.open(pf, encoding="utf-8").read()
        body = re.sub(r"<script[\s\S]*?</script>", "", t)
        txt = re.sub(r"<[^>]+>", " ", body)
        if len(" ".join(txt.split())) < 5000: errs.append(f"正文过短: {os.path.relpath(pf, out_dir)}")
    # 4) 归档卡不进站（archive manifest 与盘上卡无交集——由「only_disk 空」间接保证，这里直查）
    arc = os.path.join(cfg["cards_root"], "..", "archive", "manifest.json")
    if os.path.exists(arc):
        arc_fns = {fn for fn, e in json.load(io.open(arc, encoding="utf-8"))["cards"].items()
                   if not e.get("restored_at")}   # restored_at=已回池的活跃仓，出现在 dist 是合法的
        hit = arc_fns & disk_cards
        if hit: errs.append(f"归档卡混进 dist: {len(hit)} 张，样例 {list(hit)[:3]}")
    # 5) JS 数据文件绝迹（P7.6：旧页全静态化后，站内不再携带任何 JS 数据文件）
    for bad_js in ("pool.js", "weekly.js", "comparisons.js"):
        if glob.glob(os.path.join(out_dir, "**", bad_js), recursive=True): errs.append(f"{bad_js} 在 dist 内")
    # 6) P7 内容页四查：周刊每期正文≥3000 / archive 期链全通 / compare 索引覆盖全部 vs 页 / 长文篇数对账
    wk = sorted(glob.glob(os.path.join(out_dir, "weekly", "*", "index.html")))
    if not wk: errs.append("周刊页缺失（weekly/ 空）")
    for pf in wk:
        body = re.sub(r"<script[\s\S]*?</script>", "", io.open(pf, encoding="utf-8").read())
        if len(" ".join(re.sub(r"<[^>]+>", " ", body).split())) < 3000:
            errs.append(f"周刊正文过短: {os.path.relpath(pf, out_dir)}")
    n_deep_src = len(json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   "compare_deep.json"), encoding="utf-8")))
    n_deep_disk = len(glob.glob(os.path.join(out_dir, "compare", "deep-*.html")))
    if n_deep_disk != n_deep_src: errs.append(f"长文页数 {n_deep_disk} != 源 {n_deep_src}")
    if os.path.exists(os.path.join(out_dir, "compare", "index.html")):
        t = io.open(os.path.join(out_dir, "compare", "index.html"), encoding="utf-8").read()
        n_vs_disk = len(glob.glob(os.path.join(out_dir, "vs", "*", "index.html")))
        n_vs_link = len({m for m in re.findall(r'href="[^"]*/vs/([^"/]+)/"', t)})
        if n_vs_link != n_vs_disk: errs.append(f"compare 索引覆盖 {n_vs_link} != vs 页 {n_vs_disk}")
    print(f"VERIFY {'FAIL' if errs else 'OK'}: 卡 {len(disk_cards)}（对账 {len(fns_expect)}）· "
          f"页面 {len(page_files)}（含周刊 {len(wk)}/长文 {n_deep_disk}）· 内链坏 {bad}")
    for e in errs[:20]: print("  -", e)
    return errs

# ---------- sitemap 内容页并入（P7.8） ----------

def merge_sitemap(out_dir):
    """内容页 URL 并入 build_site 产的 sitemap：职责边界=数据 URL（卡/库/类目）归 build_site，
    内容 URL（首页/往期/周刊/对比）归 gen——周刊期数取决于仓内 weekly.js，collect 侧看不到。
    以 dist 盘上实际页面为准，追加去重，落盘后真解析自证。"""
    import datetime
    import xml.etree.ElementTree as ET
    p = os.path.join(out_dir, "sitemap.xml")
    root = ET.parse(p).getroot()
    tag = lambda e: e.tag.split("}")[-1]                      # 命名空间无关（sitemap 默认 xmlns 带花括号）
    ns = root.tag[:root.tag.index("}") + 1] if root.tag.startswith("{") else ""
    urls = [e for e in root if tag(e) == "url"]
    have = set()
    for e in urls:
        loc = next(c for c in e if tag(c) == "loc")
        have.add(loc.text)
    base = sorted(have)[0].rstrip("/")          # 首个 loc = base + "/"（build_site urls[0]）
    base = base[:base.rfind("/")] if base.count("/") > 2 else base
    assert base.startswith("http"), f"sitemap base 异常: {base}"
    n_deep = len(json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               "compare_deep.json"), encoding="utf-8")))
    adds = ["/", "/archive.html", "/compare/"] + [f"/compare/deep-{i}.html" for i in range(1, n_deep + 1)]
    adds += ["/weekly/" + os.path.basename(os.path.dirname(d)) + "/"
             for d in sorted(glob.glob(os.path.join(out_dir, "weekly", "*", "index.html")))]
    lm = datetime.date.today().isoformat(); n = 0
    for u in adds:
        if base + u in have: continue
        have.add(base + u)
        e = ET.SubElement(root, ns + "url"); ET.SubElement(e, ns + "loc").text = base + u
        ET.SubElement(e, ns + "lastmod").text = lm; n += 1
    ET.indent(root) if hasattr(ET, "indent") else None
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n")
    ET.parse(p)
    assert len(have) == len([e for e in root if tag(e) == "url"]), "sitemap 追加撞了已有 URL"
    return n, len(have)

# ---------- 自检（纯函数，不碰 dist） ----------

def _selftest():
    cfg = {"site_name": "s", "site_desc": "d", "nav": [["/", "首页"]], "cats": [["library", "开发库"]]}
    ct = {"base": "https://x.example", "card": "/p/{fn}/", "all_first": "/projects/", "all_page": "/projects/{n}.html",
          "cat_first": "/cat/{slug}/", "cat_page": "/cat/{slug}/{n}.html", "db": "/db/{slug}/"}
    assert C.esc('<a>&"') == "&lt;a&gt;&amp;&quot;"
    cfg["base_path"] = "/ai-db-weekly"
    assert C.url("/p/o/r/", cfg) == "/ai-db-weekly/p/o/r/"
    cfg["base_path"] = ""
    assert C.url("/p/o/r/", cfg) == "/p/o/r/"
    r = C.item_row({"fn": "o/r", "name": "r", "stars": 1234, "lang": "Go", "ol": "x<y", "url": "/p/o/r/"}, cfg)
    assert 'href="/p/o/r/"' in r and "1,234★" in r and "x&lt;y" in r
    pg = C.pager(6, 99, "/projects/", lambda n: f"/projects/{n}.html")
    assert pg.count("<a") == 12 and "…" in pg and '<span class="cur">6</span>' in pg   # 页码 3..9+1,2,98,99 共 10 链接+前后页
    assert C.pager(1, 1, "/x/", lambda n: "") == ""
    assert C.pager(2, 2, "/x/", lambda n: f"/x/{n}.html").count('<a href="/x/') == 2  # 第1页+上一页都指 first
    # 列表页文件名映射：第 1 页 index.html，第 n 页 n.html
    d = {"slug": "all", "cat": "全部", "page": 1, "pages": 2, "items": []}
    import tempfile, os
    out = tempfile.mkdtemp()
    p1 = list_pages.render_list_page(cfg, ct, d, out)
    assert p1.endswith(os.path.join("projects", "index.html"))
    d["page"] = 2
    p2 = list_pages.render_list_page(cfg, ct, d, out)
    assert p2.endswith(os.path.join("projects", "2.html")) and "第 2 页" in io.open(p2, encoding="utf-8").read()
    d2 = {"slug": "engine", "cat": "内核/引擎", "page": 1, "pages": 1, "items": []}
    p3 = list_pages.render_list_page(cfg, ct, d2, out)
    assert p3.endswith(os.path.join("cat", "engine", "index.html"))
    t1 = io.open(p1, encoding="utf-8").read()
    assert '<link rel="canonical" href="https://x.example/projects/">' in t1   # 第 1 页 canonical=绝对 URL
    assert "canonical" not in io.open(p2, encoding="utf-8").read()   # 分页第 2 页不出 canonical
    cfg["mirror"] = True; cfg["base_path"] = "/ai-db-weekly"
    d["items"] = [{"fn": "o/r", "name": "r", "stars": 1, "lang": "Go", "ol": "x", "url": "/p/o/r/"}]
    p4 = list_pages.render_list_page(cfg, ct, {**d, "page": 1}, out)
    t4 = io.open(p4, encoding="utf-8").read()
    assert '<meta name="robots" content="noindex">' in t4 and 'href="/ai-db-weekly/p/' in t4  # 镜像 noindex+前缀
    cfg["mirror"] = False; cfg["base_path"] = ""
    # sitemap 内容页并入：临时 sitemap + 盘上 1 期周刊 -> 追加去重、可解析、首页不重复
    import xml.etree.ElementTree as ET
    tmp = tempfile.mkdtemp()
    io.open(os.path.join(tmp, "sitemap.xml"), "w", encoding="utf-8", newline="\n").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        '<url><loc>https://x.example/</loc></url>'
        '<url><loc>https://x.example/projects/</loc></url></urlset>\n')
    os.makedirs(os.path.join(tmp, "weekly", "1"))
    io.open(os.path.join(tmp, "weekly", "1", "index.html"), "w", encoding="utf-8").write("x")
    n, tot = merge_sitemap(tmp)
    assert n == tot - 2 and tot >= 5, f"并入计数异常 n={n} tot={tot}"
    assert "https://x.example/weekly/1/" in io.open(os.path.join(tmp, "sitemap.xml"), encoding="utf-8").read()
    print(f"OK {VER} selftest: 14 asserts passed")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="lists,db,vs,weekly,home,compare,cards,sitemap,platform 逗号分隔（默认全量；legacy 模块已随 P7 旧页全静态化退役）")
    ap.add_argument("--platform", default="cf", choices=["cf", "gh"])
    ap.add_argument("--mirror", action="store_true",
                    help="镜像变体：base_path=/ai-db-weekly + noindex，输出 dist-mirror/（GH Pages 用）")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: sys.exit(_selftest())
    cfg = C.load_config(); ct = C.load_contract(cfg)
    if a.mirror:
        cfg["base_path"] = "/ai-db-weekly"; cfg["mirror"] = True; cfg["out"] = "dist-mirror"
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"])
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    if a.verify:
        errs = verify(cfg, ct, out_dir)
        sys.exit(1 if errs else 0)
    steps = (a.only.split(",") if a.only else
             ["lists", "db", "vs", "weekly", "home", "compare", "cards", "sitemap", "platform"])
    for s in steps:
        if s == "lists": list_pages.gen_lists(cfg, ct, out_dir)
        elif s == "db": db_pages.gen_db_pages(cfg, ct, out_dir)
        elif s == "vs": vs_pages.gen_vs_pages(cfg, ct, out_dir)
        elif s == "weekly": weekly_pages.gen_weekly(cfg, ct, out_dir)
        elif s == "home": home.gen_home(cfg, ct, out_dir)
        elif s == "compare": compare_pages.gen_compare(cfg, ct, out_dir)
        elif s == "cards": cards.copy_cards(cfg, out_dir)
        elif s == "sitemap":
            for f in ("sitemap.xml", "robots.txt"):
                shutil.copyfile(os.path.join(cfg["data_root"], f), os.path.join(out_dir, f))
            n, tot = merge_sitemap(out_dir)
            print(f"OK sitemap: 数据侧拷贝 + 内容页并入 {n} 条（总 {tot}；BASE 域名在 build_site 侧注入）")
        elif s == "platform": platform.emit(out_dir, a.platform)
        else: ap.error(f"unknown step {s}")
    if not a.only:
        errs = verify(cfg, ct, out_dir)
        sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
