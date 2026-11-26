"use strict";
/* compare.js P12 -- /compare/ 自选对比（渐进增强）：任选两个部署项目，全字段并排对比。
   数据两份：① 浏览瘦索引 assets/browse-{指纹}.json（与 /projects/ 共用：名称/Star/语言/类别/适配库/维护/属性/日期）
             ② 对比富字段分桶 assets/cmp/{指纹}/{桶}.json（桶号 = fn 的 FNV-1a 低字节；每次对比按需取 2 桶）。
   结果 = 吸顶身份条 + 六块方块卡（定位与解读/能力与适配/规模与趋势/活跃与健康/同类对手/README 首段），
   块内三列并排表（标签 / A / B）：集合字段各栏全列，蓝芯片=仅此一方，不再合并「共有/仅A/仅B」行。
   P12（2026-11-26 用户令）：删速览头与差异速览、信息全部进表格；「只看不同」= 隐相同/缺数据/解读正文行 +
   无差异整块收起 + 差异行整行浅蓝高亮、赢家数字提蓝。差异由规则逐项比对得出，不调用 AI、不评优劣。
   行状态：diff 不同 / same 相同 / na 一边缺数据 / empty 两边都缺 / txt 解读正文（不判同异）/
   fig 走势图（双栏合体行）/ info 参考信息（两种模式都显示）。
   结果写入 hash（#a=owner/repo&b=owner/repo）可分享；页面其余部分零 JS 可用。 */
