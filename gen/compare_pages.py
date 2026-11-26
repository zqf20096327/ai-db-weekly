# -*- coding: utf-8 -*-
"""compare_pages.py -- /compare/ 自选对比索引（P7.14 旧版排版壳 + P10.1 自选对比 + P12 方块分区结果）

版面=旧 compare.html 壳（hero + 「自选对比」卡）。P11（11-24 用户令）：删「热门对比」chips 与
「AI 对比解读」长文（deep 页不再生成；长文源 gen/compare_deep.json 保留未删）。
P12（11-26 用户令）：删速览头与差异速览，信息全部进表格——结果=吸顶身份条 + 六块方块卡
（定位与解读/能力与适配/规模与趋势/活跃与健康/同类对手/README 首段），块内三列并排表，
集合字段各栏全列（蓝芯片=仅此一方）；「只看不同」隐相同行+无差异整块收起+差异行整行高亮。
对比结果由 compare.js 渐进增强渲染，差异由规则逐项比对得出、不调 AI 不评优劣。

数据两份：浏览瘦索引（cfg["browse_json"]，gen_lists 产，与 /projects/ 共用：画像 15 键）+ 对比富字段分桶
（site/data/cmp/*.json，build_site 产，256 桶），本模块 write_cmp() 把后者落到 assets/cmp/{指纹}/。
两样就位才注入模块；缺失时本模块整段不出现、页面照常完整（verify 白名单在 build 侧对账）。
"""
import glob, hashlib, io, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

URL_INDEX = "/compare/"
CMP_BUCKETS = 256

def cmp_bucket(fn):
    """与 dbhub_collect tools/build_site.py 的 cmp_bucket 逐位同式（跨仓不 import，两处各写一份并注释）：
    FNV-1a 32 位按 UTF-16 码元，取低字节两位十六进制。verify 用它对账「fn 落在算出的桶里」。"""
    h, b = 0x811C9DC5, fn.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h = ((h ^ (b[i] | (b[i + 1] << 8))) * 0x01000193) & 0xFFFFFFFF
    return format(h & 0xFF, "02x")

def write_cmp(cfg, out_dir):
    """对比富字段分桶落站：site/data/cmp/*.json -> assets/cmp/{指纹}/{桶}.json，指纹写回 cfg["cmp_fp"]。
    指纹=按文件名排序的（桶名 + 内容 md5）再汇总：任一桶变=整目录换名，浏览器/CDN 缓存不串新旧；旧指纹目录清掉。"""
    src = os.path.join(cfg["data_root"], "data", "cmp")
    files = sorted(glob.glob(os.path.join(src, "*.json")))
    if not files:
        cfg.pop("cmp_fp", None); return 0
    h = hashlib.md5()
    for f in files:
        h.update(os.path.basename(f).encode() + b"\0" + hashlib.md5(io.open(f, "rb").read()).digest())
    fp = h.hexdigest()[:8]
    root = os.path.join(out_dir, "assets", "cmp")
    for d in glob.glob(os.path.join(root, "*")):            # 清旧指纹目录
        if os.path.basename(d) != fp: shutil.rmtree(d, ignore_errors=True)
    dst = os.path.join(root, fp); os.makedirs(dst, exist_ok=True)
    for f in files: shutil.copyfile(f, os.path.join(dst, os.path.basename(f)))
    cfg["cmp_fp"] = fp
    return len(files)

