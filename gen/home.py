# -*- coding: utf-8 -*-
"""home.py -- 站点门面首页（P7.3）：/ 不再是周刊 JS 壳，而是全站入口 + 最新一期摘要。

板块（自上而下）：最新期看点与深读入口 / 热门项目 Top10 / 类目入口 / 17 库生态入口 / 热门对比。
数据全部来自 site/ 契约分片与 data/weekly.js；复用 weekly_pages 的加载与重写（不重复实现）。
首页是全站权重最高的 URL，入口矩阵比装饰重要——每个板块标题都是搜索词承接位。
"""
import glob, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import weekly_pages as W

N_TOP = 10          # 热门项目榜条数
N_VS = 5            # 热门对比条数

def top_items(cfg):
    d = json.load(io.open(os.path.join(cfg["data_root"], "data", "all-1.json"), encoding="utf-8"))
    return d["items"][:N_TOP]

def db_entries(cfg):
    """[(库名, slug, 卡数)] 按卡数降序——库清单以分片盘上为准，不写死 17。"""
    out = []
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "db", "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        out.append((d.get("db") or os.path.basename(f)[:-5], os.path.basename(f)[:-5], d.get("count") or 0))
    return sorted(out, key=lambda x: -x[2])

def vs_top(cfg):
    """对比 Top N（双方星数和降序）。545 个分片各 <1KB，全读 <0.1s。"""
    out = []
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "vs", "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        out.append((os.path.basename(f)[:-5], d["a"], d["b"]))
    out.sort(key=lambda x: -(((x[1].get("stars") or 0) + (x[2].get("stars") or 0))))
    return out[:N_VS]

def home_body(cfg, ct):
    issues = W.load_weekly()
    no, d = max(issues.items())
    act = W.active_fns(cfg)
    cnt = {"j_link": 0, "j_drop": 0, "c_link": 0, "g_link": 0}
    lede = "\n".join(
        f'<div class="wk-lede"><b>{C.esc(lab)}</b><span>{W.relink(txt, act, cfg, cnt)}</span></div>'
        for lab, txt in (d.get("lede") or []))
    deep = "\n".join(
        f"<li>{C.esc(a.get('tag') or '')}：<a href=\"{C.esc(C.url(W.URL_FIRST.format(n=no), cfg))}\">"
        f"{C.esc(a.get('title') or '')}</a></li>" for a in (d.get("deep") or []))
    rows = "\n".join(C.item_row(it, cfg) for it in top_items(cfg))
    dbs = " · ".join(
        f'<a href="{C.esc(C.url(ct["db"].format(slug=slug), cfg))}">{C.esc(name)}</a>'
        f"（{n}）" for name, slug, n in db_entries(cfg))
    vs = "\n".join(
        f'<li><a href="{C.esc(C.url(ct["vs_first"].format(slug=slug), cfg))}">'
        f'{C.esc(a["name"])} vs {C.esc(b["name"])}</a>'
        f'<span class="wk-hint">{a["stars"]:,}★ vs {b["stars"]:,}★</span></li>'
        for slug, a, b in vs_top(cfg))
    return no, len(act), (
        f'<h1>数据库开源生态 · 周刊与项目档案库</h1>\n'
        f'<p class="sub">每周一刊 · 项目档案每日更新 · 共 {len(act):,} 个数据库开源项目</p>\n'
        f'<h2>最新一期：第 {no} 期（{d["date"]}）</h2>\n{lede}\n'
        f'<ul class="wk-ol">\n{deep}\n</ul>\n'
        f'<p class="wk-card"><a href="{C.esc(C.url(W.URL_FIRST.format(n=no), cfg))}">阅读本期全文</a> · '
        f'<a href="{C.esc(C.url("/archive.html", cfg))}">往期目录</a></p>\n'
        f'<h2>热门项目 Top {N_TOP}（按 star）</h2>\n<ol class="rows">\n{rows}\n</ol>\n'
        f'<p class="wk-card"><a href="{C.esc(C.url(ct["all_first"], cfg))}">浏览全部 {len(act):,} 个项目</a></p>\n'
        f'<h2>按类目浏览</h2>\n<div class="chips">{C.chips_html(cfg, None)}</div>\n'
        f'<h2>按数据库生态浏览</h2>\n<p class="wk-nums">{dbs}</p>\n'
        f'<h2>热门对比</h2>\n<ul class="wk-glance">\n{vs}\n</ul>\n'
        f'<p class="wk-card"><a href="{C.esc(C.url("/compare/", cfg))}">全部对比</a></p>')

def gen_home(cfg, ct, out_dir):
    no, total, body = home_body(cfg, ct)
    p = os.path.join(out_dir, "index.html")
    C.dump(p, C.page(cfg, f"数据库开源生态周刊 · {total:,} 个开源项目档案与选型对比",
                     cfg["site_desc"], ct["base"] + "/", body, "/"))
    t = io.open(p, encoding="utf-8").read()
    txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", "", t))
    n = len(" ".join(txt.split()))
    assert n >= 1500, f"首页正文仅 {n} 字（<1500）"
    assert "data/weekly.js" not in t and "app.js" not in t, "首页仍引用旧 JS"
    print(f"OK home: 门面首页（第 {no} 期摘要 + Top{N_TOP} + 类目/库/对比入口），正文 {n} 字")
    return n

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_home(cfg, ct, out_dir)
