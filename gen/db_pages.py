# -*- coding: utf-8 -*-
"""db_pages.py -- /db/{slug}/ 库生态页 ×17（P7.14：恢复旧版项目浏览排版）

版面=list_pages 同族（card + fzone 数据库/类别 chips + table.rows 清单），
当前库 chip 高亮；库页承接「xx 数据库工具」类搜索词。
"""
import glob, io, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import list_pages as L

def gen_db_pages(cfg, ct, out_dir):
    L._boot_maps(cfg)
    shutil.rmtree(os.path.join(out_dir, "db"), ignore_errors=True)   # 全量重写前清场
    bins = L.combo_bins(L.load_all_items(cfg), {v: k for k, v in L.DB_NAME.items()},
                        {name: slug for slug, name in cfg["cats"]})   # P8.4：类别行钻取 + 组合页共用
    n = 0
    for f in sorted(glob.glob(os.path.join(cfg["data_root"], "data", "db", "*.json"))):
        d = json.load(io.open(f, encoding="utf-8"))
        slug = d["slug"]
        name = L.DB_NAME.get(slug, d.get("db") or slug)
        rows = "".join(L.row_html(it, cfg) for it in d["items"])
        body = f"""<main>
    <section class="card">
      <div class="card-head" style="margin-bottom:2px"><h2>{C.esc(name)} 生态工具<span class="hint">收录 {d["count"]:,} 项 · Star 降序 · 本页 Top {len(d["items"])}</span></h2></div>
      <div class="fzone">
        <div class="tagrow"><span class="glabel">数据库</span>{L.db_chips(cfg, on_slug=slug)}</div>
        <div class="tagrow"><span class="glabel">类别</span>{L.cat_chips(cfg, via_db=slug, combos=bins)}</div>
      </div>
      <div class="statline"><span class="big" title="{C.esc(name)} 相关的开源工具与项目">匹配 {d["count"]:,}</span>
        <span class="sub">库页封顶 500 热门 · 长尾走类目页</span></div>
      <hr class="divider">
      <div class="tblwrap"><table class="rows">
        <thead><tr><th style="min-width:250px">项目</th><th>库</th><th>类别</th><th>语言</th><th class="r">Star</th></tr></thead>
        <tbody>
{rows}
        </tbody></table></div>
    </section>
  </main>
  <footer>{C.esc(name)} 生态工具档案 · 数据每日更新 · 一卡可跨多库（计入多库页）。</footer>"""
        p = os.path.join(out_dir, ct["db"].format(slug=slug).lstrip("/"), "index.html")
        C.dump(p, C.page_legacy(cfg, f"{name} 生态工具与开源项目大全（{d['count']} 个）· 数据库项目档案",
                                f"{name} 生态的开源项目档案 {d['count']} 个：驱动、备份、监控、迁移与管理工具，Star 降序。",
                                ct["base"] + ct["db"].format(slug=slug), body, "/projects/", L.FZONE_CSS))
        n += 1
    n_combo = L.gen_combo_pages(cfg, ct, out_dir, bins)   # P8.3：组合页挂本步尾部（开头 rmtree db/ 已清场）
    print(f"OK db_pages: {n} 库页（旧版排版，库 chip 高亮）+ {n_combo} 组合页")
    return n