(function () {
  var B = window.CMP || {};
  var BASE = B.base || "";
  var q = function (s) { return document.querySelector(s); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function comma(n) { return isNum(n) ? String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",") : "—"; }
  function kfmt(n) { return typeof n === "number" && n >= 1000 ? Math.floor(n / 1000) + "k" : String(n); }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function parseDay(s) {
    return /^\d{4}-\d{2}-\d{2}/.test(s || "") ? new Date(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10))) : null;
  }
  function daysBetween(d0, d1) { return Math.round((d1 - d0) / 864e5); }
  function uniq(xs) { var o = {}, r = []; (xs || []).forEach(function (x) { if (x && !o[x]) { o[x] = 1; r.push(x); } }); return r; }

  /* @bucket */
  function bucket(s) {                       // FNV-1a 32 位取低字节；与 build_site.cmp_bucket / compare_pages.cmp_bucket 逐位同式
    var h = 0x811c9dc5 | 0;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return ("0" + ((h >>> 0) & 255).toString(16)).slice(-2);
  }
  /* @endbucket */

  var DATA = null, BY = {};                  /* fn 小写 -> 瘦索引条目 */
  var MENU_N = 12;

  /* ---------- 自动补全（子串命中；DATA 本身 Star 降序，取前 12 即热度序） ---------- */
  function suggest(v) {
    v = v.trim().toLowerCase();
    if (!v || !DATA) return [];
    var out = [];
    for (var i = 0; i < DATA.length && out.length < MENU_N; i++) {
      if (DATA[i].fn.toLowerCase().indexOf(v) >= 0) out.push(DATA[i]);
    }
    return out;
  }
  function menuHTML(list, cur) {
    return list.map(function (it, i) {
      return '<a data-i="' + i + '" href="#' + encodeURIComponent(it.fn) + '"' + (i === cur ? ' class="sel"' : "") +
        "><span>" + esc(it.fn) + '</span><span class="mono small muted">' + kfmt(it.stars) + "★</span></a>";
    }).join("");
  }

  /* 输入框状态机：sel=已选定条目（点选/回车才定）；菜单开着 ↑↓ 移动、Enter 选取，Esc 关 */
  function attach(id, menuId) {
    var inp = q("#" + id), menu = q("#" + menuId), list = [], cur = -1;
    function close() { menu.hidden = true; list = []; cur = -1; }
    function pick(it) { inp.value = it.fn; inp.sel = it; close(); }
    inp.addEventListener("input", function () {
      inp.sel = null;
      list = suggest(inp.value);
      if (!list.length) return close();
      cur = 0; menu.hidden = false; menu.innerHTML = menuHTML(list, cur);
    });
    inp.addEventListener("keydown", function (e) {
      if (menu.hidden) { if (e.key === "Enter") { e.preventDefault(); go(); } return; }
      if (e.key === "ArrowDown") { e.preventDefault(); cur = Math.min(cur + 1, list.length - 1); menu.innerHTML = menuHTML(list, cur); }
      else if (e.key === "ArrowUp") { e.preventDefault(); cur = Math.max(cur - 1, 0); menu.innerHTML = menuHTML(list, cur); }
      else if (e.key === "Enter") { e.preventDefault(); pick(list[Math.max(cur, 0)]); go(); }
      else if (e.key === "Escape") close();
    });
    menu.addEventListener("click", function (e) {
      var a = e.target.closest("a[data-i]");
      if (a) { e.preventDefault(); pick(list[+a.getAttribute("data-i")]); }
    });
    inp.sel = null; inp._close = close;
  }

  /* ---------- 富字段（按需取 2 桶；失败按「无数据」渲染，不中断对比） ---------- */
  var richP = {}, ASOF = "";
  function rich(fn) {
    var k = fn.toLowerCase();
    if (!B.cmp) return Promise.resolve(null);
    if (!richP[k]) {
      richP[k] = fetch(BASE + "/assets/cmp/" + B.cmp + "/" + bucket(k) + ".json")
        .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
        .then(function (d) { if (d && d.asof) ASOF = d.asof; return (d && d.items && d.items[k]) || null; })
        .catch(function (err) { console.warn("[compare] 对比数据加载失败:", k, err); richP[k] = null; return null; });
    }
    return richP[k];
  }

  /* ---------- 视图：瘦索引 + 富字段 -> 渲染用字段（缺项为 null / []） ---------- */
  var PERSONA = { build: "开发", use: "使用", ops: "运维" };
  var ECO = { tool: "工具", app: "应用", unclear: "未明" };
  var AIK = { mcp: "MCP 服务", rag: "RAG", text2sql: "Text2SQL", "dba-agent": "DBA Agent", other: "非 AI" };
  var INSTALL = { source: "源码", binary: "二进制", docker: "Docker", pypi: "PyPI", npm: "npm", helm: "Helm" };
  var MNT = { ok: "活跃", stale: "疑似停维", gone: "已归档" };
  var CONF = { high: ["高", "c2"], mid: ["中", "c1"], low: ["低", "c0"] };
  var DASH = '<span class="muted">—</span>';
  function miss(m) { return '<span class="miss">' + esc(m) + "</span>"; }
  function chips(xs, cls) {
    return (xs || []).map(function (x) {
      return '<span class="tag ' + (typeof cls === "function" ? cls(x) : (cls || "")) + '">' + esc(x) + "</span>";
    }).join("");
  }
  function ul(xs) {
    return xs && xs.length ? '<ul class="pts">' + xs.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" : DASH;
  }
  function para(s) { return s ? "<p>" + esc(s) + "</p>" : DASH; }

  function view(it, r) {
    var hasR = r != null;                    /* 富字段在不在 = 区分「未解读」与「解读过但为空」的依据 */
    r = r || {};
    var asof = parseDay(ASOF) || new Date();
    var pd = parseDay(it.pushed), cd = (it.created || "").slice(0, 10), cy = cd.slice(0, 4);
    var tr = (r.tr || []).filter(isNum), last = tr.length - 1;
    var d0 = parseDay(r.td0), d1 = parseDay(r.td1), ar = {};
    (r.ar || []).forEach(function (x) { if (x && x[0] && isNum(x[1])) ar[x[0]] = x[1]; });
    return {
      fn: it.fn, name: it.name || it.fn.split("/")[1], url: BASE + "/p/" + it.fn + "/",
      stars: isNum(it.stars) ? it.stars : null, lang: it.lang || null, cat: it.cat || null, dbs: it.dbs || [],
      ol: it.ol || "", mnt: it.mnt || "ok", off: !!it.off, hasR: hasR,
      created: cd, age: cy ? asof.getUTCFullYear() - +cy : null,
      pushed: pd ? it.pushed.slice(0, 10) : null, pushedAgo: pd ? daysBetween(pd, asof) : null,
      catTags: r.ct || [], persona: (r.pe || []).map(function (x) { return PERSONA[x] || x; }),
      eco: r.eco ? (ECO[r.eco] || r.eco) : null,
      ai: r.aik ? (AIK[r.aik] || r.aik) : (it.ai ? "AI 项目" : null),
      conf: r.cf || null, install: (r.ins || []).map(function (x) { return INSTALL[x] || x; }),
      lic: r.lic || null, sec: isNum(r.sec) ? r.sec : null,
      review: r.rv || "", hl: r.hl || [], uc: r.uc || [], caps: (r.cap || []).map(function (x) { return x[0]; }),
      ver: r.ver || null, vpub: r.vpub || null, n90: isNum(r.n90) ? r.n90 : null,
      c90: isNum(r.c90) ? r.c90 : null, ctr: isNum(r.ctr) ? r.ctr : null, mts: isNum(r.mts) ? r.mts : null,
      tr: tr, gain: last > 0 && tr[0] > 0 ? { d: tr[last] - tr[0], pc: 100 * (tr[last] - tr[0]) / tr[0] } : null,
      span: d0 && d1 ? daysBetween(d0, d1) : null, d0: r.td0 || null, d1: r.td1 || null,
      ar: ar, nw: r.nw && r.nw[0] ? r.nw : null, rm: r.rm || ""
    };
  }

  /* ---------- 走势图：近 30 天双线（各按自身区间缩放：看走势，不看绝对高度） ---------- */
  function polyline(pts, W, H, PAD, col, dashed) {
    var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), rng = (hi - lo) || 1;
    var xy = pts.map(function (v, i) {
      return (PAD + (W - 2 * PAD) * i / (pts.length - 1)).toFixed(1) + "," + (H - PAD - (H - 2 * PAD) * (v - lo) / rng).toFixed(1);
    }).join(" ");
    return '<polyline points="' + xy + '" fill="none" stroke="' + col + '" stroke-width="1.8"' +
      (dashed ? ' stroke-dasharray="5 4"' : "") + "/>";
  }
  function gainText(p) {
    return p.gain ? "<b>" + (p.gain.d >= 0 ? "+" : "") + comma(p.gain.d) + "</b>（" + (p.gain.d >= 0 ? "+" : "") + p.gain.pc.toFixed(1) + "%）" : "—";
  }
  function trend2(A, Bv) {
    var lab = function (p, cls) {
      return "<span><i class=\"" + cls + "\"></i>" + esc(p.name) + " 近 " + (p.span || "?") + " 天 " + gainText(p) + "</span>";
    };
    return '<svg class="trend2" viewBox="0 0 640 96" preserveAspectRatio="none" aria-hidden="true">' +
      '<line x1="8" y1="88" x2="632" y2="88" stroke="var(--line)" stroke-dasharray="2 4"/>' +
      (A.tr.length > 1 ? polyline(A.tr, 640, 96, 8, "var(--accent)", false) : "") +
      (Bv.tr.length > 1 ? polyline(Bv.tr, 640, 96, 8, "var(--muted)", true) : "") + "</svg>" +
      '<div class="trend2-l">' + lab(A, "a") + lab(Bv, "b") + "</div>";
  }

  function numcell(v, mx, m, win) {
    if (!isNum(v)) return m ? miss(m) : DASH;
    var w = mx ? Math.max(4, Math.round(100 * v / mx)) : 0;
    return '<div class="cmp-num' + (win && mx && v === mx ? " win" : "") + '"><span class="mono">' + comma(v) +
      '</span><span class="bar"><i style="width:' + w + '%"></i></span></div>';
  }

  /* ---------- 主体：吸顶身份条 + 六块方块卡 ----------
     每块 = card（标题 + 「N 处不同」芯片）内一张三列表（标签/A/B）。计数（全部 N / 只看不同 M）
     回填表单卡内的工具条 #cmp-tools；「只看不同」按 .cmpblk 内有无 tr.diff 决定整块去留。 */
  function idbar(A, Bv) {
    var cell = function (p, cls) {
      return '<div class="cell ' + cls + '"><span class="who"><b>' + esc(p.name) + "</b>" +
        '<a class="repo" href="' + esc(p.url) + '">' + esc(p.fn) + '</a></span><span class="st">' + comma(p.stars) +
        "<small> ★</small></span></div>";
    };
    return '<div class="idbar"><div class="sp"></div>' + cell(A, "a") + cell(Bv, "b") + "</div>";
  }

  function build(A, Bv) {
    var a = A.name, b = Bv.name, blocks = [], cur = null, nAll = 0, nDiff = 0;
    function block(t) { cur = { t: t, rows: [], n: 0 }; blocks.push(cur); }
    function push(kind, html) { cur.rows.push(html); nAll++; if (kind === "diff") { cur.n++; nDiff++; } }
    function put(kind, label, ca, cb, isTxt, winSide) {   // 双值行：标签列 + A 列 + B 列（手机端 data-col 小字前缀；winSide=赢家侧 td.win）
      var ta = ' class="ca' + (isTxt ? " txt" : "") + (winSide === "a" ? " win" : "") + '"';
      var tb = ' class="cb' + (isTxt ? " txt" : "") + (winSide === "b" ? " win" : "") + '"';
      push(kind, '<tr class="' + kind + '"><th class="lab">' + esc(label) + "</th>" +
        '<td' + ta + ' data-col="' + esc(a) + '">' + ca + '</td><td' + tb + ' data-col="' + esc(b) + '">' + cb + "</td></tr>");
    }
    function putfull(kind, label, inner) {       // 合体行：走势图等双栏内容
      push(kind, '<tr class="' + kind + '"><th class="lab">' + esc(label) + '</th><td colspan="2">' + inner + "</td></tr>");
    }
    var state = function (pa, pb, eq) { return !pa && !pb ? "empty" : pa && pb ? (eq ? "same" : "diff") : "na"; };

    function scalar(label, va, vb, ta, tb, m) {          // ta/tb = 展示文案（缺省取原值）；m = 缺数据时缺侧文案
      ta = ta != null ? ta : va; tb = tb != null ? tb : vb;
      var pa = ta != null && ta !== "", pb = tb != null && tb !== "";
      var k = state(pa, pb, ta === tb);
      put(k, label, pa ? esc(ta) : (k === "na" ? miss(m) : DASH), pb ? esc(tb) : (k === "na" ? miss(m) : DASH));
    }
    function sets(label, sa, sb, m) {            // 集合行：各栏全列，仅此一方=蓝芯片；一边缺数据=na（「无」≠「未解读」）
      sa = uniq(sa); sb = uniq(sb);
      var ka = sa.length > 0, kb = sb.length > 0;
      if (!ka && !kb) { putfull("empty", label, DASH); return; }
      if (!ka || !kb) {
        var hasR = ka ? Bv.hasR : A.hasR;       // 缺的一边：解读过=「无」（计差异）；没解读=na（不计）
        var none = hasR ? '<span class="muted">无</span>' : miss(m);
        put(hasR ? "diff" : "na", label, ka ? chips(sa, "u") : none, kb ? chips(sb, "u") : none);   // 有值侧全蓝：对面没有=全部仅此一方
        return;
      }
      var inB = {}, inA = {};
      sb.forEach(function (x) { inB[x] = 1; }); sa.forEach(function (x) { inA[x] = 1; });
      var same = sa.length === sb.length && sa.every(function (x) { return inB[x]; });
      put(same ? "same" : "diff", label,
        chips(sa, function (x) { return inB[x] ? "" : "u"; }),
        chips(sb, function (x) { return inA[x] ? "" : "u"; }));
    }
    function ratio(label, x, y, thr, mode, m, note) {       // 数值行：行内最高加粗+比例条；超阈值才计「不同」
      var pa = isNum(x), pb = isNum(y), mx = Math.max(pa ? x : 0, pb ? y : 0), big = null, lo = Math.min(x, y);
      if (pa && pb && mx > 0 && (lo === 0 || (mode === "abs" ? Math.abs(x - y) >= 2 : mx / lo >= thr))) big = x >= y ? "a" : "b";
      var k = state(pa, pb, big === null), win = k === "diff";
      var cell = function (v, w) {
        return numcell(v, mx, m, w) + (isNum(v) && note ? '<div class="cmp-note">' + esc(note) + "</div>" : "");
      };
      put(k, label, cell(x, win && big === "a"), cell(y, win && big === "b"), false, win ? big : null);
    }
    function gainRow() {                        // 区间涨幅：独立成行（P12；速览时代只是汇总盒里的一枚 chip）
      var gA = A.gain, gB = Bv.gain;
      var cell = function (p) {
        return gainText(p) + (p.d0 && p.d1 ? '<div class="cmp-note">近 ' + (p.span || "?") + " 天 · " +
          esc(p.d0) + " → " + esc(String(p.d1).slice(5)) + "</div>" : "");
      };
      if (!gA && !gB) { putfull("empty", "区间涨幅", DASH); return; }
      if (!gA || !gB) { put("na", "区间涨幅", gA ? cell(A) : miss("无趋势数据"), gB ? cell(Bv) : miss("无趋势数据")); return; }
      var k = Math.abs(gA.pc - gB.pc) >= 0.5 ? "diff" : "same";
      put(k, "区间涨幅", cell(A), cell(Bv), false, k === "diff" ? (gA.pc >= gB.pc ? "a" : "b") : null);
    }
    function rivalRow() {                       // 同类对手：各栏全列，蓝描边=仅此一方的对手；一边没擂台数据=na
      var ra = {}, rb = {}, addAll = function (src, dst, skip) {
        Object.keys(src).forEach(function (k) { if (k.toLowerCase() !== skip) dst[k] = src[k]; });
      };
      addAll(A.ar, ra, Bv.fn); addAll(Bv.ar, rb, A.fn);
      var ka = Object.keys(ra).length, kb = Object.keys(rb).length;
      if (!ka && !kb) { putfull("empty", "同类对手", DASH); return; }
      var common = Object.keys(ra).filter(function (k) { return rb[k] != null; });
      var side = function (src) {
        return Object.keys(src).sort().map(function (x) {
          var t = BY[x.toLowerCase()], own = common.indexOf(x) < 0;
          return '<a class="rival' + (own ? " own" : "") + (t ? '" href="' + esc(BASE + "/p/" + t.fn + "/") : ' nolink"') +
            '"><b>' + esc(x.split("/")[1] || x) + '</b><span class="mono">' + Math.max(ra[x] || 0, rb[x] || 0).toFixed(2) + "</span></a>";
        }).join("") || '<span class="muted">—</span>';
      };
      var same = ka > 0 && kb > 0 && ka === kb &&
        Object.keys(ra).every(function (k) { return rb[k] != null; });
      put(!ka || !kb ? "na" : (same ? "same" : "diff"), "同类对手", side(ra), side(rb));
    }

    /* 块 1：定位与解读 */
    block("定位与解读");
    scalar("一句话定位", A.ol, Bv.ol, null, null, "无定位");
    scalar("类别", A.cat, Bv.cat, null, null, "未分类");
    sets("多标签", A.catTags, Bv.catTags, "未解读");
    sets("面向谁", A.persona, Bv.persona, "未解读");
    scalar("生态位", A.eco, Bv.eco, null, null, "未解读");
    scalar("AI 类型", A.ai, Bv.ai, null, null, "未解读");
    var conf = function (p) { return p.conf && CONF[p.conf] ? '<span class="conf ' + CONF[p.conf][1] + '"></span>' + CONF[p.conf][0] : null; };
    put("info", "解读置信度", conf(A) || DASH, conf(Bv) || DASH);   // 置信度=解读可信度，不是项目差异：两模式都显示、不计数
    scalar("主语言", A.lang, Bv.lang, null, null, "无语言数据");
    scalar("许可证", A.lic || "未声明", Bv.lic || "未声明");
    put("txt", "综述", para(A.review), para(Bv.review), true);
    put("txt", "亮点", ul(A.hl), ul(Bv.hl), true);
    put("txt", "适用场景", ul(A.uc), ul(Bv.uc), true);

    /* 块 2：能力与适配 */
    block("能力与适配");
    sets("能力标签", A.caps, Bv.caps, "未解读");
    sets("适配数据库", A.dbs, Bv.dbs, "无适配数据");

    /* 块 3：规模与趋势 */
    block("规模与趋势");
    ratio("Star", A.stars, Bv.stars, 1.15, "pct");
    gainRow();
    putfull(A.tr.length > 1 || Bv.tr.length > 1 ? "fig" : "empty", "近期 Star 走势", trend2(A, Bv));
    scalar("创建于", A.created.slice(0, 4), Bv.created.slice(0, 4),
      A.age !== null ? A.created.slice(0, 7) + "（" + A.age + " 年）" : null,
      Bv.age !== null ? Bv.created.slice(0, 7) + "（" + Bv.age + " 年）" : null);
    ratio("README 被引用", A.mts, Bv.mts, 2, "times", "未采集", "近 90 天全池 README 提及次数");

    /* 块 4：活跃与健康 */
    block("活跃与健康");
    var ma = A.mnt, mb = Bv.mnt, mk = ma === mb ? "same" : "diff";
    var st = function (mm, p) {
      return (mm !== "ok" ? '<span class="tag st-warn">' + MNT[mm] + "</span>" : MNT[mm]) +
        (p.pushedAgo !== null ? '<div class="cmp-note">' + esc(p.pushed) + " · " + p.pushedAgo + " 天前推送</div>" : "");
    };
    put(mk, "维护状态", st(ma, A), st(mb, Bv));
    ratio("90 天提交", A.c90, Bv.c90, 1.5, "times");
    ratio("贡献者", A.ctr, Bv.ctr, 1.5, "times");
    ratio("90 天发版", A.n90, Bv.n90, 2, "abs");
    put("info", "最新发版",                                 // 版本号两边必然不同：只展示不比对
      A.ver ? '<b class="mono">' + esc(A.ver) + "</b> · " + esc((A.vpub || "").slice(5) || "—") : DASH,
      Bv.ver ? '<b class="mono">' + esc(Bv.ver) + "</b> · " + esc((Bv.vpub || "").slice(5) || "—") : DASH);
    sets("安装方式", A.install, Bv.install, "未解读");
    scalar("安全通告", A.sec, Bv.sec, A.sec != null ? A.sec + " 条" : null, Bv.sec != null ? Bv.sec + " 条" : null);
    scalar("归属", A.off, Bv.off, A.off ? "官方" : "社区", Bv.off ? "官方" : "社区");
    var nw = function (p) {
      return p.nw ? '<b class="mono">' + esc(p.nw[0]) + '</b> <span class="muted small">' + esc(p.nw[1]) + "</span>" +
        '<div class="clamp">' + esc(p.nw[2]) + "</div>" : '<span class="muted">近 90 天无发版</span>';
    };
    put("txt", "最近动态", nw(A), nw(Bv), true);

    /* 块 5：同类对手 */
    block("同类对手");
    rivalRow();

    /* 块 6：README 首段 */
    block("README 首段");
    put("txt", "README 首段", para(A.rm), para(Bv.rm), true);

    var html = idbar(A, Bv) + '<div class="cmpx" id="cmpx">' + blocks.map(function (bl) {
      return '<section class="card cmpblk"><div class="bh"><h2>' + esc(bl.t) + "</h2>" +
        '<span class="gcnt">' + bl.n + " 处不同</span></div>" +
        '<table class="cmp"><tbody>' + bl.rows.join("") + "</tbody></table></section>";
    }).join("") + "</div>";
    return { html: html, nAll: nAll, nDiff: nDiff };
  }

  /* ---------- 「只看不同」：类名切换 + 无差异整块收起 ---------- */
  var MODE = "all";
  function applyMode() {
    var box = q("#cmpx");
    if (!box) return;
    var dif = MODE === "diff";
    box.classList.toggle("difonly", dif);
    box.querySelectorAll(".cmpblk").forEach(function (blk) {
      blk.hidden = dif && !blk.querySelectorAll("tr.diff").length;   // 无差异整块收起
    });
    document.querySelectorAll("#cmp-mode span[data-m]").forEach(function (s) {   // 工具条在 #cmpx 外（表单卡内），从文档找
      s.className = s.getAttribute("data-m") === MODE ? "on" : "";
    });
  }
  function toolsHTML(nAll, nDiff) {           // 工具条渲染进表单卡下沿的静态 #cmp-tools（结果不在=整条隐藏）
    return '<span>数据截至 ' + esc(ASOF || "—") +
      '<span class="lg"><i></i>不同</span><span class="lg"><i class="u"></i>仅此一方</span></span>' +
      '<span class="cmpx-tools"><span class="seg" id="cmp-mode" role="group" aria-label="显示范围">' +
      '<span data-m="all" class="' + (MODE === "all" ? "on" : "") + '">全部<span class="n">' + nAll + "</span></span>" +
      '<span data-m="diff" class="' + (MODE === "diff" ? "on" : "") + '">只看不同<span class="n">' + nDiff + "</span></span>" +
      '</span><button type="button" class="btn" id="cmp-copy">复制链接</button></span>';
  }
  function copyLink(btn) {
    var url = location.href, done = function () { var t = btn.textContent; btn.textContent = "已复制"; setTimeout(function () { btn.textContent = t; }, 1500); };
    var fallback = function () {
      var ta = document.createElement("textarea");
      ta.value = url; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { /* 剪贴板不可用：链接仍在地址栏 */ }
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, fallback);
    else fallback();
  }

  /* ---------- 入口 ---------- */
  function hint(msg) {
    q("#cmp-out").innerHTML = '<p class="small muted" style="margin-top:10px">' + esc(msg) + "</p>";
    q("#cmp-tools").hidden = true;            // 无结果（换对/出错）：工具条一并藏起
  }
  function resolve(v) { return v ? BY[v.trim().toLowerCase()] || null : null; }

  var seq = 0;
  function go() {
    var va = q("#cmp-a").value, vb = q("#cmp-b").value;
    var ia = q("#cmp-a").sel || resolve(va), ib = q("#cmp-b").sel || resolve(vb);
    if (!va.trim() && !vb.trim()) return hint("先输入项目 A 和项目 B，再点「对比」。");
    if (!ia) return hint("项目 A 不在站内部署集内（只收录归属过 17 库的项目；输入 owner/repo 或仓名）");
    if (!ib) return hint("项目 B 不在站内部署集内");
    if (ia.fn === ib.fn) return hint("两边是同一个项目");
    q("#cmp-a").value = ia.fn; q("#cmp-b").value = ib.fn;
    hint("正在载入 " + ia.name + " 与 " + ib.name + " 的解读数据…");
    var my = ++seq;
    Promise.all([rich(ia.fn), rich(ib.fn)]).then(function (rs) {
      if (my !== seq) return;                    // 期间又发起了别的对比：丢弃过期结果
      var r = build(view(ia, rs[0]), view(ib, rs[1]));
      q("#cmp-out").innerHTML = r.html;
      q("#cmp-tools").hidden = false;
      q("#cmp-tools").innerHTML = toolsHTML(r.nAll, r.nDiff);
      applyMode();
      history.replaceState(null, "", location.pathname + (location.search || "") +
        "#a=" + encodeURIComponent(ia.fn) + "&b=" + encodeURIComponent(ib.fn));
    });
  }
  function fromHash() {
    var m = location.hash.match(/[#&]a=([^&]+)&b=([^&]+)/);
    if (!m) return false;
    var a, b;
    try { a = decodeURIComponent(m[1]); b = decodeURIComponent(m[2]); } catch (e) { return false; }
    q("#cmp-a").value = a; q("#cmp-b").value = b;
    var ia = resolve(a), ib = resolve(b);
    q("#cmp-a").sel = ia; q("#cmp-b").sel = ib;
    return !!(ia && ib && ia.fn !== ib.fn);
  }

  q("#cmp-go").addEventListener("click", go);
  q("#cmp-swap").addEventListener("click", function () {
    var a = q("#cmp-a"), b = q("#cmp-b"), t = a.value; a.value = b.value; b.value = t;
    var s = a.sel; a.sel = b.sel; b.sel = s;
    if (q("#cmp-out").querySelector("table")) go();
  });
  q("#cmp-tools").addEventListener("click", function (e) {
    var s = e.target.closest("#cmp-mode span[data-m]");
    if (s) { MODE = s.getAttribute("data-m"); applyMode(); return; }
    if (e.target.closest("#cmp-copy")) copyLink(e.target.closest("#cmp-copy"));
  });
  window.addEventListener("hashchange", function () { if (fromHash()) go(); });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".cmp-cell")) { q("#cmp-a")._close(); q("#cmp-b")._close(); }
  });
  attach("cmp-a", "cmp-am"); attach("cmp-b", "cmp-bm");
  hint("输入项目 A、B 后点「对比」。");

  /* 启动：取瘦索引 -> hash 预填（分享链直达结果） */
  fetch(BASE + "/assets/" + B.idx)
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      DATA = data;
      data.forEach(function (it) { BY[it.fn.toLowerCase()] = it; });
      if (fromHash()) go();
    })
    .catch(function (err) { console.warn("[compare] 瘦索引加载失败，保持静态索引：", err); hint("项目索引加载失败，请刷新重试。"); });
})();
