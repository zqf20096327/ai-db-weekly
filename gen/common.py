# -*- coding: utf-8 -*-
"""common.py -- 站点页公共壳（模板层，零数据逻辑）

解耦纪律（见 gen/README.md）：
  1. 本模块只管「页面长什么样」；读什么数据、出多少页，归 list_pages/db_pages；
  2. URL 模式唯一权威 = 数据契约 site/urls.json（load_contract()），本模块不写死任何路径模式；
  3. 样式自带（内联），不依赖旧 assets/app.css——新页与旧页互不影响。
"""
import html, io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

def load_config():
    return json.load(io.open(os.path.join(HERE, "config.json"), encoding="utf-8"))

def load_contract(cfg=None):
    """site/urls.json = build_site 产物，URL 模式唯一权威。"""
    cfg = cfg or load_config()
    return json.load(io.open(os.path.join(cfg["data_root"], "urls.json"), encoding="utf-8"))

def esc(s): return html.escape(str(s), quote=True)

def url(path, cfg):
    """站内 URL 唯一出口：根绝对路径 + base_path 前缀（GH 镜像仓库名路径）。改 URL 前缀只动这里。"""
    return cfg.get("base_path", "").rstrip("/") + path

CSS = """
:root{--brand:#0F766E;--brand-soft:rgba(15,118,110,.08);--ink:#1F2937;--sub:#6B7280;--line:#E5E7EB;--bg:#F8FAFC}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:15px/1.7 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--brand);text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:20px 16px 48px}
.hd{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;padding:10px 0 14px;border-bottom:1px solid var(--line);margin-bottom:14px}
.hd .brand{font-size:17px;font-weight:700;color:var(--ink)}
nav{display:flex;flex-wrap:wrap;gap:2px 14px;font-size:14px}
nav a,.on{color:var(--sub)}nav a:hover{color:var(--brand)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 16px}
.chip{font-size:13px;padding:3px 11px;border:1px solid var(--line);border-radius:12px;background:#fff}
.chip.on{background:var(--brand);color:#fff;border-color:var(--brand)}
h1{font-size:21px;margin:4px 0 6px}.sub{color:var(--sub);font-size:13.5px;margin-bottom:14px}
ol.rows{list-style:none}
ol.rows li{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:11px 12px;border:1px solid var(--line);background:#fff;border-radius:8px;margin-bottom:8px}
.r-top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.r-name{font-weight:650;font-size:15.5px}
.r-fn{color:var(--sub);font-size:12.5px}
.r-stars{color:#B45309;font-size:13px;font-weight:600;white-space:nowrap}
.r-meta{grid-column:1/-1;color:var(--sub);font-size:13px}
.pager{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0;font-size:14px}
.pager a,.pager .cur,.pager .dot{padding:4px 11px;border:1px solid var(--line);border-radius:7px;background:#fff;color:var(--ink)}
.pager .cur{background:var(--brand);color:#fff;border-color:var(--brand)}
.pager .dot{border:none;background:none;color:var(--sub)}
.vs-grid{display:grid;grid-template-columns:1fr 40px 1fr;gap:0;margin:14px 0;align-items:stretch}
.vs-side{border:1px solid var(--line);background:#fff;border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:6px}
.vs-mid{display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--sub)}
.vs-why{color:var(--sub);font-size:13px}
.vs-score{margin-top:auto;font-size:12.5px;color:var(--brand);font-weight:600}
@media(max-width:720px){.vs-grid{grid-template-columns:1fr}.vs-mid{padding:8px 0}}
.ft{border-top:1px solid var(--line);margin-top:28px;padding-top:12px;color:var(--sub);font-size:12.5px}
h2{font-size:17px;margin:24px 0 10px}
h3{font-size:15.5px;margin:2px 0 4px}
.wk-nums{color:var(--sub);font-size:13px}
.wk-lede{display:flex;gap:10px;padding:10px 12px;border:1px solid var(--line);background:#fff;border-radius:8px;margin-bottom:8px;font-size:14px}
.wk-lede b{flex:none;color:var(--brand)}
.wk-deep{border:1px solid var(--line);background:#fff;border-radius:10px;padding:14px 16px;margin-bottom:14px}
.wk-deep p{margin:6px 0;font-size:14px}
.wk-tag{display:inline-block;font-size:12px;color:var(--brand);background:var(--brand-soft);border-radius:10px;padding:1px 9px;margin-bottom:6px}
.wk-panel{border-collapse:collapse;margin:8px 0;font-size:13px}
.wk-panel td{border:1px solid var(--line);padding:3px 10px}
.wk-card{font-size:13px}
.wk-ol{margin:0 0 0 18px;font-size:14px}
.wk-ol li{margin:4px 0}
.wk-hint{font-weight:400;color:var(--sub);font-size:12.5px;margin-left:8px}
.wk-glance{list-style:none;margin:0}
.wk-glance li{display:flex;gap:10px;flex-wrap:wrap;padding:6px 10px;border-bottom:1px dashed var(--line);font-size:13.5px}
.wk-fn{font-weight:600}
.wk-meta{color:var(--sub)}
.sev{color:#B91C1C;font-weight:600}
.g7{color:#B45309;font-weight:600}
.tag{font-size:12px;border:1px solid var(--line);border-radius:8px;padding:0 6px}
.tag.off{color:var(--brand);border-color:var(--brand)}
.tag.gray{color:var(--sub)}
.muted{color:var(--sub)}
"""