CMP_CSS = """  /* P10.1 自选对比（仅 compare 索引页携带） */
.cmp-form{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
.cmp-cell{flex:1;min-width:220px;position:relative}
.cmp-in{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;
        color:var(--ink);background:#fff}
.cmp-in:focus{outline:none;border-color:var(--accent)}
.cmp-menu{position:absolute;top:40px;left:0;right:0;background:#fff;border:1px solid var(--line);
          border-radius:8px;box-shadow:var(--shadow);z-index:6;max-height:264px;overflow:auto}
.cmp-menu a{display:flex;justify-content:space-between;gap:8px;padding:7px 10px;font-size:13px;color:var(--ink)}
.cmp-menu a:hover,.cmp-menu a.sel{background:var(--accent-soft)}

  /* P12 对比结果：吸顶身份条 + 六块方块卡 + 三列并排表（本页 .wrap 收口 1240：双列长文行长可控） */
.wrap{max-width:1240px}
#cmp-out{display:grid;gap:12px}                     /* 身份条 + 六块之间统一 12px 留白 */
.fdiv{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;
      margin-top:14px;border-top:1px solid var(--line);padding-top:11px;font-size:12px;color:var(--muted)}
.cmpx-tools{display:flex;align-items:center;gap:8px;flex:none}
.seg .n{font-weight:700;margin-left:4px}
.lg{display:inline-flex;align-items:center;margin-right:10px;white-space:nowrap}
.lg i{display:inline-block;width:6px;height:6px;margin-right:4px;border-radius:2px;
      vertical-align:1px;background:var(--accent)}
.lg .u{width:10px;height:10px;border-radius:3px;background:var(--accent-soft);border:1px solid var(--accent)}
.idbar{position:sticky;top:54px;z-index:15;display:grid;grid-template-columns:128px 1fr 1fr;
       background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}
.idbar .cell{display:flex;justify-content:space-between;align-items:baseline;gap:8px;padding:7px 10px 6px;min-width:0}
.idbar .cell .who{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.idbar .cell .who b{font-size:14px}
.idbar .cell .who .repo{font-weight:400;margin-left:6px;color:var(--muted)}
.idbar .cell .st{font-weight:700;white-space:nowrap}
.idbar .cell .st small{font-weight:400;color:var(--muted);font-size:12px}
.idbar .cell.a{border-top:2px solid var(--accent)}
.idbar .cell.b{border-top:2px solid var(--muted)}
.cmpx{display:grid;gap:12px}
.cmpblk{padding:14px 18px 10px}
.cmpblk[hidden]{display:none!important}
.bh{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:4px;flex-wrap:wrap}
.bh h2{font-size:16px;font-weight:700}
.gcnt{display:none;background:var(--accent-soft);color:var(--accent);font-size:12px;font-weight:700;
      border-radius:999px;padding:1px 9px}
.cmpx.difonly .gcnt{display:inline-block}
  /* 三列并排表：标签 128px / A / B 等宽；覆盖 app.css 旧 table.cmp（sticky 左列、td min-width） */
table.cmp{width:100%;border-collapse:collapse;table-layout:fixed}
.cmp th,.cmp td{text-align:left;font-size:13px;padding:8px 10px;border-bottom:1px solid var(--line);
                vertical-align:top;overflow-wrap:anywhere}
.cmp tr:last-child th,.cmp tr:last-child td{border-bottom:0}
.cmp td{min-width:0}
.cmp th:first-child{position:static;width:128px;background:transparent}
.cmp th.lab{width:128px;font-size:12px;font-weight:400;color:var(--muted);white-space:nowrap}
.cmp th.lab::before{content:"";display:inline-block;width:6px;height:6px;margin-right:7px;
                    vertical-align:1px;border-radius:2px}    /* 状态点只标差异；相同行隐形占位保标签纵对齐 */
.cmp tr.diff th.lab::before{background:var(--accent)}
.cmp tr.same th.lab::before{border:1px solid transparent}
.cmp tr.na th.lab::before{border:1px dashed var(--muted);width:5px;height:5px;border-radius:50%}
.cmp tr.na th.lab,.cmp tr.empty th.lab{color:#b3b8c2}
.cmp tbody tr:hover th,.cmp tbody tr:hover td{background:var(--accent-soft)}
.cmp td.txt{line-height:1.65}
.cmp td.txt p{margin:0}
.cmp td.txt ul{list-style:none;margin:0}
.cmp td.txt li{padding:1px 0 1px 13px;position:relative}
.cmp td.txt li::before{content:"•";position:absolute;left:2px;color:var(--muted)}
.tag.u{background:var(--accent-soft);color:var(--accent);border:1px solid var(--accent);line-height:18px}
.miss{color:var(--muted);font-size:12px;border-bottom:1px dashed var(--line)}
.cmp-num{display:flex;align-items:center;gap:10px;white-space:nowrap}
.cmp-num .bar{flex:0 0 120px;height:4px;background:var(--card);border:1px solid var(--line);
              border-radius:3px;overflow:hidden}
.cmp-num .bar i{display:block;height:100%;background:var(--muted);opacity:.55}
.cmp-num.win .bar i{background:var(--accent);opacity:1}
.cmp td.win,.cmp td.win *{font-weight:700}
.cmp td.win .muted{font-weight:400}
.cmp-note{font-size:12px;color:var(--muted);margin-top:1px}
.trend2{display:block;width:100%;height:92px}
.trend2-l{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;margin-top:2px;align-items:center}
.trend2-l i{display:inline-block;width:18px;height:0;border-top:2px solid var(--accent);vertical-align:3px;margin-right:5px}
.trend2-l i.b{border-top:2px dashed var(--muted)}
.rival{display:inline-flex;align-items:baseline;gap:5px;font-size:12px;padding:0 9px;border:1px solid var(--line);
       border-radius:999px;margin:0 4px 3px 0;background:var(--card);color:var(--ink)}
.rival:hover{border-color:var(--accent);color:var(--accent)}
.rival.nolink{cursor:default}
.rival .mono{font-size:11px;color:var(--muted)}
.rival.own{border-color:var(--accent);color:var(--accent)}
  /* 只看不同：隐相同/缺数据/解读正文/走势行；无差异整块 JS 置 hidden；差异行整行浅蓝高亮、共有芯片压暗 */
.cmpx.difonly tr.same,.cmpx.difonly tr.na,.cmpx.difonly tr.empty,.cmpx.difonly tr.txt,.cmpx.difonly tr.fig{display:none}
.cmpx tr[hidden]{display:none!important}   /* 手机端 table.cmp tr{display:block} 会盖掉 UA 的 [hidden]，这里显式压住 */
.cmpx.difonly tr.diff th.lab{background:var(--accent-soft)}
.cmpx.difonly tr.diff td{background:var(--accent-soft)}
.cmpx.difonly tr.diff td.win,.cmpx.difonly tr.diff td.win *{color:var(--accent)}
.cmpx.difonly .tag:not(.u){opacity:.45}
.cmpx.difonly .rival:not(.own){opacity:.45}
  /* 手机：身份条平置两格；块内表格上下堆叠——每个维度 = 标签 + A 值 + B 值（色条区分），不横滚找 B 列 */
@media(max-width:720px){
  .idbar{position:static;grid-template-columns:1fr 1fr;gap:8px;padding:8px}
  .idbar .sp{display:none}
  .idbar .cell .who .repo{display:none}
  .cmpblk{padding:12px 12px 8px}
  table.cmp,table.cmp tr,table.cmp th,table.cmp td{display:block;min-width:0}
  table.cmp tr{border-bottom:1px solid var(--line);padding:5px 0 7px}
  table.cmp tr > th{width:auto;white-space:normal;padding:5px 8px 3px}
  table.cmp td{border:0;padding:3px 8px 3px 12px;border-left:2px solid var(--line)}
  table.cmp td.ca{border-left-color:var(--accent)}
  table.cmp td[colspan]{border-left:0;padding-left:8px}
  table.cmp td[data-col]::before{content:attr(data-col);display:block;font-size:11px;color:var(--muted);line-height:1.5}
  .cmpx.difonly tr.diff td{color:var(--ink)}
  .cmp-num .bar{flex:1 1 60px;max-width:160px}
}
"""

