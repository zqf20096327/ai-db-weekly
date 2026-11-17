# -*- coding: utf-8 -*-
"""weekly_pages.py -- /weekly/{n}/ 每期静态页 + /archive.html 往期索引（P7.1/P7.2/P7.13）

数据源 = 仓根 data/weekly.js（freeze_issue 编译产物，唯一全量源——issues/*.json 是缺字段底稿，
只有 no/date/theme/deep，无 lede/nums/glance/onelines/panel，故不读它）。
解析纪律：weekly.js 每行一条 WEEKLY[n] = {...};，逐行 json.loads，期号不一致/解析失败即断言崩。

排版（P7.13 用户令「严格按照之前排版」）：全部沿用旧版 assets/app.css 设计令牌与 hero+三板块
版面（期号行/导读/一句话情报/深读卡/速览四卡），页面壳=common.page_legacy。静态化替代：
  - 旧「点卡片开抽屉读全文」-> <details class="article-card"> 原卡即 summary，展开即正文+信号面板；
  - 旧 data-fn 假链（JS 开抽屉）-> /p/{fn}/ 真卡链；fn 不在活跃集降级纯文本，绝不留站内 404；
  - <code>owner/repo</code> 速览写法与 glance 行 fn 按同一规则补链。
活跃集来自 site/data/all-*.json 分片（数据契约，不读 collect 仓内部文件）。
URL 模式 /weekly/{n}/ 属内容页，归 gen 侧声明（数据 URL 才归 build_site 契约，见 P7.8 注）。
"""
import glob, io, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I 隔离模式不自动加脚本目录
import common as C

URL_FIRST = "/weekly/{n}/"
WEEKLY_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "weekly.js")

JUMP = re.compile(r'<a href="#" class="jump" data-fn="([^"]+)">(.*?)</a>')
CODE_FN = re.compile(r"<code>([A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*)</code>")
SIDE = {"intl": "国际", "cn": "国产"}
GLANCE_LAB = [("risk", "risk", "🔴", "风险预警"), ("ver", "rel", "📦", "版本动态"),
              ("gain", "gain", "📈", "增星榜"), ("newb", "newb", "🌱", "新项目")]   # (css 类=旧版, 数据键, 图标, 名)

# 期号行 + details 卡（静态化新增的微调，视觉零变化）
EXTRA_CSS = """\
.iss-no-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.iss-nav { margin-left: auto; display: inline-flex; gap: 14px; font-size: 12px; }
.iss-nav a { color: var(--muted); }
.iss-nav a:hover { color: var(--accent); }
.iss-nav .off { color: var(--line); }
details.article-card { cursor: pointer; }
details.article-card[open] { cursor: default; }
details.article-card > summary { display: flex; flex-direction: column; gap: 8px; list-style: none; }
details.article-card > summary::-webkit-details-marker { display: none; }
details.article-card .dr-article { border-top: 1px dashed var(--line); margin-top: 8px; padding-top: 6px; }
.issue-panel { grid-template-columns: repeat(2,1fr); }
.dr-actions { margin-top: 10px; }
"""

ARCHIVE_CSS = """\
.iss { border: 1px solid var(--line); border-radius: 12px; background: var(--card);
       padding: 14px 18px; margin-bottom: 12px; box-shadow: var(--shadow); }
.iss-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.iss-no { font-weight: 700; color: var(--accent); }
.iss-head .tags { display: inline-flex; gap: 6px; flex-wrap: wrap; }
.iss-deep { display: grid; gap: 5px; margin-top: 9px; }
.iss-deep .it { display: flex; gap: 9px; align-items: baseline; font-size: 12px; min-width: 0; }
.iss-deep .it .t { color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.iss-deep .it .fn { color: var(--muted); }
@media (max-width: 640px) {
  .iss-deep .it { flex-direction: column; align-items: flex-start; gap: 3px; }
  .iss-deep .it .t { white-space: normal; }
}
"""

def load_weekly():
    """data/weekly.js -> {no: issue}。行格式漂移（freeze_issue 换手笔）会在断言处崩，故意的。"""
    out = {}
    for ln in io.open(WEEKLY_JS, encoding="utf-8"):
        m = re.match(r"WEEKLY\[(\d+)\] = (\{.*\});\s*$", ln)
        if not m: continue
        d = json.loads(m.group(2))
        assert d["no"] == int(m.group(1)), f"weekly.js 期号漂移: 键 {m.group(1)} != no {d['no']}"
        out[d["no"]] = d
    assert out, "weekly.js 一期都没解析到"
    return out

