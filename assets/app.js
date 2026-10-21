/* 数据库开源生态观测 · demo —— 共享基座：数据层 / hash 路由 / chips / 抽屉 / 分页 / 主题 / 关注 */
"use strict";

/* ---------- 数据层 ---------- */
const I = { FN:0, DESC:1, LANG:2, ST:3, FK:4, DB:5, DBS:6, CAT:7, CC:8,
            AIK:9, O:10, SEC:11, CR:12, PU:13, C7:14, C90:15, RV:16,
            RD:17, SN:18, SW:19, CT:20, G7:21, EV:22, LIC:23, HP:24,
            ARC:25, SL:26, RP:27, STAT:28, ECO:29, PF:30, CS:31 };
/* AI 类型可能是逗号串（AI 解读支持多类型）；"ai" 为伞形值 = 仅有 AI 标记无具体类型 */
function aikHas(r, kind) {
  const k = r[I.AIK];
  if (!k) return false;
  return kind === "ai" || k.split(",").includes(kind);
}
function aikLabel(r) {
  const parts = (r[I.AIK] || "").split(",").filter(x => x && x !== "ai");
  return parts.length ? "AI·" + parts.join("·") : (r[I.AIK] ? "AI 工具" : "");
}
/* AI 解读的维护状态 / 生态位 / 人群 */
const STAT_CN = { active: "活跃", maintenance: "维护中", experimental: "实验性",
                  deprecated: "已弃用", discontinued: "已停维" };
const STAT_CLS = { active: "ok", maintenance: "warn", experimental: "info",
                   deprecated: "sev", discontinued: "sev" };
const ECO_CN = { tool: "生态工具", app: "纯应用" };
const PF_CN = { use: "用库", ops: "管库", build: "造库" };
function statusTag(r) {
  const s = r[I.STAT];
  if (!s) return "";
  return `<span class="tag st-${STAT_CLS[s]}" title="AI 解读的维护状态">${STAT_CN[s]}</span>`;
}
/* 快照日期（YYYYMMDD）往前推 N 天，返回 YYYY-MM-DD（用于"事件"筛选） */
function snapCut(days) {
  const d = new Date(`${M.snap.slice(0,4)}-${M.snap.slice(4,6)}-${M.snap.slice(6,8)}`);
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}
/* let 而非 const：index.html 不再同步直载 pool.js（gzip 后仍 2.5MB 级、拖慢首屏），改为渲染同时
   lazyPool() 后台注入、到货 rebindPool() 重绑本组；其余三页 pool.js 仍在 app.js 之前加载，一次绑定到位 */
let P = window.POOL || [];
let M = window.META || {};
let DBS = M.dbOrder || [];
let CATS = M.catOrder || [];
const NA = "未归类";
const GH = fn => "https://github.com/" + fn;

let _byFn = null;
function byFn(fn) {
  if (!_byFn) { _byFn = {}; for (const r of P) _byFn[r[I.FN]] = r; }
  return _byFn[fn];
}
const isNA = r => !r[I.DB];

/* ---------- pool 按需加载（仅 index.html 使用；其余页面同步直载不经过这里） ----------
   页面删掉 <script src="data/pool.js">，内联脚本调 lazyPool() 注册后台下载（load 事件后开拉，
   不阻塞渲染也不拖住 window.load），到货 → rebindPool() 重绑 P/M/DBS/CATS/NEW_CUT 并清
   _byFn 空表缓存，再补画打开中的项目抽屉。
   失败 1.5s 后自动重试一次；仍失败置 _poolFail（占位文案提示），下次开抽屉即再重试 */
let _poolTask = null, _poolFail = false;
function poolPending() { return window.POOL === undefined; }
function rebindPool() {
  P = window.POOL || [];
  M = window.META || {};
  DBS = M.dbOrder || [];
  CATS = M.catOrder || [];
  NEW_CUT = typeof M.snap === "string" ? newCutoff() : "0000";
  _byFn = null;   /* 空索引表一旦缓存，byFn 将永远查无此人 */
}
function lazyPool() {
  if (window.POOL !== undefined) { rebindPool(); return Promise.resolve(); }
  if (_poolTask) return _poolTask;
  _poolFail = false;
  _poolTask = new Promise((resolve, reject) => {
    const tryLoad = retried => {
      const s = document.createElement("script");
      s.src = "data/pool.js";
      const fail = () => {
        s.remove();
        if (!retried) setTimeout(() => tryLoad(true), 1500);   /* 弱网抖动，重试一次 */
        else { _poolFail = true; _poolTask = null; reject(new Error("pool.js 加载失败")); }
      };
      s.onload = () => {
        if (window.POOL === undefined) return fail();   /* 200 但内容无效（截断/代理页）：按失败重试，防永久"加载中" */
        rebindPool(); refreshPdBody(); resolve();
      };
      s.onerror = fail;
      document.head.appendChild(s);
    };
    /* load 前注入的动态 script 会拖住 window.load——弱网 2.5MB 下标签页转圈数分钟
       （页面其实早已可用）。等 load 事件后再开拉；抽屉/搜索此间走占位与降级不受影响 */
    if (document.readyState === "complete") tryLoad(false);
    else window.addEventListener("load", () => tryLoad(false), { once: true });
  });
  return _poolTask;
}