def selfcmp_block(cfg, js_v):
    """P10.1 自选对比注入块：classList 置 .js + 模块骨架 + window.CMP 配置 + compare.js。
    P12：卡内下沿挂 #cmp-tools 工具条容器（全部/只看不同/复制链接，JS 有结果才亮），结果区
    #cmp-out 移出卡片外——六块方块卡与吸顶身份条不在表单卡肚子里，区域划分各自独立。
    浏览瘦索引指纹（cfg["browse_json"]）、对比富字段指纹（cfg["cmp_fp"]）与 compare.js 三样就位才注入——
    单跑本模块（无 lists 步 / 无 cmp 数据）时键缺失=静态照旧，verify 白名单在 build 侧对账。"""
    bj, fp = cfg.get("browse_json") or "", cfg.get("cmp_fp") or ""
    if not (bj and fp and js_v): return ""
    return (f'\n<script>document.documentElement.classList.add("js")</script>\n'
            f'<section class="card jsonly" id="selfcmp">\n'
            f'      <div class="card-head"><h2>⚖️ 自选对比</h2></div>\n'
            f'      <div class="cmp-form">\n'
            f'        <div class="cmp-cell"><input id="cmp-a" class="cmp-in" placeholder="项目 A：输入 owner/repo 或仓名" autocomplete="off">'
            f'<div class="cmp-menu" id="cmp-am" hidden></div></div>\n'
            f'        <button type="button" class="icon-btn" id="cmp-swap" title="交换双方">⇄</button>\n'
            f'        <div class="cmp-cell"><input id="cmp-b" class="cmp-in" placeholder="项目 B" autocomplete="off">'
            f'<div class="cmp-menu" id="cmp-bm" hidden></div></div>\n'
            f'        <button type="button" class="btn primary" id="cmp-go">对比</button>\n'
            f'      </div>\n'
            f'      <div class="fdiv" id="cmp-tools" hidden></div>\n'
            f'    </section>\n'
            f'<div id="cmp-out"></div>\n'
            f'<script>window.CMP={{base:{json.dumps(cfg.get("base_path", ""))},idx:{json.dumps(bj)},cmp:{json.dumps(fp)}}};</script>\n'
            f'<script src="{C.esc(C.url("/assets/compare.js", cfg))}?v={js_v}" defer></script>')