def nav_html(cfg, active):
    links = "".join(
        f'<a href="{esc(u)}"{" class=on" if u == active else ""}>{esc(t)}</a>' for u, t in cfg["nav"])
    return f'<nav>{links}</nav>'

def chips_html(cfg, cur_slug):
    out = []
    for slug, name in cfg["cats"]:
        on = ' on' if slug == cur_slug else ""
        out.append(f'<a class="chip{on}" href="{esc(url("/cat/" + slug + "/", cfg))}">{esc(name)}</a>')
    allon = ' on' if cur_slug == "all" else ""
    return (f'<a class="chip{allon}" href="{esc(url("/projects/", cfg))}">全部</a>') + "".join(out)

def item_row(it, cfg):
    stars = f'{it["stars"]:,}★' if isinstance(it.get("stars"), int) else ""
    meta = " · ".join(x for x in (it.get("lang"), (it.get("ol") or "")) if x)
    return (f'<li><div class="r-top"><a class="r-name" href="{esc(url(it["url"], cfg))}">{esc(it["name"])}</a>'
            f'<span class="r-fn">{esc(it["fn"])}</span><span class="r-stars">{stars}</span></div>'
            f'<div class="r-meta">{esc(meta)}</div></li>')

def pager(cur, pages, first_url, page_url):
    """页码窗：首/末恒显，当前±3，省略号折叠。first_url=第 1 页 URL（无页号），page_url=fn(n)。"""
    if pages <= 1: return ""
    def want(n): return n in (1, 2, pages - 1, pages) or abs(n - cur) <= 3
    seg, last = [], 0
    for n in range(1, pages + 1):
        if not want(n): continue
        if last and n - last > 1: seg.append('<span class="dot">…</span>')
        seg.append(f'<span class="cur">{n}</span>' if n == cur
                   else f'<a href="{esc(first_url if n == 1 else page_url(n))}">{n}</a>')   # 第 1 页链 first（P3 遗留 404 修复）
        last = n
    prev = f'<a href="{esc(first_url if cur == 2 else page_url(cur - 1))}">上一页</a>' if cur > 1 else ""
    nxt = f'<a href="{esc(page_url(cur + 1))}">下一页</a>' if cur < pages else ""
    return f'<div class="pager">{prev}{"".join(seg)}{nxt}</div>'

def page(cfg, title, desc, canon, body, active=""):
    """整页壳。canon 传绝对 URL（ct.base+路径）；分页第 2 页起传 None 不输出。
    镜像模式（cfg.mirror）：加 noindex——镜像站只做灾备不做收录，SEO 收敛到主站。"""
    c = f'<link rel="canonical" href="{esc(canon)}">\n' if canon else ""
    ni = '<meta name="robots" content="noindex">\n' if cfg.get("mirror") else ""
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{esc(title)}</title>\n"
            f'<meta name="description" content="{esc(desc)}">\n{ni}{c}'
            f"<style>{CSS}</style>\n</head>\n<body>\n"
            f'<div class="wrap">\n<div class="hd"><a class="brand" href="{esc(url("/", cfg))}">{esc(cfg["site_name"])}</a>{nav_html(cfg, active)}</div>\n'
            f"{body}\n"
            f'<div class="ft">数据每日更新 · <a href="{esc(url("/projects/", cfg))}">项目库</a> · '
            f'本项目档案由 dbhub 采集管线自动生成</div>\n</div>\n</body>\n</html>\n')

def dump(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    return len(s)

# ---------- 旧版设计壳（P7.13：周刊族页面恢复 assets/app.css 原排版） ----------

LEGACY_NAV = [("/", "周刊"), ("/archive.html", "往期周刊"), ("/projects/", "项目浏览"), ("/compare/", "项目对比")]

def page_legacy(cfg, title, desc, canon, body, cur_lk, extra_css=""):
    """旧版设计整页壳：header/nav 与 hero 分节排版全部沿用 assets/app.css 令牌体系。
    与 page() 的差别=外观壳（引用 assets/app.css）而非内联新样式；SEO 头（desc/canonical/
    镜像 noindex）两边一致。cur_lk=当前高亮导航项路径。"""
    c = f'<link rel="canonical" href="{esc(canon)}">\n' if canon else ""
    ni = '<meta name="robots" content="noindex">\n' if cfg.get("mirror") else ""
    links = "".join(
        f'<a class="lk{" on" if u == cur_lk else ""}" href="{esc(url(u, cfg))}">{esc(t)}</a>'
        for u, t in LEGACY_NAV)
    ex = f"<style>\n{extra_css}\n</style>\n" if extra_css else ""
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{esc(title)}</title>\n"
            f'<meta name="description" content="{esc(desc)}">\n{ni}{c}'
            f'<link rel="stylesheet" href="{esc(url("/assets/app.css", cfg))}">\n{ex}'
            "</head>\n<body>\n"
            f'<header><div class="wrap nav">\n'
            f'<a class="brand" href="{esc(url("/", cfg))}">开源生态<b>观测</b></a>\n{links}\n'
            f'<span class="spacer"></span>\n'
            f'<a class="icon-btn" href="{esc(url("/assets/qr-wechat.jpg", cfg))}" target="_blank" '
            'rel="noopener" title="联系作者 · 公众号">💬 联系我们</a>\n'
            "</div></header>\n"
            f'<div class="wrap">\n{body}\n</div>\n</body>\n</html>\n')