def active_fns(cfg):
    """活跃 fn 集，统一小写。manifest 键全小写（13944/13944），卡物理路径即小写；
    weekly.js 用 GitHub 原始大小写（ClickHouse/ClickHouse），大小写不归一会 100% 假降级。"""
    fns = set()
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "all-*.json")):
        for it in json.load(io.open(f, encoding="utf-8"))["items"]:
            fns.add(it["fn"].lower())
    return fns

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")

# ---------- 内链重写 ----------

def fn_link(fn, act, cfg, cnt):
    """fn -> 卡链接；不在活跃集返回纯文本（降级），永不产站内 404。
    URL 用小写形态=与卡物理路径逐字一致（GH Pages 大小写敏感）。"""
    if not fn: return ""
    key = fn.lower()
    if key in act:
        cnt["g_link"] += 1
        return f'<a href="{C.esc(C.url("/p/" + key + "/", cfg))}">{C.esc(fn)}</a>'
    return C.esc(fn)                             # glance 行降级不计数：源里本就不是链接

def relink(html, act, cfg, cnt):
    """对一段源 HTML 做 jump 假链 + code 仓名两类重写（jump 保 class=jump 虚线样式）。"""
    def jump_sub(m):
        fn, key = m.group(1), m.group(1).lower()
        if key in act:
            cnt["j_link"] += 1
            return f'<a class="jump" href="{C.esc(C.url("/p/" + key + "/", cfg))}">{m.group(2)}</a>'
        cnt["j_drop"] += 1
        return f"<span>{m.group(2)}</span>"
    def code_sub(m):
        fn, key = m.group(1), m.group(1).lower()
        if key in act:
            cnt["c_link"] += 1
            return f'<a href="{C.esc(C.url("/p/" + key + "/", cfg))}"><code>{fn}</code></a>'
        return m.group(0)                       # 不是站内仓（或未收录）保持 code 原样
    return CODE_FN.sub(code_sub, JUMP.sub(jump_sub, html))

# ---------- 整期版面（首页与各期页共用；版面=旧 index.html 原排版静态直出） ----------

def _hero(d, act, cfg, cnt, nos, home):
    no = d["no"]
    prev = [x for x in nos if x < no]; nxt = [x for x in nos if x > no]
    iss_nav = ((f'<a href="{C.esc(C.url(URL_FIRST.format(n=prev[-1]), cfg))}">‹ 上一期</a>' if prev
                else '<span class="off">‹ 上一期</span>')
               + (f'<a href="{C.esc(C.url(URL_FIRST.format(n=nxt[0]), cfg))}">下一期 ›</a>' if nxt else "")
               + ("" if home else f'<a href="{C.esc(C.url("/", cfg))}">回到最新</a>')
               + f'<a href="{C.esc(C.url("/archive.html", cfg))}">往期 →</a>')
    numline = "<i>·</i>".join(
        f'<a href="{C.esc(C.url("/projects/", cfg))}"><b>{C.esc(r[1])}</b>{C.esc(r[0])}</a>'
        for r in (d.get("nums") or [])[:6])   # 第 3 列是旧 JS 页锚链，弃
    lede = "\n".join(
        f'<div class="lede-row"><span class="lede-k">{C.esc(lab)}</span>'
        f'<div class="lede-t">{relink(txt, act, cfg, cnt)}</div></div>'
        for lab, txt in (d.get("lede") or []))
    return f"""<section class="hero issue-hero">
    <div class="iss-no-row">
      <div class="issue-no">第 {no} 期 <span class="muted">· {C.esc(d["date"])} · 每周一刊</span></div>
      <span class="iss-nav">{iss_nav}</span>
    </div>
    <div class="h1-row">
      <h1>数据库开源生态周刊</h1>
      <a class="btn primary cta-top" href="{C.esc(C.url("/projects/", cfg))}">浏览 {len(act):,} 个项目档案 →</a>
    </div>
    <div class="issue-slogan">国际 7 库 · 国产 10 库 · 每周更新</div>
    <div class="numline">{numline}</div>
    <div class="lede-label">本期导读</div>
    <div class="lede">
{lede}
    </div>
  </section>"""

