# -*- coding: utf-8 -*-
"""db_pages.py -- /db/<slug>/ 17 库页（每库：相关项目聚合页，承接「xx 数据库工具」类搜索词）"""
import glob, io, json, os, shutil
import common as C

def gen_db_pages(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "db"), ignore_errors=True)   # 全量重写前清场
    data_root = cfg["data_root"]; n = 0
    for f in sorted(glob.glob(os.path.join(data_root, "data", "db", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8"))
        slug, items = d["slug"], d["items"]
        rows = "\n".join(C.item_row(it, cfg) for it in items)
        title = f'{d["db"]} 生态工具与开源项目大全（{d["count"]} 个）· 数据库项目档案'
        body = (f'<h1>{C.esc(d["db"])} 生态 · 开源项目</h1>\n'
                f'<p class="sub">与 {C.esc(d["db"])} 适配/相关的开源项目 {d["count"]} 个，按 star 降序，'
                f'本页展示前 {len(items)} 个热门项目</p>\n'
                f'<div class="chips">{C.chips_html(cfg, None)}</div>\n'
                f'<ol class="rows">\n{rows}\n</ol>\n')
        p = os.path.join(out_dir, ct["db"].format(slug=slug).lstrip("/"), "index.html")
        C.dump(p, C.page(cfg, title, f'{d["db"]} 相关开源项目档案 {d["count"]} 个：驱动、工具、管理、监控与生态组件。',
                         ct["base"] + ct["db"].format(slug=slug), body, f"/db/{slug}/"))
        n += 1
    print(f"OK db_pages: {n} 库页（/db/<slug>/）")
    return n
