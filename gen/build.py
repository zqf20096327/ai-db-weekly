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
import list_pages, db_pages, cards, legacy, platform

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
    # 2) 内链 404：列表/库页里每个 /p/ 链接必须有对应物理页；导航链接必须存在
    page_files = (glob.glob(os.path.join(out_dir, "projects", "*.html"))
                  + glob.glob(os.path.join(out_dir, "cat", "*", "*.html"))
                  + glob.glob(os.path.join(out_dir, "db", "*", "index.html")))
    bad = 0
    for pf in page_files:
        t = io.open(pf, encoding="utf-8").read()
        for href in set(re.findall(r'href="(/p/[^"]+)"', t)):
            if not os.path.exists(os.path.join(out_dir, *href.strip("/").split("/"), "index.html")):
                bad += 1
                if bad <= 3: errs.append(f"内链 404: {href} (from {os.path.relpath(pf, out_dir)})")
    for u, _ in cfg["nav"]:
        if u == "/": continue
        target = (os.path.join(out_dir, *u.strip("/").split("/"), "index.html") if u.endswith("/")
                  else os.path.join(out_dir, *u.strip("/").split("/")))
        if not os.path.exists(target):
            errs.append(f"导航死链: {u}")
    # 3) 正文可索引：抽 3 个列表页，剥 script 后正文 >5,000 字且含已知项目名
    for pf in page_files[:3]:
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
    # 5) pool.js 不在站内
    if glob.glob(os.path.join(out_dir, "**", "pool.js"), recursive=True): errs.append("pool.js 在 dist 内")
    print(f"VERIFY {'FAIL' if errs else 'OK'}: 卡 {len(disk_cards)}（对账 {len(fns_expect)}）· "
          f"列表/库页 {len(page_files)} · 内链坏 {bad}")
    for e in errs[:20]: print("  -", e)
    return errs

# ---------- 自检（纯函数，不碰 dist） ----------

def _selftest():
    cfg = {"site_name": "s", "site_desc": "d", "nav": [["/", "首页"]], "cats": [["library", "开发库"]]}
    ct = {"card": "/p/{fn}/", "all_first": "/projects/", "all_page": "/projects/{n}.html",
          "cat_first": "/cat/{slug}/", "cat_page": "/cat/{slug}/{n}.html", "db": "/db/{slug}/"}
    assert C.esc('<a>&"') == "&lt;a&gt;&amp;&quot;"
    r = C.item_row({"fn": "o/r", "name": "r", "stars": 1234, "lang": "Go", "ol": "x<y", "url": "/p/o/r/"})
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
    assert '<link rel="canonical" href="/projects/">' in t1          # 第 1 页 canonical
    assert "canonical" not in io.open(p2, encoding="utf-8").read()   # 分页第 2 页不出 canonical
    print(f"OK {VER} selftest: 8 asserts passed")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="legacy,lists,db,cards,sitemap,platform 逗号分隔（默认全量）")
    ap.add_argument("--platform", default="cf", choices=["cf", "gh"])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: sys.exit(_selftest())
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"])
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    if a.verify:
        errs = verify(cfg, ct, out_dir)
        sys.exit(1 if errs else 0)
    steps = (a.only.split(",") if a.only else
             ["legacy", "lists", "db", "cards", "sitemap", "platform"])
    for s in steps:
        if s == "legacy": legacy.copy_legacy(cfg, out_dir)
        elif s == "lists": list_pages.gen_lists(cfg, ct, out_dir)
        elif s == "db": db_pages.gen_db_pages(cfg, ct, out_dir)
        elif s == "cards": cards.copy_cards(cfg, out_dir)
        elif s == "sitemap":
            for f in ("sitemap.xml", "robots.txt"):
                shutil.copyfile(os.path.join(cfg["data_root"], f), os.path.join(out_dir, f))
            print("OK sitemap: sitemap.xml + robots.txt 进站（注意：BASE 域名在 build_site 侧注入）")
        elif s == "platform": platform.emit(out_dir, a.platform)
        else: ap.error(f"unknown step {s}")
    if not a.only:
        errs = verify(cfg, ct, out_dir)
        sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