def _deep_cards(d, act, cfg, cnt):
    out = []
    for a in d.get("deep") or []:
        nums = "".join(f'<span><b>{C.esc(v)}</b> {C.esc(k)}</span>' for k, v in (a.get("nums") or [])[:4])
        paras = "".join(f"<p>{C.esc(p)}</p>" for p in a.get("body") or [])
        panel = ('<div class="issue-panel">' + "".join(
            f'<div class="ip"><div class="k">{C.esc(k)}</div><div class="v mono">{C.esc(v)}</div></div>'
            for k, v in a["panel"]) + "</div>") if a.get("panel") else ""
        fn = a.get("fn") or ""
        card_link = (f'<div class="dr-actions"><a class="btn" href="{C.esc(C.url("/p/" + fn.lower() + "/", cfg))}">'
                     f'项目档案 →</a></div>') if fn.lower() in act else ""
        out.append(
            f'<details class="article-card">\n<summary>\n'
            f'<div class="sector">{C.esc(a.get("tag") or "")}</div>\n'
            f'<h3>{C.esc(a.get("title") or "")}</h3>\n'
            f'<div class="fn mono">{C.esc(fn)}</div>\n'
            f'<p>{C.esc(a.get("summary") or "")}</p>\n'
            f'<div class="nums">{nums}</div>\n'
            f'<div class="read">阅读全文 ↓</div>\n</summary>\n'
            f'<div class="dr-article">\n{paras}\n{panel}\n{card_link}\n'
            f'<div class="small muted" style="margin-top:12px">选稿依据与信号面板冻结于第 {d["no"]} 期'
            f'（快照 {C.esc(d.get("snap") or "—")}）。</div>\n</div>\n</details>')
    return "\n".join(out)

def _d_item(r, act, cfg, cnt):
    fn = r.get("fn") or ""
    inner = (f'{r.get("chip") or ""} <span class="repo">{C.esc(fn)}</span>'
             f'<span class="d-meta">{r.get("meta") or ""}</span>')
    key = fn.lower()
    if key in act:
        cnt["g_link"] += 1
        return f'<a class="d-item" href="{C.esc(C.url("/p/" + key + "/", cfg))}">{inner}</a>'
    return f'<div class="d-item">{inner}</div>'

def _digest(d, act, cfg, cnt):
    g = d.get("glance") or {}
    out = []
    for key, data_key, emoji, name in GLANCE_LAB:
        blk = g.get(data_key) or {}
        rows = "\n".join(_d_item(r, act, cfg, cnt) for r in blk.get("rows") or [])
        body = rows if rows.strip() else '<div class="d-empty">✓ 本周无相关事件</div>'
        out.append(
            f'<section class="card digest {key}">\n'
            f'<div class="card-head"><h2>{emoji} {name}<span class="hint">{C.esc(blk.get("hint") or "")}</span></h2>\n'
            f'<a class="small" href="{C.esc(C.url("/projects/", cfg))}" style="color:var(--accent)">全部 →</a></div>\n'
            f'<div class="d-list">\n{body}\n</div>\n</section>')
    return "\n".join(out)

def issue_html(d, act, cfg, cnt, nos, home=False):
    """整期版面：hero（期号行/h1/slogan/数字行/导读）+ 一句话情报 + 深读卡 + 速览四卡。"""
    onelines = "\n".join(f"<li>{relink(t, act, cfg, cnt)}</li>" for t in d.get("onelines") or [])
    return (_hero(d, act, cfg, cnt, nos, home) + f"""
  <main>
    <section>
      <div class="sec-title"><h3>💬 一句话情报</h3><span class="line"></span><span class="muted">知道就好 · 数据自动生成</span></div>
      <div class="card oneline-card"><ul>
{onelines}
      </ul></div>
    </section>
    <section>
      <div class="sec-title"><h3>📖 本期深读</h3><span class="line"></span><span class="muted">国际开源 · 国产开源 · AI×数据库 · 点卡片读全文</span></div>
      <div class="grid3 issue-grid">
{_deep_cards(d, act, cfg, cnt)}
      </div>
    </section>
    <section>
      <div class="sec-title"><h3>⚡ 本周速览</h3><span class="line"></span><span class="muted">只报变化（事件）· 发刊时冻结 · 状态请查工具页</span></div>
      <div class="grid2">
{_digest(d, act, cfg, cnt)}
      </div>
    </section>
  </main>""")

# ---------- 各期页 ----------

def issue_desc(d):
    first = (d.get("deep") or [{}])[0]
    return (strip_tags(first.get("summary") or "") or "数据库开源项目一周动态：看点、深读与速览。")[:150]

def gen_issue_page(d, act, cfg, ct, out_dir, cnt, nos):
    rel = URL_FIRST.format(n=d["no"])
    p = os.path.join(out_dir, *rel.lstrip("/").split("/"), "index.html")
    C.dump(p, C.page_legacy(cfg, f"数据库开源生态周刊 · 第 {d['no']} 期", issue_desc(d),
                            ct["base"] + rel, issue_html(d, act, cfg, cnt, nos), "/", EXTRA_CSS))
    return p