/* ---------- detail 按需分片加载 ---------- */
/* detail（AI 解读/README 摘录）按 djb2 hash 分 512 片存于 data/d/s{n}.json，
   点开项目只取所在片（~40KB），合并进 window.DETAIL 供 dOf/D[fn] 读取。
   算法与 build/emit.py 的 shard_of 逐字符一致（selftest 抽样对答案钉死）。 */
const SHARD_N = 512;
function shardOf(fn) {
  let h = 5381;
  for (let i = 0; i < fn.length; i++) h = (h * 33 + fn.charCodeAt(i)) >>> 0;
  return h % SHARD_N;
}
const _shards = new Map();   // 片号 -> Promise<该片对象>（已合并则同步值）
function loadShard(n) {
  if (_shards.has(n)) return _shards.get(n);
  const p = fetch(`data/d/s${n}.json`)
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(obj => {
      if (!window.DETAIL) window.DETAIL = {};
      Object.assign(window.DETAIL, obj);
      return obj;
    })
    .catch(() => { _shards.delete(n); return {}; });   /* 失败置空可重试；调用方按未就绪处理 */
  _shards.set(n, p);
  return p;
}
function loadDetailFor(fns) {
  return Promise.all([...new Set(fns.map(shardOf))].map(loadShard));
}
/* 片到货后：抽屉若仍开着且正文含项目详情段（.pd-body），就地补全重画 */
function refreshPdBody() {
  const node = document.querySelector("#drawer-body .pd-body");
  if (node && el("drawer").classList.contains("open"))
    node.outerHTML = projectDetailHtml(node.dataset.fn)
      || '<div class="empty"><div class="big">🕳️</div>该项目已不在当前收录中（往期记录）</div>';   /* index 窗口期点往期行：pool 到货后占位符换诚实文案 */
}
const dbList = r => (isNA(r) ? [NA] : (r[I.DBS] && r[I.DBS].length ? r[I.DBS] : [r[I.DB]]));

