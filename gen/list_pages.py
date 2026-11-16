# -*- coding: utf-8 -*-
"""list_pages.py -- /projects/ 总览分页 + /cat/<slug>/ 类目分页（读 site/data 分片，构建期全静态）

解耦：只认数据契约（site/data/*.json + urls.json），不知道 dbhub_collect 内部结构；
     页数由分片文件数决定，本模块零统计逻辑。
"""
import glob, io, json, os, shutil
import common as C

def load_shard(p):
    return json.load(io.open(p, encoding="utf-8"))

def shard_pages(data_root, kind, slug=None):
    """返回有序分片路径列表。kind='all' -> all-N.json；kind='cat' -> cat/{slug}-N.json"""
    if kind == "all":
        fs = glob.glob(os.path.join(data_root, "data", "all-*.json"))
    else:
        fs = glob.glob(os.path.join(data_root, "data", "cat", f"{slug}-*.json"))
    return sorted(fs, key=lambda f: int(os.path.basename(f).rsplit("-", 1)[1].split(".")[0]))

def render_list_page(cfg, ct, d, out_dir):
    """一个分片 -> 一个静态页。第 1 页落 {first}/index.html（干净 URL），其余 {first}/{n}.html。
    标题纪律：第 1 页=SEO 主标题（承接搜索词映射表），第 2 页起加「第 N 页」防标题重复。"""
    n, pages, items = d["page"], d["pages"], d["items"]
    slug = d["slug"]
    if slug == "all":
        first = ct["all_first"]
        pg = lambda i: ct["all_page"].format(n=i)
        h1 = "项目库 · 数据库开源项目"
        title1 = "数据库开源项目库：13,944 个项目档案与选型对比"
        active = "/projects/"
    else:
        first = ct["cat_first"].format(slug=slug)
        pg = lambda i: ct["cat_page"].format(slug=slug, n=i)
        h1 = f'{d["cat"]} · 数据库开源项目'
        title1 = f'{d["cat"]}工具与开源项目大全 · 数据库项目档案'
        active = f"/cat/{slug}/"
    title = title1 if n == 1 else f'{title1}（第 {n} 页）'
    rows = "\n".join(C.item_row(it, cfg) for it in items)
    body = (f'<h1>{C.esc(h1)}</h1>\n<p class="sub">按 star 降序 · 第 {n}/{pages} 页 · 本页 {len(items)} 条</p>\n'
            f'<div class="chips">{C.chips_html(cfg, "all" if slug == "all" else slug)}</div>\n'
            f'<ol class="rows">\n{rows}\n</ol>\n'
            f'{C.pager(n, pages, C.url(first, cfg), lambda i: C.url(pg(i), cfg))}')
    rel = first if n == 1 else pg(n)
    p = os.path.join(out_dir, *rel.lstrip("/").split("/")[:-1],
                     "index.html" if n == 1 else f"{n}.html")
    C.dump(p, C.page(cfg, title, cfg["site_desc"], ct["base"] + first if n == 1 else None, body, active))
    return p

def gen_lists(cfg, ct, out_dir):
    for d in ("projects", "cat"):                                    # 全量重写前清场（分片数变了旧页会残留）
        shutil.rmtree(os.path.join(out_dir, d), ignore_errors=True)
    data_root = cfg["data_root"]; n_pages = 0
    shards = shard_pages(data_root, "all") + [f for s, _ in cfg["cats"]
                                              for f in shard_pages(data_root, "cat", s)]
    for f in shards:
        render_list_page(cfg, ct, load_shard(f), out_dir); n_pages += 1
    assert n_pages == len(shards)
    print(f"OK list_pages: {n_pages} 页（/projects/ + /cat/，第 1 页=index.html 干净 URL）")
    return n_pages