# ---------- 往期索引（旧 archive.html 原排版静态直出） ----------

def archive_html(issues, cfg, ct, out_dir):
    arts = []
    for no, d in sorted(issues.items(), reverse=True):
        th = d.get("theme") or {}
        chips = ""
        if th.get("cat"):
            chips += f'<span class="tag gray">类别轮值 · {C.esc(th["cat"])}</span>'
        if th.get("side"):
            chips += f'<span class="tag gray">{"国产主打" if th["side"] == "cn" else "国际主打"}</span>'
        if any((a.get("sec") == "ai") for a in d.get("deep") or []):
            chips += '<span class="tag">AI×数据库</span>'
        deep = "\n".join(
            f'<div class="it"><span class="sector">{C.esc(a.get("tag") or "")}</span>'
            f'<span class="t">{C.esc(a.get("title") or "")}</span>'
            f'<span class="fn mono">{C.esc(a.get("fn") or "")}</span></div>'
            for a in d.get("deep") or [])
        arts.append(f"""<article class="iss">
  <div class="iss-head">
    <span class="iss-no">第 {no} 期</span>
    <span class="small muted">{C.esc(d["date"])} · 快照 {C.esc(d.get("snap") or "—")}</span>
    <span class="tags">{chips}</span>
    <a class="more-btn" style="margin-left:auto" href="{C.esc(C.url(URL_FIRST.format(n=no), cfg))}">阅读本期 →</a>
  </div>
  <div class="iss-deep">
{deep}
  </div>
</article>""")
    body = f"""<section class="hero" style="padding:30px 0 6px">
    <h1>往期周刊</h1>
    <p>全部往期按期号倒序。深读按「类别轮值 + 板块主打 + 本周事件」三席选出；数字与速览冻结于发刊快照，往期所见即当时所记。</p>
  </section>
  <main>
    <section class="card">
      <div class="card-head"><h2>全部期刊<span class="hint">{len(issues)} 期</span></h2></div>
{"".join(arts)}
    </section>
  </main>
  <footer>往期周刊 · 共 {len(issues)} 期 · 内容与数据冻结于各期快照 · <a href="{C.esc(C.url("/", cfg))}">回到最新期 →</a></footer>"""
    p = os.path.join(out_dir, "archive.html")
    C.dump(p, C.page_legacy(cfg, "往期周刊 · 数据库开源生态观测",
                            "数据库开源生态周刊往期目录：每期看点、三篇深读、一周速览与生态体检，链接直达各期全文。",
                            ct["base"] + "/archive.html", body, "/archive.html", ARCHIVE_CSS))
    return p

# ---------- 入口 ----------

def gen_weekly(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "weekly"), ignore_errors=True)   # 清场：旧期页残留不留死链
    issues = load_weekly()
    nos = sorted(issues)
    act = active_fns(cfg)
    cnt = {"j_link": 0, "j_drop": 0, "c_link": 0, "g_link": 0}
    n_expect = 0
    for no in nos:
        gen_issue_page(issues[no], act, cfg, ct, out_dir, cnt, nos)
        n_expect += json.dumps(issues[no], ensure_ascii=False).count("data-fn=")   # dumps 转义引号，按 data-fn= 计
    assert cnt["j_link"] + cnt["j_drop"] == n_expect, \
        f"jump 重写数 {cnt['j_link']+cnt['j_drop']} != 源 data-fn 数 {n_expect}（正则漏抓，查属性顺序）"
    archive_html(issues, cfg, ct, out_dir)
    # 正文可索引门槛：每期剥 script/style 后 >=3000 字（P7.1 通过标准）
    for no in nos:
        t = io.open(os.path.join(out_dir, URL_FIRST.format(n=no).lstrip("/"), "index.html"),
                    encoding="utf-8").read()
        txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", "", t))
        n = len(" ".join(txt.split()))
        assert n >= 3000, f"第 {no} 期正文仅 {n} 字（<3000）"
    print(f"OK weekly_pages: {len(issues)} 期（/weekly/{{n}}/）+ archive.html（旧版排版静态直出）；"
          f"jump 真链 {cnt['j_link']}、降级 {cnt['j_drop']}；code 补链 {cnt['c_link']}；glance 补链 {cnt['g_link']}")
    return len(issues)

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_weekly(cfg, ct, out_dir)