/* ---------- 工具 ---------- */
const el = id => document.getElementById(id);
function esc(s) { return String(s == null ? "" : s)
  .replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function fmtK(n) {
  n = n || 0;
  if (Math.abs(n) >= 10000) return (n / 1000).toFixed(0) + "k";
  if (Math.abs(n) >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}
function act(r) {  // 活跃度指数（口径公开）：c7×2 + 近30天发版×15 + 贡献者档(≤20)，封顶100
  const a = (r[I.C7] || 0) * 2 + ((r[I.RD] != null && r[I.RD] <= 30) ? 15 : 0)
          + Math.min(20, Math.floor((r[I.CT] || 0) / 20));
  return Math.min(100, a);
}
function idxScore(r) { return Math.min(r[I.G7] || 0, 200) * 2 + act(r) * 3
                             + Math.log10((r[I.ST] || 0) + 1) * 15; }
const SEV_CN = { critical: "严重", high: "高危", moderate: "中危", low: "低危" };
function sevBadge(sw) {
  if (!sw) return "";
  const cls = sw === "critical" || sw === "high" ? "" : " " + sw;
  return `<span class="sev${cls}">${SEV_CN[sw] || sw}</span>`;
}
function confDot(r) {
  const cc = r[I.CC];
  const src = r[I.CS] === "ai" ? "AI 解读" : (cc == 2 ? "topic 主题" : cc == 1 ? "关键词" : "待归类");
  return `<span class="conf c${cc}" title="分类置信度：${cc==2?"高":cc==1?"中":"低"}（${src}）"></span>`;
}
/* 维护状态：AI 判定(弃用/停维) > archived > 疑似停维(★≥100 且 90 天零提交) > 活跃/未知 */
function maint(r) {
  if (r[I.STAT] === "deprecated" || r[I.STAT] === "discontinued") return "dep";
  if (r[I.ARC]) return "arc";
  if (r[I.ST] >= 100 && r[I.C90] === 0) return "stale";
  return "";
}
function maintBadge(r) {
  const m = maint(r);
  if (m === "dep") return `<span class="bdg dep" title="AI 解读判定：README 已声明弃用/停维">${STAT_CN[r[I.STAT]]}</span>`;
  if (m === "arc") return '<span class="bdg arc" title="仓库已在 GitHub 标记归档，不再维护">已归档</span>';
  if (m === "stale") return '<span class="bdg stale" title="★≥100 且近 90 天零提交">疑似停维</span>';
  return "";
}
function relTxt(r) {
  if (!r[I.RV]) return "—";
  const d = r[I.RD];
  return `${esc(String(r[I.RV]).slice(0, 14))}<span class="muted small"> ${d==null?"":d+"天前"}</span>`;
}
function g7Txt(r) {
  const g = r[I.G7];
  if (g == null) return '<span class="muted">—</span>';
  if (g > 0) return `<span class="g7">+${g}</span>`;
  if (g < 0) return `<span class="g7 neg">${g}</span>`;
  return '<span class="muted">0</span>';
}
function newCutoff() {
  const d = new Date(`${M.snap.slice(0,4)}-${M.snap.slice(4,6)}-${M.snap.slice(6,8)}`);
  d.setDate(d.getDate() - 45);
  return d.toISOString().slice(0, 10);
}
let NEW_CUT = typeof M.snap === "string" ? newCutoff() : "0000";

/* ---------- 主题 ---------- */
(function initTheme() {
  const t = localStorage.getItem("dbh_theme")
         || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = t;
})();
function bindThemeBtn() {
  const b = el("theme-btn");
  if (!b) return;
  b.onclick = () => {
    const cur = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = cur;
    localStorage.setItem("dbh_theme", cur);
  };
}

/* ---------- hash 路由 ---------- */
function parseHash() {
  const o = {};
  new URLSearchParams(location.hash.replace(/^#/, "")).forEach((v, k) => { o[k] = v; });
  return o;
}
function writeHash(o) {
  const s = new URLSearchParams(o).toString();
  history.replaceState(null, "", location.pathname + (s ? "#" + s : ""));
}

/* ---------- 我的关注 ---------- */
function getWatch() { try { return new Set(JSON.parse(localStorage.getItem("dbh_watch") || "[]")); }
                      catch (e) { return new Set(); } }
function saveWatch(s) { localStorage.setItem("dbh_watch", JSON.stringify([...s])); }
function getMyDbs() { try { return new Set(JSON.parse(localStorage.getItem("dbh_mydbs") || "[]")); }
                      catch (e) { return new Set(); } }
function saveMyDbs(s) { localStorage.setItem("dbh_mydbs", JSON.stringify([...s])); }
/* 对比篮：有序数组，最多 4 个 */
function getCompare() { try { const a = JSON.parse(localStorage.getItem("dbh_compare") || "[]");
                              return Array.isArray(a) ? a.filter(x => typeof x === "string") : []; }
                        catch (e) { return []; } }
function saveCompare(a) { localStorage.setItem("dbh_compare", JSON.stringify(a.slice(0, 4))); }
function cmpKey(fns) { return [...fns].sort().join("|"); }
function toggleCompareUi(btn, fn) {
  let a = getCompare();
  if (a.includes(fn)) a = a.filter(x => x !== fn);
  else { if (a.length >= 4) { alert("对比最多 4 个项目，先移除一个"); return; }
         a.push(fn); }
  saveCompare(a);
  btn.textContent = a.includes(fn) ? "⇄ 已在对比" : "⇄ 加入对比";
  const go = document.getElementById("dr-cmp-go");
  if (go) { if (a.length >= 2) { go.style.display = ""; go.textContent = `去对比（${a.length}）→`; }
            else go.style.display = "none"; }
}

/* ---------- chips 行 ---------- */
/* items: [{v, label, n}] ；sel: Set（空=全部）；点击回调 onToggle(v, isOn) */
function renderChips(container, items, sel, onToggle, foldN) {
  foldN = foldN || 12;
  const all = items[0] && items[0].v === "*";
  const hasSel = sel && sel.size > 0;
  const showAll = !hasSel;
  let vis = items;
  const needFold = items.length > foldN + 2;
  const folded = !container._unfold;
  if (needFold && folded) {
    const keep = items.slice(0, foldN).filter(x => x.v !== "*");
    const hiddenSel = items.slice(foldN).some(x => x.v !== "*" && sel.has(x.v));
    vis = items.slice(0, foldN);
    if (hiddenSel) sel.forEach(v => { const it = items.find(x => x.v === v);
      if (it && !vis.includes(it)) vis.push(it); });
  }
  let html = "";
  for (const it of vis) {
    const on = it.v === "*" ? showAll : (sel && sel.has(it.v));
    const cls = "chip" + (on ? " on" : "") + (it.v === "*" ? " all" : "");
    html += `<span class="${cls}" data-v="${esc(it.v)}">${esc(it.label)}`
          + (it.n != null ? ` <span class="n">${fmtK(it.n)}</span>` : "") + `</span>`;
  }
  if (needFold) html += `<span class="more-btn">${folded ? `更多 ${items.length - foldN} ▾` : "收起 ▴"}</span>`;
  container.innerHTML = html;
  container.querySelectorAll(".chip").forEach(c => c.onclick = () => {
    const v = c.dataset.v;
    if (v === "*") onToggle("*");
    else onToggle(v, !(sel && sel.has(v)));
  });
  const mb = container.querySelector(".more-btn");
  if (mb) mb.onclick = () => { container._unfold = !container._unfold;
                               renderChips(container, items, sel, onToggle, foldN); };
}

/* ---------- 抽屉 ---------- */
function openDrawer(title, bodyHtml) {
  el("drawer-title").innerHTML = title;
  el("drawer-body").innerHTML = bodyHtml;
  el("drawer").classList.add("open");
  el("drawer-bg").classList.add("open");
}
function closeDrawer() {
  el("drawer").classList.remove("open");
  el("drawer-bg").classList.remove("open");
}
function bindDrawer() {
  el("drawer-bg").onclick = closeDrawer;
  document.querySelectorAll(".dr-close").forEach(b => b.onclick = closeDrawer);
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeDrawer(); });
}

/* 项目详情（抽屉正文）—— 含 AI 解读块（三源：快照指标 + 富集信号 + AI 解读文本）
   外包 .pd-body 标记段：detail 懒加载到货后 refreshPdBody 据此定位补画 */
function projectDetailHtml(fn, extraHead) {
  if (poolPending()) {   /* pool 未就绪：占位段与正常返回同形（.pd-body[data-fn]），到货后 refreshPdBody 原地补画 */
    const failed = _poolFail;   /* 先取状态：lazyPool() 会重置并立刻发起新一轮拉取 */
    lazyPool().catch(() => {});   /* 本任务可能无他处挂 catch（如二次失败周期），失败态由占位文案呈现 */
    return `<div class="pd-body" data-fn="${esc(fn)}"><div class="small muted" style="margin:10px 0 2px">生态数据${failed ? "加载失败，正在重试" : "加载中"}…</div></div>`;
  }
  const r = byFn(fn);
  if (!r) return "";
  const det = window.DETAIL;
  const d = (det && det[fn] !== undefined) ? det[fn] : null;   /* null=所在片未到货（区别于到货后确无此条） */
  if (!d) loadDetailFor([fn]).then(() => {
    if ((window.DETAIL || {})[fn] !== undefined) refreshPdBody();   /* 失败不重画：停留占位，重开抽屉即重试 */
  });
  const w = getWatch();
  const cN = getCompare().length;   // 篮内 ≥2 时抽屉里露出「去对比」直达链接
  const cmpGo = cN >= 2
    ? `<a class="btn" id="dr-cmp-go" href="compare.html">去对比（${cN}）→</a>`
    : `<a class="btn" id="dr-cmp-go" href="compare.html" style="display:none">去对比 →</a>`;
  const aikL = aikLabel(r);
  const chips = [
    ...dbList(r).slice(0, 4).map(x => `<span class="tag${x===NA?" gray":""}">${esc(x)}</span>`),
    `<span class="tag gray">${confDot(r)}${esc(r[I.CAT])}</span>`,
    statusTag(r),
    r[I.ECO] ? `<span class="tag gray" title="生态位：${r[I.ECO]==="app"?"只是使用数据库的应用":"为数据库生态服务的工具/组件"}">${ECO_CN[r[I.ECO]]}</span>` : "",
    r[I.PF] ? `<span class="tag gray" title="目标人群（AI 解读）">${PF_CN[r[I.PF]]}</span>` : "",
    r[I.SEC] === "cn" ? `<span class="tag gray">国产生态</span>` : "",
    r[I.O] ? `<span class="tag off">官方</span>` : "",
    aikL ? `<span class="tag">${esc(aikL)}</span>` : "",
    r[I.LANG] ? `<span class="tag gray">${esc(r[I.LANG])}</span>` : "",
    r[I.CR] >= NEW_CUT ? `<span class="tag">新项目</span>` : "",
  ].join("");
  const secLine = r[I.SN]
    ? `<div class="sec-line">${sevBadge(r[I.SW])}<span class="small muted">在册安全通告 ${r[I.SN]} 条</span></div>`
    : "";
  const secIds = (d && d.si && r[I.SN])
    ? `<details class="ids"><summary>展开 GHSA / CVE 编号</summary><div class="mono small" style="margin-top:6px;word-break:break-all">${esc(d.si).replace(/;/g, "<br>")}</div></details>` : "";
  const evLine = r[I.EV]
    ? `<div class="small" style="margin-top:8px"><span class="muted">分类依据（${r[I.CS]==="ai"?"AI 解读为主，规则为辅":"规则推导"}）：</span><span class="mono">${esc(r[I.EV])}</span></div>` : "";
  const m = maint(r);
  const maintLine = m === "dep"
    ? `<div class="warnbar">⚠ AI 解读判定：该项目已${r[I.STAT]==="deprecated"?"声明弃用":"停止维护"}，不建议新项目选用。</div>`
    : m === "arc"
    ? `<div class="warnbar">⚠ 该仓库已在 GitHub 标记为归档（Archived），不再接收维护，选型请谨慎。</div>`
    : m === "stale"
    ? `<div class="warnbar soft">⚠ 疑似停维：★≥100 且近 90 天零提交。若无近期发版，建议评估替代品。</div>` : "";
  /* AI 解读块：一句话定位 + 中文解读 + 能力事实 + 适用场景 + 原文依据；无解读回落 README 摘录 */
  const aiBlock = !d
    ? '<div class="small muted" style="margin:10px 0 2px">AI 解读与 README 摘录加载中…</div>'
    : (d.rw || d.ol)
    ? `<div class="ai-read">
         <div class="ai-read-head"><b>AI 解读</b><span class="muted small">${d.src==="desc"?"基于简介（无 README）":"基于 README"} · 置信${d.cg==="mid"?"中":"高"}</span></div>
         ${d.ol ? `<div class="ol">${esc(d.ol)}</div>` : ""}
         ${d.rw ? `<p class="rw">${esc(d.rw)}</p>` : ""}
         ${(d.hl && d.hl.length) ? `<div class="ai-cols"><div><span class="cap">能力事实</span><ul>${d.hl.map(h=>`<li>${esc(h)}</li>`).join("")}</ul></div>
           ${(d.uc && d.uc.length) ? `<div><span class="cap">适用场景</span><ul>${d.uc.map(u=>`<li>${esc(u)}</li>`).join("")}</ul></div>` : ""}</div>` : ""}
         ${d.ew ? `<div class="small muted" style="margin-top:6px">生态位依据：${esc(d.ew)}</div>` : ""}
         ${d.oe ? `<details class="ids"><summary>依据原文（README 摘句）</summary><div class="quote" style="margin-top:6px">${esc(d.oe)}</div></details>` : ""}
       </div>`
    : (d.rm ? `<div class="small muted" style="margin:10px 0 2px">README 摘录</div><div class="quote">${esc(d.rm)}</div>` : "");
  return `
  <div class="pd-body" data-fn="${esc(fn)}">
  ${extraHead || ""}
  ${maintLine}
  <div class="dr-hero">
    <div><a class="repo" href="${GH(fn)}" target="_blank" rel="noopener">${esc(fn)} ↗</a></div>
    ${r[I.DESC] ? `<div class="sub" style="white-space:normal">${esc(r[I.DESC])}</div>` : ""}
  </div>
  <div class="sec-line" style="margin-top:10px">${chips}</div>
  <div class="kpis">
    <div class="kpi"><div class="k">Star</div><div class="v">${fmtK(r[I.ST])}</div></div>
    <div class="kpi"><div class="k">本周增星</div><div class="v">${r[I.G7]==null?"—":(r[I.G7]>0?"+":"")+r[I.G7]}</div></div>
    <div class="kpi"><div class="k">贡献者</div><div class="v">${r[I.CT]==null?"—":fmtK(r[I.CT])}</div></div>
  </div>
  ${aiBlock}
  ${secLine}${secIds}
  <div class="facts">
    <div class="fk">提交 7/90 天</div><div class="mono">${r[I.C7]==null?"—":r[I.C7]} / ${r[I.C90]==null?"—":r[I.C90]}</div>
    <div class="fk">最新发版</div><div class="mono">${relTxt(r)}${(d && d.rp)?`<span class="muted small">（${esc(d.rp)}）</span>`:""}</div>
    <div class="fk">活跃度指数</div><div class="mono">${act(r)} <span class="muted small">/100</span></div>
    <div class="fk">许可证</div><div class="mono">${r[I.LIC]?esc(r[I.LIC]):'<span class="muted">未声明/无</span>'}</div>
    ${(d && d.ins && d.ins.length) ? `<div class="fk">安装方式</div><div class="mono small">${d.ins.join(" / ")}</div>` : ""}
    ${(d && d.lg)?`<div class="fk">语言构成</div><div>${esc(d.lg)}</div>`:""}
    <div class="fk">创建 / 最近推送</div><div class="mono small">${esc(r[I.CR])} / ${esc(r[I.PU])}</div>
  </div>
  ${evLine}
  <div class="dr-actions">
    <a class="btn primary" href="${GH(fn)}" target="_blank" rel="noopener">在 GitHub 打开 ↗</a>
    ${r[I.HP]?`<a class="btn" href="${esc(r[I.HP])}" target="_blank" rel="noopener">官网 ↗</a>`:""}
    <button class="btn" onclick="toggleWatchUi(this,'${esc(fn)}')">${w.has(fn)?"★ 已关注":"☆ 关注"}</button>
    <button class="btn" onclick="toggleCompareUi(this,'${esc(fn)}')">${getCompare().includes(fn)?"⇄ 已在对比":"⇄ 加入对比"}</button>
    ${cmpGo}
    ${r[I.SN]?`<a class="btn" href="https://github.com/advisories?query=${encodeURIComponent(fn)}" target="_blank" rel="noopener">安全通告 ↗</a>`:""}
  </div>`;
}
function toggleWatchUi(btn, fn) {
  const s = getWatch();
  s.has(fn) ? s.delete(fn) : s.add(fn);
  saveWatch(s);
  btn.textContent = s.has(fn) ? "★ 已关注" : "☆ 关注";
}

/* ---------- 分页 ---------- */
function pagerHtml(total, page, size) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return "";
  const parts = [];
  const add = (p, label, cls) => parts.push(`<a class="${cls||""}" data-pg="${p}">${label}</a>`);
  add(page - 1, "‹ 上一页", page === 1 ? "gap" : "");
  const want = [];
  if (pages <= 9) { for (let i = 1; i <= pages; i++) want.push(i); }
  else {
    want.push(1, 2);
    if (page > 4) want.push("…");
    for (let i = Math.max(3, page - 2); i <= Math.min(pages - 2, page + 2); i++) want.push(i);
    if (page < pages - 3) want.push("…");
    want.push(pages - 1, pages);
  }
  for (const w of want) {
    if (w === "…") parts.push(`<span class="gap">…</span>`);
    else parts.push(w === page ? `<span class="cur">${w}</span>` : `<a data-pg="${w}">${w}</a>`);
  }
  add(page + 1, "下一页 ›", page === pages ? "gap" : "");
  return `<div class="pager">${parts.join("")}</div><div class="small muted" style="text-align:center">第 ${page} / ${pages} 页 · 共 ${total.toLocaleString()} 项</div>`;
}
function bindPager(container, cb) {
  container.querySelectorAll("[data-pg]").forEach(a => a.onclick = () => {
    const p = +a.dataset.pg;
    if (p >= 1) cb(p);
  });
}

/* ---------- 公共导航 ---------- */
function navHtml(cur) {
  const links = [["index.html", "周刊"], ["archive.html", "往期周刊"], ["mystack.html", "我的关注"],
                 ["projects.html", "项目浏览"], ["compare.html", "项目对比"]];
  return `<header><div class="wrap nav">
    <a class="brand" href="index.html">开源生态<b>观测</b></a>
    ${links.map(([h, t]) => `<a class="lk ${h===cur?"on":""}" href="${h}">${t}</a>`).join("")}
    <span class="spacer"></span>
    <span class="gnav" id="gnav">
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.8"/>
        <path d="M10.5 10.5 L14.5 14.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
      <input id="gq" type="text" autocomplete="off" spellcheck="false"
             placeholder="搜索全站…" aria-label="全局搜索">
      <kbd>/</kbd>
      <div class="gnav-sug" id="gnav-sug"></div>
    </span>
    <span class="contact-wrap">
      <button class="icon-btn" id="contact-btn" title="联系作者 · 公众号" aria-haspopup="true" aria-expanded="false">💬 联系我们</button>
      <span class="contact-pop" id="contact-pop" hidden>
        <img src="assets/qr-wechat.jpg" alt="公众号二维码" width="158" height="158">
        <span class="cap">微信扫码关注公众号</span>
      </span>
    </span>
    <button class="icon-btn" id="theme-btn" title="切换主题">🌗</button>
  </div></header>`;
}
function drawerHtml() {
  return `<div id="drawer-bg"></div>
  <aside id="drawer" aria-label="详情">
    <div class="dr-head"><h3 id="drawer-title">详情</h3><button class="dr-close" title="关闭">✕</button></div>
    <div id="drawer-body"></div>
  </aside>`;
}

/* 排序键（项目浏览器与矩阵共用口径） */
function sortVal(r, sort) {
  switch (sort) {
    case "gro": return [(r[I.G7] == null ? -1e9 : r[I.G7]), r[I.ST]];
    case "act": return [act(r), r[I.ST]];
    case "new": return [r[I.CR] || "", r[I.ST]];
    case "rel": return [r[I.RD] == null ? -1e9 : -r[I.RD], r[I.ST]];
    case "push": return [r[I.PU] || "", r[I.ST]];
    case "idx": return [idxScore(r), r[I.ST]];
    default:    return [r[I.ST], r[I.G7] || 0];   // star
  }
}
function cmpRec(a, b, sort) {
  const va = sortVal(a, sort), vb = sortVal(b, sort);
  return (vb[0] > va[0]) - (vb[0] < va[0]) || (vb[1] > va[1]) - (vb[1] < va[1]);
}

/* ═════════ 导航栏全局搜索（全站入口：/ 聚焦，建议面板，回车跳项目浏览页带条件）═════════ */
(function injectGnavStyle() {
  const s = document.createElement("style");
  s.textContent = `
.gnav { position: relative; display: flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); background: var(--bg); border-radius: 6px;
  height: 30px; padding: 0 8px; width: 210px; flex: 0 0 auto; }
.gnav:focus-within { border-color: var(--accent); background: var(--card);
  box-shadow: 0 0 0 3px var(--accent-soft); }
.gnav svg { color: var(--muted); flex: 0 0 auto; }
.gnav:focus-within svg { color: var(--accent); }
.gnav input { border: none; outline: none; background: transparent; flex: 1;
  min-width: 0; font: inherit; font-size: 12px; color: var(--ink); }
.gnav input::placeholder { color: var(--muted); }
.gnav kbd { font: 12px var(--mono); border: 1px solid var(--line);
  border-radius: 4px; padding: 0 4px; color: var(--muted); line-height: 1.5; }
.gnav:focus-within kbd { display: none; }
.gnav-sug { position: absolute; top: calc(100% + 6px); right: 0; width: 400px;
  background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  box-shadow: var(--shadow); z-index: 1000; max-height: 60vh; overflow: auto;
  padding: 4px; display: none; font-size: 12px; }
.gnav.open .gnav-sug { display: block; }
.gnav-sug .gh { font-size: 12px; font-weight: 400; color: var(--muted);
  padding: 7px 10px 3px; text-transform: uppercase; letter-spacing: 2px; }
.gnav-sug .gi { display: flex; align-items: center; gap: 8px; padding: 6px 10px;
  border-radius: 6px; cursor: pointer; min-width: 0; }
.gnav-sug .gi.on, .gnav-sug .gi:hover { background: var(--accent-soft); }
.gnav-sug .gi .t { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.gnav-sug .gi .m { margin-left: auto; color: var(--muted); font-size: 12px;
  white-space: nowrap; padding-left: 12px; }
.gnav-sug .gi mark { background: none; color: var(--accent); font-weight: 700; }
.gnav-sug .none { padding: 14px 10px; color: var(--muted); text-align: center; }
@media (max-width: 980px) { .gnav { width: 130px; } .gnav-sug { width: 320px; } }
@media (max-width: 760px) { .gnav { display: none; } }`;
  document.head.appendChild(s);
})();

function bindGlobalSearch() {
  const wrap = document.getElementById("gnav");
  if (!wrap || wrap._bound) return;
  wrap._bound = true;
  const inp = document.getElementById("gq"), sug = document.getElementById("gnav-sug");
  let idx = -1, flat = [], timer = null;
  const qhist = () => { try { return JSON.parse(localStorage.getItem("dbh_qhist")||"[]"); }
                        catch(e){ return []; } };
  const ghl = (text, q) => {
    const at = text.toLowerCase().indexOf(q);
    if (!q || at < 0) return esc(text);
    return esc(text.slice(0,at)) + "<mark>" + esc(text.slice(at, at+q.length)) + "</mark>"
         + esc(text.slice(at+q.length));
  };
  const url = {
    q:  v => "projects.html#q=" + encodeURIComponent(v) + "&view=list&blk=all",
    cat: v => "projects.html#cat=" + encodeURIComponent(v) + "&view=list&blk=all",
    db:  v => {
      /* 与页面分组口径一致：TiDB 起为国产板块 */
      const cs = (typeof DBS !== "undefined" && DBS.length) ? DBS.indexOf("TiDB") : -1;
      const blk = (cs > 0 && DBS.indexOf(v) >= cs) ? "cn" : "intl";
      return "projects.html#blk=" + blk + "&db=" + encodeURIComponent(v) + "&view=list";
    },
  };
  function renderSug(raw) {
    const q = raw.trim().toLowerCase();
    flat = [];
    let html = "";
    const POK = typeof P !== "undefined" && P && P.length;
    if (!q) {
      const h = qhist();
      if (h.length) {
        html += `<div class="gh">最近搜索</div>`;
        for (const t of h) {
          flat.push({ go: url.q(t), t, fill: t });
          html += `<div class="gi" data-k="${flat.length-1}"><span>🕘</span><span class="t">${esc(t)}</span></div>`;
        }
      } else {
        html += `<div class="none">搜索项目 / 类别 / 数据库，回车前往项目浏览</div>`;
      }
    } else {
      let projs = [], cats = [], dbs = [], n = 0;
      if (POK) {
        const hits = [];
        for (let i = 0; i < P.length; i++) {
          if (!P[i][I.DB]) continue;   /* 只搜已归库项目，与项目浏览页宇宙一致 */
          const fn = P[i][I.FN].toLowerCase(), ds = (P[i][I.DESC]||"").toLowerCase();
          let w = 0;
          if (fn.indexOf(q) >= 0) w = 2;
          else if (ds.indexOf(q) >= 0) w = 1;
          if (w) hits.push({ i, sc: w * (Math.log10((P[i][I.ST]||0) + 1) + 1) });
        }
        hits.sort((a,b) => b.sc - a.sc);
        n = hits.length;
        projs = hits.slice(0,3).map(h => P[h.i]);
        cats = CATS.filter(c => c.toLowerCase().includes(q)).slice(0,2);
        dbs  = DBS.filter(d => d.toLowerCase().includes(q)).slice(0,2);
      }
      if (!n && !cats.length && !dbs.length)
        html += `<div class="none">没有匹配“${esc(raw)}”${POK ? "" : "（本页无数据，回车仍可前往项目浏览搜索）"}</div>`;
      if (projs.length) {
        html += `<div class="gh">项目</div>`;
        for (const r of projs) {
          flat.push({ go: url.q(r[I.FN]), t: r[I.FN], fill: r[I.FN] });
          html += `<div class="gi" data-k="${flat.length-1}"><span>📦</span><span class="t mono">${ghl(r[I.FN], q)}</span>
            <span class="m">★${fmtK(r[I.ST])} · ${esc(r[I.CAT])}</span></div>`;
        }
      }
      if (cats.length) {
        html += `<div class="gh">类别</div>`;
        for (const c of cats) {
          flat.push({ go: url.cat(c), t: c });
          html += `<div class="gi" data-k="${flat.length-1}"><span>🗂</span><span class="t">${ghl(c, q)}</span></div>`;
        }
      }
      if (dbs.length) {
        html += `<div class="gh">数据库</div>`;
        for (const d of dbs) {
          flat.push({ go: url.db(d), t: d });
          html += `<div class="gi" data-k="${flat.length-1}"><span>🗄</span><span class="t">${ghl(d, q)}</span></div>`;
        }
      }
      flat.push({ go: url.q(raw.trim()), t: "" });
      html += `<div class="gi" data-k="${flat.length-1}"><span>🔍</span>
        <span class="t">前往项目浏览${n ? `查看全部 <b>${n.toLocaleString()}</b> 个匹配` : `搜索“${esc(raw)}”`}</span><span class="m">↵</span></div>`;
    }
    sug.innerHTML = html;
    wrap.classList.add("open");
    idx = -1;
    sug.querySelectorAll(".gi").forEach(g => {
      g.onclick = () => { const it = flat[+g.dataset.k];
        if (!it) return;
        if (it.fill) inp.value = it.fill;   /* 词形条目（历史/项目）回填；类别/库直达不回填（词≠状态） */
        closeSug(); inp.blur();             /* 同页 hash 跳转须显式收面板：mousedown preventDefault 挡了 blur */
        location.href = it.go; };
      g.addEventListener("mouseenter", () => {
        idx = +g.dataset.k;
        sug.querySelectorAll(".gi").forEach(x => x.classList.toggle("on", +x.dataset.k === idx));
      });
    });
  }
  function closeSug() { wrap.classList.remove("open"); idx = -1; flat = []; }
  inp.addEventListener("focus", () => renderSug(inp.value));
  inp.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => renderSug(inp.value), 150);
  });
  inp.addEventListener("blur", () => setTimeout(() => {
    if (!sug.contains(document.activeElement)) closeSug();
  }, 120));
  inp.addEventListener("keydown", e => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!flat.length) return;
      idx = (idx + (e.key === "ArrowDown" ? 1 : -1) + flat.length) % flat.length;
      sug.querySelectorAll(".gi").forEach(g => g.classList.toggle("on", +g.dataset.k === idx));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const v = inp.value.trim();
      const it = (idx >= 0 && flat[idx]) || null;
      if (it) {
        if (it.fill) inp.value = it.fill;
        closeSug(); inp.blur();
        location.href = it.go;
      } else if (v) {
        try {
          const h = qhist().filter(x => x !== v);
          h.unshift(v);
          localStorage.setItem("dbh_qhist", JSON.stringify(h.slice(0,5)));
        } catch(_) {}
        closeSug(); inp.blur();
        location.href = url.q(v);
      }
    } else if (e.key === "Escape") { closeSug(); inp.blur(); }
  });
  sug.addEventListener("mousedown", e => e.preventDefault());
  document.addEventListener("keydown", e => {          /* 全站任意处按 / 聚焦全局搜索 */
    const tag = (document.activeElement||{}).tagName || "";
    if (e.key === "/" && !/INPUT|SELECT|TEXTAREA/.test(tag)) {
      e.preventDefault();
      inp.focus();
    }
  });
}
setTimeout(bindGlobalSearch, 0);   /* 等 navHtml 注入后再绑定 */

/* ---------- 公众号二维码 popover（导航右端，全站共用） ---------- */
function bindContact() {
  const btn = document.getElementById("contact-btn"), pop = document.getElementById("contact-pop");
  if (!btn || !pop) return;
  const set = on => { pop.hidden = !on; btn.setAttribute("aria-expanded", String(on)); };
  btn.addEventListener("click", e => { e.stopPropagation(); set(pop.hidden); });
  document.addEventListener("click", e => { if (!pop.hidden && !pop.contains(e.target)) set(false); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !pop.hidden) set(false); });
}
setTimeout(bindContact, 0);
