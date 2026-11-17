# -*- coding: utf-8 -*-
"""vs_pages.py -- /vs/{a}--{b}/ 对比页（P7.14：恢复旧版「信号并排」排版）

版面=旧 compare.html 的 table.cmp（.cg 分组行 + 行内最高加粗 .win + .clamp 定位），
静态直出双方画像与 Star 信号 + 擂台说明。数据契约 site/data/vs/*.json（build_site 产）；
对子怎么选归 build_site，页长什么样归这里。
"""
import glob, io, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

def _th(x, cfg):
    return (f'<th class="cmp-proj"><a href="{C.esc(C.url(x["url"], cfg))}" style="color:inherit">'
            f'{C.esc(x["name"])} <span class="muted small mono">{C.esc(x["fn"].split("/")[0])}</span></a></th>')

def _td(html): return f"<td>{html}</td>"

def side_html(it, score, why, cfg):
    stars = f'{it["stars"]:,}' if isinstance(it.get("stars"), int) else "—"
    meta = " · ".join(x for x in (it.get("lang"), it.get("cat")) if x)
    return (f'<td><div class="clamp"><b>{C.esc(it["name"])}</b> · {stars}★</div>'
            f'<div class="clamp muted">{C.esc(it.get("ol") or "")}</div>'
            f'<div class="small muted">{C.esc(meta)}</div></td>')

def gen_vs_pages(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "vs"), ignore_errors=True)   # 全量重写前清场：弃用的对不留死链页
    files = sorted(glob.glob(os.path.join(cfg["data_root"], "data", "vs", "*.json")))
    for f in files:
        d = json.load(io.open(f, encoding="utf-8"))
        slug = os.path.basename(f)[:-5]
        A, B = d["a"], d["b"]
        sa = f'{A["stars"]:,}' if isinstance(A.get("stars"), int) else "—"
        sb = f'{B["stars"]:,}' if isinstance(B.get("stars"), int) else "—"
        a_win = (A.get("stars") or 0) >= (B.get("stars") or 0)
        row = lambda label, ca, cb, title="": (
            f'<tr><th{f" title=\"{C.esc(title)}\"" if title else ""}>{label}</th>{ca}{cb}</tr>')
        star_row = (f'<tr><th title="GitHub Stars 总数；加粗=行内最高">Star</th>'
                    f'<td class="{"win" if a_win else ""}"><span class="mono">{sa}</span></td>'
                    f'<td class="{"win" if not a_win else ""}"><span class="mono">{sb}</span></td></tr>')
        rows = "".join([
            row("一句话定位", _td(f'<div class="clamp">{C.esc(A.get("ol") or "—")}</div>'),
                            _td(f'<div class="clamp">{C.esc(B.get("ol") or "—")}</div>')),
            row("类别", _td(f'<span class="tag gray">{C.esc(A.get("cat") or "—")}</span>'),
                         _td(f'<span class="tag gray">{C.esc(B.get("cat") or "—")}</span>')),
            row("主语言", _td(C.esc(A.get("lang") or "—")), _td(C.esc(B.get("lang") or "—"))),
            row("适配库", _td(" ".join(f'<span class="tag">{C.esc(x)}</span>' for x in (A.get("dbs") or [])[:4]) or '<span class="muted">—</span>'),
                          _td(" ".join(f'<span class="tag">{C.esc(x)}</span>' for x in (B.get("dbs") or [])[:4]) or '<span class="muted">—</span>')),
            star_row,
        ])
        body = f"""<main>
    <section class="hero" style="padding:24px 0 8px">
      <h1>{C.esc(A["name"])} vs {C.esc(B["name"])}，怎么选</h1>
      <p>同类擂台直接对手 · 相似度 {C.esc(str(d.get("a_score") or "—"))}。对比由算法自动圈选，
        分数为生态重叠度（词表标签×生态专注度），非孰优孰劣；详细信号见双方项目卡。</p>
    </section>
    <section class="card">
      <div class="card-head"><h2>信号并排<span class="hint">数据层自动 · 加粗=行内最高</span></h2></div>
      <div class="tblwrap"><table class="cmp">
        <tr><th></th>{_th(A, cfg)}{_th(B, cfg)}</tr>
        <tr class="cg"><th colspan="3">画像</th></tr>
        {rows}
        <tr class="cg"><th colspan="3">擂台解读</th></tr>
        {row("擂台视角", _td(f'<div class="clamp">{C.esc(d.get("a_why") or "")}</div>'), _td(f'<div class="clamp">{C.esc(d.get("b_why") or "")}</div>'))}
      </table></div>
      <div class="small muted" style="margin-top:10px">算法：{C.esc(d.get("algo") or "arena v2.6")} ·
        详细档案：<a href="{C.esc(C.url(A["url"], cfg))}">{C.esc(A["fn"])} 项目卡</a> ·
        <a href="{C.esc(C.url(B["url"], cfg))}">{C.esc(B["fn"])} 项目卡</a></div>
    </section>
  </main>
  <footer>对比页由擂台算法自动圈选生成 · <a href="{C.esc(C.url("/compare/", cfg))}">全部对比</a> · 数据每日更新。</footer>"""
        p = os.path.join(out_dir, ct["vs_first"].format(slug=slug).lstrip("/"), "index.html")
        C.dump(p, C.page_legacy(cfg, f'{A["name"]} vs {B["name"]}：怎么选（{sa}★ vs {sb}★）· 数据库开源对比',
                                f'{A["name"]} 与 {B["name"]} 对比：一句话定位、星数、语言、适配库与擂台相似度，帮你选型。',
                                ct["base"] + ct["vs_first"].format(slug=slug), body, "/compare/"))
    print(f"OK vs_pages: {len(files)} 对比页（/vs/{'<slug>'}/，旧版 cmp 排版）")
    return len(files)
