# -*- coding: utf-8 -*-
"""compare_pages.py -- /compare/ 对比索引页 + AI 深度对比长文静态页（P7.4）

索引页 = 全部 vs 对（site/data/vs/*.json，按双方星数和降序——高星对吃「A vs B」搜索词）
        + 深度长文入口（置顶）。
长文页源 = gen/compare_deep.json（data/comparisons.js 一次性转出的仓内内容源；原 JS 不进 dist，
          转出脚本即建仓时的一次性命令，不随构建跑）。
"""
import glob, io, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

DEEP_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_deep.json")
URL_INDEX = "/compare/"
URL_DEEP = "/compare/deep-{n}.html"
MIN_DEEP_CHARS = 800        # 长文正文门槛：实测 898/1104 字，原估 3000 系高估（见清单 7.4 验证结果）

def fn_item_map(cfg):
    """fn(小写) -> 分片 item（stars/lang/ol），全分片扫一遍 ~1s。"""
    m = {}
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "all-*.json")):
        for it in json.load(io.open(f, encoding="utf-8"))["items"]:
            m[it["fn"].lower()] = it
    return m

def vs_entries(cfg):
    out = []
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "vs", "*.json")):
        d = json.load(io.open(f, encoding="utf-8"))
        out.append((os.path.basename(f)[:-5], d["a"], d["b"]))
    out.sort(key=lambda x: -(((x[1].get("stars") or 0) + (x[2].get("stars") or 0))))
    return out

# ---------- 索引页 ----------

def index_body(cfg, ct, deeps):
    ents = vs_entries(cfg)
    rows = "\n".join(
        f'<li><div class="r-top"><a class="r-name" href="{C.esc(C.url(ct["vs_first"].format(slug=slug), cfg))}">'
        f'{C.esc(a["name"])} vs {C.esc(b["name"])}</a>'
        f'<span class="r-stars">{a["stars"]:,}★ vs {b["stars"]:,}★</span></div>'
        f'<div class="r-meta">{C.esc(a["fn"])} · {C.esc(b["fn"])}'
        f' · {C.esc((a.get("ol") or "")[:60])}</div></li>'
        for slug, a, b in ents)
    deep = "\n".join(
        f'<li><div class="r-top"><a class="r-name" href="{C.esc(C.url(URL_DEEP.format(n=i), cfg))}">'
        f'{C.esc(d["title"])}</a></div>'
        f'<div class="r-meta">{C.esc(" vs ".join(d["key"].split("|")))} · {C.esc(d["verdict"][:80])}…</div></li>'
        for i, d in enumerate(deeps, 1))
    return len(ents), (
        f'<h1>项目对比 · 数据库开源项目怎么选</h1>\n'
        f'<p class="sub">擂台算法自动圈选的同类对手两两对比（星数、语言、定位、生态重叠度），'
        f'另有人工圈题的 AI 深度对比长文。</p>\n'
        f'<h2>深度对比（AI 撰稿）</h2>\n<ol class="rows">\n{deep}\n</ol>\n'
        f'<h2>全部对比 {len(ents)} 组（按热度降序）</h2>\n<ol class="rows">\n{rows}\n</ol>\n')

# ---------- 长文页 ----------

def deep_body(d, cfg, ct, items):
    fns = d["key"].split("|")
    secs = "\n".join(
        f'<h3>{C.esc(s.get("h") or "")}</h3>\n<p>{C.esc(s.get("text") or "")}</p>'
        for s in d.get("sections") or [])
    picks = ("<table class=\"wk-panel\"><tr><td>场景</td><td>推荐</td></tr>" + "".join(
        f'<tr><td>{C.esc(p.get("scene") or "")}</td><td>{C.esc(p.get("pick") or "")}</td></tr>'
        for p in d.get("picks") or []) + "</table>") if d.get("picks") else ""
    cards = []
    for fn in fns:
        it = items.get(fn.lower())
        if it:
            meta = " · ".join(x for x in (it.get("lang"), f'{it["stars"]:,}★') if x)
            cards.append(f'<li><a class="r-name" href="{C.esc(C.url(it["url"], cfg))}">{C.esc(fn)}</a>'
                         f'<span class="wk-hint">{C.esc(meta)}</span>'
                         f'<div class="r-meta">{C.esc(it.get("ol") or "")}</div></li>')
        else:
            cards.append(f'<li><span class="r-name">{C.esc(fn)}</span>'
                         '<span class="wk-hint">已归档，无项目卡</span></li>')
    related = ""
    if len(fns) == 2:                                   # 双方对比且擂台有成对页 -> 互链
        slug = fns[0].replace("/", "__") + "--" + fns[1].replace("/", "__")
        alt = fns[1].replace("/", "__") + "--" + fns[0].replace("/", "__")
        for s in (slug, alt):
            if os.path.exists(os.path.join(cfg["data_root"], "data", "vs", s + ".json")):
                related = (f'<p class="wk-card">相关：<a href="{C.esc(C.url(ct["vs_first"].format(slug=s), cfg))}">'
                           f'{C.esc(fns[0])} vs {C.esc(fns[1])} 擂台对比页</a></p>')
                break
    return (
        f'<h1>{C.esc(d["title"])}</h1>\n'
        f'<p class="sub">AI 深度对比 · {C.esc(" vs ".join(fns))} · '
        f'<a href="{C.esc(C.url(URL_INDEX, cfg))}">返回对比索引</a></p>\n'
        f'<div class="wk-lede"><b>结论</b><span>{C.esc(d.get("verdict") or "")}</span></div>\n'
        f'{secs}\n<h2>怎么选</h2>\n{picks}\n'
        f'<h2>参战项目档案</h2>\n<ol class="rows">\n' + "\n".join(cards) + '\n</ol>\n' + related)

# ---------- 入口 ----------

def gen_compare(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "compare"), ignore_errors=True)   # 清场：长文篇数变了不留死页
    deeps = json.load(io.open(DEEP_SRC, encoding="utf-8"))
    items = fn_item_map(cfg)
    n_vs, idx = index_body(cfg, ct, deeps)
    p = os.path.join(out_dir, "compare", "index.html")
    C.dump(p, C.page(cfg, f"数据库开源项目对比大全：{n_vs} 组热门 A vs B 选型对比",
                     f"{n_vs} 组数据库开源项目两两对比：星数、语言、定位一句话与擂台相似度，另有 AI 深度对比长文。",
                     ct["base"] + URL_INDEX, idx, URL_INDEX))
    for i, d in enumerate(deeps, 1):
        body = deep_body(d, cfg, ct, items)
        t = C.page(cfg, d["title"], (d.get("verdict") or "")[:150],
                   ct["base"] + URL_DEEP.format(n=i), body, URL_INDEX)
        txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", "", t))
        n = len(" ".join(txt.split()))
        assert n >= MIN_DEEP_CHARS, f"长文 deep-{i} 正文仅 {n} 字（<{MIN_DEEP_CHARS}）"
        C.dump(os.path.join(out_dir, *URL_DEEP.format(n=i).lstrip("/").split("/")), t)
    print(f"OK compare_pages: 索引页（{n_vs} 组 vs）+ {len(deeps)} 篇 AI 长文（/compare/）")
    return n_vs

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_compare(cfg, ct, out_dir)
