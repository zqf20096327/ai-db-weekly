# -*- coding: utf-8 -*-
"""compare_pages.py -- /compare/ 对比索引 + AI 长文页（P7.14：恢复旧版项目对比排版）

版面=旧 compare.html 原版静态直出：hero + 「热门对比」chips 行（旧版 curated 位，现为
热度 Top12 → /vs/）+「🤖 AI 对比解读」卡（ai-title/ai-verdict/ai-sec/ai-picks 原样式）
+ 全部对比清单（table.rows，545 组按热度降序）。旧版对比篮/信号并排是 pool.js 交互能力，
静态版由 /vs/{slug}/ 对比页承接；长文页源 = gen/compare_deep.json（原 JS 不进 dist）。
"""
import glob, io, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import list_pages as L

DEEP_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_deep.json")
URL_INDEX = "/compare/"
URL_DEEP = "/compare/deep-{n}.html"
MIN_DEEP_CHARS = 800        # 长文正文门槛：实测 898/1104 字，原估 3000 系高估（见清单 7.4 验证结果）
N_HOT = 12                  # 热门对比 chips 数（旧版 curated 4 位，静态版放宽到 12）

def fn_item_map(cfg):
    """fn(小写) -> 分片 item（stars/lang/ol/dbs），全分片扫一遍 ~1s。"""
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

# ---------- AI 长文（旧版 ai-* 原样式） ----------

def deep_body(d, cfg, ct, items):
    fns = d["key"].split("|")
    secs = "".join(f'<div class="ai-sec"><b>{C.esc(s.get("h") or "")}</b>'
                   f"<p>{C.esc(s.get('text') or '')}</p></div>" for s in d.get("sections") or [])
    picks = "".join(f'<div class="ai-pick"><span class="scene">{C.esc(p.get("scene") or "")}</span>'
                    f" → <b>{C.esc(p.get('pick') or '')}</b></div>" for p in d.get("picks") or [])
    cards = " ".join(
        (f'<a class="chip" href="{C.esc(C.url(items[fn.lower()]["url"], cfg))}">{C.esc(fn)}'
         f'<span class="n">{items[fn.lower()]["stars"]:,}★</span></a>')
        if fn.lower() in items else f'<span class="chip off">{C.esc(fn)}</span>'
        for fn in fns)
    related = ""
    if len(fns) == 2:                                   # 双方对比且擂台有成对页 -> 互链（slug 全小写=与盘上 vs 分片一致）
        for s in (fns[0].lower().replace("/", "__") + "--" + fns[1].lower().replace("/", "__"),
                  fns[1].lower().replace("/", "__") + "--" + fns[0].lower().replace("/", "__")):
            if os.path.exists(os.path.join(cfg["data_root"], "data", "vs", s + ".json")):
                related = (f'<div class="small muted" style="margin-top:12px">相关：'
                           f'<a href="{C.esc(C.url(ct["vs_first"].format(slug=s), cfg))}" style="color:var(--accent)">'
                           f'{C.esc(fns[0])} vs {C.esc(fns[1])} 擂台对比页 →</a></div>')
                break
    return f"""<h3 class="ai-title">{C.esc(d["title"])}</h3>
<div class="ai-verdict">{C.esc(d.get("verdict") or "")}</div>
{secs}
<div class="ai-picks">{picks}</div>
<div class="tagrow" style="margin-top:14px">{cards}</div>
{related}
<div class="small muted" style="margin-top:10px">AI 对比解读构建期生成（基于双方 README 与信号，非运行时调用）·
选材冻结于发稿时，最新信号见各项目卡。</div>"""

# ---------- 索引页 ----------

