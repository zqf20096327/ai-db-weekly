# -*- coding: utf-8 -*-
"""weekly_pages.py -- /weekly/{n}/ 每期静态页 + /archive.html 往期索引（P7.1/P7.2）

数据源 = 仓根 data/weekly.js（freeze_issue 编译产物，唯一全量源——issues/*.json 是缺字段底稿，
只有 no/date/theme/deep，无 lede/nums/glance/onelines/panel，故不读它）。
解析纪律：weekly.js 每行一条 WEEKLY[n] = {...};，逐行 json.loads，期号不一致/解析失败即断言崩。

内链纪律（本模块核心价值）：
  - 源数据里的 <a href="#" class="jump" data-fn="X">text</a> 是死链 -> 重写为 /p/X/ 真卡链；
  - fn 不在活跃分片集（归档/出池仓）-> 降级 <span> 纯文本，绝不留站内 404；
  - <code>owner/repo</code> 速览写法与 glance 行的 fn 字段按同一规则补链。
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
GLANCE_LAB = [("risk", "风险雷达"), ("rel", "发版动态"), ("gain", "涨星榜"), ("newb", "新项目")]

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
    """对一段源 HTML 做 jump 假链 + code 仓名两类重写。"""
    def jump_sub(m):
        fn, key = m.group(1), m.group(1).lower()
        if key in act:
            cnt["j_link"] += 1
            return f'<a href="{C.esc(C.url("/p/" + key + "/", cfg))}">{m.group(2)}</a>'
        cnt["j_drop"] += 1
        return f"<span>{m.group(2)}</span>"
    def code_sub(m):
        fn, key = m.group(1), m.group(1).lower()
        if key in act:
            cnt["c_link"] += 1
            return f'<a href="{C.esc(C.url("/p/" + key + "/", cfg))}"><code>{fn}</code></a>'
        return m.group(0)                       # 不是站内仓（或未收录）保持 code 原样
    return CODE_FN.sub(code_sub, JUMP.sub(jump_sub, html))

# ---------- 每期页 ----------

def deep_html(a, act, cfg, cnt):
    paras = "\n".join(f"<p>{relink(p, act, cfg, cnt)}</p>" for p in a.get("body") or [])
    panel = ("<table class=\"wk-panel\">" + "".join(
        f"<tr><td>{C.esc(k)}</td><td>{C.esc(v)}</td></tr>" for k, v in a["panel"]) + "</table>") if a.get("panel") else ""
    fn = a.get("fn") or ""
    card = (f'<p class="wk-card">项目档案：<a href="{C.esc(C.url("/p/" + fn.lower() + "/", cfg))}">{C.esc(fn)} 项目卡</a>'
            "（star 趋势 · 能力标签 · 适配数据库）</p>") if fn.lower() in act else ""
    return (f'<article class="wk-deep">\n<div class="wk-tag">{C.esc(a.get("tag") or "")}</div>\n'
            f'<h3>{C.esc(a.get("title") or "")}</h3>\n<p class="sub">{C.esc(a.get("summary") or "")}</p>\n'
            f"{paras}\n{panel}\n{card}\n</article>")

def glance_html(g, act, cfg, cnt):
    out = []
    for key, lab in GLANCE_LAB:
        blk = g.get(key)
        if not blk or not blk.get("rows"): continue
        rows = "\n".join(
            f'<li><span class="wk-fn">{fn_link(r.get("fn") or "", act, cfg, cnt)}</span>'
            f'<span class="wk-meta">{r.get("chip") or ""} {r.get("meta") or ""}</span></li>'
            for r in blk["rows"])
        out.append(f'<h2>{lab}<span class="wk-hint">{C.esc(blk.get("hint") or "")}</span></h2>\n'
                   f'<ul class="wk-glance">\n{rows}\n</ul>')
    return "\n".join(out)

def issue_sub(d):
    th = d.get("theme") or {}
    return " · ".join(x for x in (th.get("cat"), SIDE.get(th.get("side")), th.get("note")) if x)

def issue_body(d, act, cfg, cnt):
    parts = [f'<h1>数据库开源生态周刊 · 第 {d["no"]} 期</h1>',
             f'<p class="sub">{C.esc(d["date"])} · {C.esc(issue_sub(d))} · '
             f'<a href="{C.esc(C.url("/archive.html", cfg))}">往期目录</a></p>']
    nums = " · ".join(f"{C.esc(r[0])} {C.esc(r[1])}" for r in (d.get("nums") or [])[:6])   # 第 3 列是旧 JS 页锚链，弃
    if nums: parts.append(f'<p class="wk-nums">{nums}</p>')
    if d.get("lede"):
        parts.append("<h2>本期看点</h2>\n" + "\n".join(
            f'<div class="wk-lede"><b>{C.esc(lab)}</b><span>{relink(txt, act, cfg, cnt)}</span></div>'
            for lab, txt in d["lede"]))
    parts.append("<h2>深读</h2>")
    for a in d.get("deep") or []:
        parts.append(deep_html(a, act, cfg, cnt))
    if d.get("onelines"):
        parts.append('<h2>一周速览</h2>\n<ul class="wk-ol">\n'
                     + "\n".join(f"<li>{relink(t, act, cfg, cnt)}</li>" for t in d["onelines"])
                     + "\n</ul>")
    g = glance_html(d.get("glance") or {}, act, cfg, cnt)
    if g: parts.append(g)
    return "\n".join(parts)

def gen_issue_page(d, act, cfg, ct, out_dir, cnt):
    first = (d.get("deep") or [{}])[0]
    t_cut = strip_tags(first.get("title") or "")[:32]
    title = f'数据库开源生态周刊 第 {d["no"]} 期（{d["date"]}）：{t_cut}'
    desc = (strip_tags(first.get("summary") or "") or cfg["site_desc"])[:150]
    rel = URL_FIRST.format(n=d["no"])
    p = os.path.join(out_dir, *rel.lstrip("/").split("/"), "index.html")
    C.dump(p, C.page(cfg, title, desc, ct["base"] + rel, issue_body(d, act, cfg, cnt), ""))
    return p

# ---------- 往期索引 ----------

def archive_body(issues, cfg):
    rows = "\n".join(
        f'<li><div class="r-top"><a class="r-name" href="{C.esc(C.url(URL_FIRST.format(n=no), cfg))}">'
        f'第 {no} 期 · {C.esc(d["date"])}</a></div>'
        f'<div class="r-meta">{C.esc(issue_sub(d))} · 深读：'
        + " / ".join(C.esc(strip_tags(a.get("title") or "")[:24]) for a in (d.get("deep") or [])[:3])
        + "</div></li>"
        for no, d in sorted(issues.items(), reverse=True))
    return (f'<h1>往期周报 · 数据库开源生态周刊</h1>\n'
            f'<p class="sub">每周一期：看点、深读、一周速览、生态体检。共 {len(issues)} 期，'
            f'<a href="{C.esc(C.url("/projects/", cfg))}">项目档案库</a>每日更新。</p>\n'
            f'<ol class="rows">\n{rows}\n</ol>\n')

def gen_archive(issues, cfg, ct, out_dir):
    p = os.path.join(out_dir, "archive.html")
    C.dump(p, C.page(cfg, f"往期周报 · 数据库开源生态周刊（共 {len(issues)} 期）",
                     "数据库开源生态周刊往期目录：每期看点、三篇深读、一周速览与生态体检，链接直达各期全文。",
                     ct["base"] + "/archive.html", archive_body(issues, cfg), "/archive.html"))
    return p

# ---------- 入口 ----------

def gen_weekly(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "weekly"), ignore_errors=True)   # 清场：旧期页/legacy 拷进的 issues JSON 一并清掉
    issues = load_weekly()
    act = active_fns(cfg)
    cnt = {"j_link": 0, "j_drop": 0, "c_link": 0, "g_link": 0}
    n_expect = 0
    for no, d in sorted(issues.items()):
        gen_issue_page(d, act, cfg, ct, out_dir, cnt)
        n_expect += json.dumps(d, ensure_ascii=False).count("data-fn=")   # dumps 会把引号转义成 \"，按 data-fn= 计
    assert cnt["j_link"] + cnt["j_drop"] == n_expect, \
        f"jump 重写数 {cnt['j_link']+cnt['j_drop']} != 源 data-fn 数 {n_expect}（正则漏抓，查属性顺序）"
    gen_archive(issues, cfg, ct, out_dir)
    # 正文可索引门槛：每期剥 script/style 后 >=3000 字（P7.1 通过标准）
    import re as _re
    for no in sorted(issues):
        t = io.open(os.path.join(out_dir, URL_FIRST.format(n=no).lstrip("/"), "index.html"),
                    encoding="utf-8").read()
        txt = _re.sub(r"<[^>]+>", " ", _re.sub(r"<(script|style)[\s\S]*?</\1>", "", t))
        n = len(" ".join(txt.split()))
        assert n >= 3000, f"第 {no} 期正文仅 {n} 字（<3000）"
    print(f"OK weekly_pages: {len(issues)} 期（/weekly/{{n}}/）+ archive.html；"
          f"jump 真链 {cnt['j_link']}、降级 {cnt['j_drop']}；code 补链 {cnt['c_link']}；glance 补链 {cnt['g_link']}")
    return len(issues)

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_weekly(cfg, ct, out_dir)
