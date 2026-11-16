# -*- coding: utf-8 -*-
"""vs_pages.py -- /vs/{a}--{b}/ 对比页（高转化搜索词：A vs B 怎么选）

数据契约 site/data/vs/*.json（build_site 产）：{a, b, a_score, a_why, b_score, b_why, algo}；
渲染双栏对照 + 擂台算法说明 + 双方卡片入口。零数据逻辑：对子怎么选归 build_site，页长什么样归这里。
"""
import glob, io, json, os, shutil
import common as C

def side_html(it, score, why, cfg):
    stars = f'{it["stars"]:,}★' if isinstance(it.get("stars"), int) else ""
    meta = " · ".join(x for x in (it.get("lang"), it.get("cat")) if x)
    return (f'<div class="vs-side">\n'
            f'<a class="r-name" href="{C.esc(C.url(it["url"], cfg))}">{C.esc(it["name"])}</a>\n'
            f'<div class="r-fn">{C.esc(it["fn"])}</div>\n<div class="r-stars">{stars}</div>\n'
            f'<p class="r-meta">{C.esc(it.get("ol") or "")}</p>\n'
            f'<p class="r-meta">{C.esc(meta)}</p>\n'
            f'<p class="vs-why">{C.esc(why or "")}</p>\n'
            f'<div class="vs-score">擂台相似度 {score}</div>\n</div>')

def gen_vs_pages(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "vs"), ignore_errors=True)   # 全量重写前清场：弃用的对不留死链页
    files = sorted(glob.glob(os.path.join(cfg["data_root"], "data", "vs", "*.json")))
    for f in files:
        d = json.load(io.open(f, encoding="utf-8"))
        slug = os.path.basename(f)[:-5]
        A, B = d["a"], d["b"]
        title = f'{A["name"]} vs {B["name"]}：怎么选（{A["stars"]:,}★ vs {B["stars"]:,}★）· 数据库开源对比'
        body = (f'<h1>{C.esc(A["name"])} vs {C.esc(B["name"])}，怎么选</h1>\n'
                f'<p class="sub">同类擂台直接对手 · {C.esc(d.get("algo") or "arena")}</p>\n'
                f'<div class="chips">{C.chips_html(cfg, None)}</div>\n'
                f'<div class="vs-grid">\n{side_html(A, d.get("a_score"), d.get("a_why"), cfg)}\n'
                f'<div class="vs-mid">VS</div>\n{side_html(B, d.get("b_score"), d.get("b_why"), cfg)}\n</div>\n'
                f'<p class="sub">详细档案：<a href="{C.esc(C.url(A["url"], cfg))}">{C.esc(A["fn"])} 项目卡</a> · '
                f'<a href="{C.esc(C.url(B["url"], cfg))}">{C.esc(B["fn"])} 项目卡</a>；对比由算法自动圈选，'
                f'分数为生态重叠度（词表标签×生态专注度），非孰优孰劣。</p>\n')
        p = os.path.join(out_dir, ct["vs_first"].format(slug=slug).lstrip("/"), "index.html")
        C.dump(p, C.page(cfg, title, f'{A["name"]} 与 {B["name"]} 对比：一句话定位、星数、语言与擂台相似度，帮你在同类开源项目中选型。',
                         ct["base"] + ct["vs_first"].format(slug=slug), body, ""))
    print(f"OK vs_pages: {len(files)} 对比页（/vs/{'<slug>'}/）")
    return len(files)