def index_body(cfg, ct, deeps):
    ents = vs_entries(cfg)
    hot = "".join(
        f'<a class="chip" href="{C.esc(C.url(ct["vs_first"].format(slug=slug), cfg))}">'
        f'{C.esc(a["name"])} vs {C.esc(b["name"])}<span class="n">{L.fmt_k(a.get("stars") or 0)}★</span></a>'
        for slug, a, b in ents[:N_HOT])
    rows = "".join(
        f'<tr><td><a class="repo" href="{C.esc(C.url(ct["vs_first"].format(slug=slug), cfg))}">'
        f'{C.esc(a["name"])} vs {C.esc(b["name"])}（{C.esc(a["fn"])} / {C.esc(b["fn"])}）</a>'
        f'<div class="sub">{C.esc((a.get("ol") or "")[:80])}</div></td>'
        f'<td>{L.db_tags(a)}</td>'
        f'<td class="small">{C.esc(a.get("cat") or "—")}</td>'
        f'<td class="r mono">{a["stars"]:,}★ vs {b["stars"]:,}★</td></tr>'
        for slug, a, b in ents)
    deep_cards = ""
    items = fn_item_map(cfg)
    for i, d in enumerate(deeps, 1):
        deep_cards += (f'<div class="sec-title" style="margin:14px 0 0"><h3>解读 {i} · '
                       f'{C.esc(" vs ".join(d["key"].split("|")[:2]))}</h3><span class="line"></span>'
                       f'<a class="small" href="{C.esc(C.url(URL_DEEP.format(n=i), cfg))}" '
                       f'style="color:var(--accent)">单独页 →</a></div>\n' + deep_body(d, cfg, ct, items))
    return len(ents), f"""<main>
    <section class="hero" style="padding:24px 0 8px">
      <h1>项目对比</h1>
      <p>同类项目并排比较，帮你选型。热门对比与全部清单为擂台算法自动圈选（{len(ents)} 组）；
        「AI 对比解读」为构建期生成的深度长文。旧版对比篮是交互能力（已随 pool.js 退役），
        静态版点任意组合进对比页。</p>
    </section>
    <section class="card">
      <div class="card-head"><h2>热门对比<span class="hint">按双方热度 · 点按进入</span></h2></div>
      <div class="tagrow" style="margin-top:8px">{hot}</div>
      <div class="sec-title" style="margin:14px 0 0"><h3>☰ 全部对比（{len(ents)} 组）</h3><span class="line"></span>
        <span class="muted small">按热度降序 · 每组含画像并排与擂台解读</span></div>
      <div class="tblwrap"><table class="rows">
        <thead><tr><th style="min-width:250px">组合</th><th>库</th><th>类别</th><th class="r">热度</th></tr></thead>
        <tbody>
{rows}
        </tbody></table></div>
    </section>
    <section class="card">
      <div class="card-head"><h2>🤖 AI 对比解读<span class="hint">构建期由 AI 基于双方 README 与信号生成 · 非运行时调用</span></h2></div>
{deep_cards}
    </section>
  </main>
  <footer>对比组合由擂台算法圈选 · 分数为生态重叠度非孰优孰劣 · 数据每日更新。</footer>"""

# ---------- 长文单独页 ----------

def deep_page_body(d, cfg, ct, items):
    return f"""<main>
    <section class="hero" style="padding:24px 0 8px">
      <h1>AI 对比解读 · {C.esc(" vs ".join(d["key"].split("|")[:2]))}</h1>
      <p><a href="{C.esc(C.url(URL_INDEX, cfg))}" style="color:var(--accent)">← 返回项目对比</a></p>
    </section>
    <section class="card">
      <div class="card-head"><h2>🤖 {C.esc(d["title"])}</h2></div>
      {deep_body(d, cfg, ct, items)}
    </section>
  </main>
  <footer>AI 对比解读 · 构建期生成 · <a href="{C.esc(C.url(URL_INDEX, cfg))}">全部对比</a></footer>"""

# ---------- 入口 ----------

def gen_compare(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "compare"), ignore_errors=True)   # 清场：长文篇数变了不留死页
    L._boot_maps(cfg)
    deeps = json.load(io.open(DEEP_SRC, encoding="utf-8"))
    items = fn_item_map(cfg)
    n_vs, idx = index_body(cfg, ct, deeps)
    p = os.path.join(out_dir, "compare", "index.html")
    C.dump(p, C.page_legacy(cfg, f"项目对比 · {n_vs} 组数据库开源项目怎么选",
                            f"{n_vs} 组同类开源项目对比：画像并排、热度与擂台解读，另有 AI 深度对比长文。",
                            ct["base"] + URL_INDEX, idx, "/compare/", L.FZONE_CSS))
    for i, d in enumerate(deeps, 1):
        body = deep_page_body(d, cfg, ct, items)
        t = C.page_legacy(cfg, f'{d["title"]} · AI 对比解读', (d.get("verdict") or "")[:150],
                          ct["base"] + URL_DEEP.format(n=i), body, "/compare/", L.FZONE_CSS)
        txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", "", t))
        n = len(" ".join(txt.split()))
        assert n >= MIN_DEEP_CHARS, f"长文 deep-{i} 正文仅 {n} 字（<{MIN_DEEP_CHARS}）"
        C.dump(os.path.join(out_dir, *URL_DEEP.format(n=i).lstrip("/").split("/")), t)
    print(f"OK compare_pages: 索引（{n_vs} 组 + 热门 {N_HOT} chips）+ {len(deeps)} 篇 AI 长文（旧版排版）")
    return n_vs

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_compare(cfg, ct, out_dir)