def index_body(cfg, js_v=""):
    return f"""<main>
    <section class="hero" style="padding:24px 0 8px">
      <h1>项目对比</h1>
      <p>任选两个数据库开源项目并排比较：解读结论、能力、适配库、规模趋势、活跃健康、同类对手逐项对照，
        相同与不同自动标出；结果写入网址，可分享。</p>
      <noscript><p class="small muted">「自选对比」需要浏览器开启 JavaScript；各项目的完整档案见 <a href="{C.esc(C.url("/projects/", cfg))}" style="color:var(--accent)">项目浏览</a>。</p></noscript>
    </section>{selfcmp_block(cfg, js_v)}
  </main>
  <footer>对比内容由规则逐项比对自动生成，不评优劣 · 解读层为 AI 依据项目 README 生成、证据行可在项目卡回查 · 数据每日更新。</footer>"""

# ---------- 入口 ----------

def gen_compare(cfg, ct, out_dir):
    shutil.rmtree(os.path.join(out_dir, "compare"), ignore_errors=True)   # 清场：P11 前的 deep 长文页一并清掉，不留死页
    n_cmp = write_cmp(cfg, out_dir)
    _js = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "compare.js"))
    js_v = hashlib.md5(io.open(_js, "rb").read()).hexdigest()[:8] if os.path.exists(_js) else ""
    idx = index_body(cfg, js_v)
    C.dump(os.path.join(out_dir, "compare", "index.html"),
           C.page_legacy(cfg, "项目对比 · 任选两个数据库开源项目并排比较",
                         "任选两个数据库开源项目并排对比：解读结论、能力标签、适配库、活跃健康、同类对手逐项对照，相同与不同自动标出。",
                         ct["base"] + URL_INDEX, idx, "/compare/", CMP_CSS))
    print(f"OK compare_pages: 索引（自选对比 + {n_cmp} 桶富字段）")
    return n_cmp

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_compare(cfg, ct, out_dir)
