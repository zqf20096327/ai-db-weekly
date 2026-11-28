"use strict";
/* browse.js P9.3 -- /projects/ 浏览页渐进增强：旧 pool.js 版筛选面板复活（多选 chips + 搜索 + 排序 + 客户端翻页）。
   与旧 pool.js 的本质区别：数据不进 HTML——异步 fetch 瘦索引（assets/browse-{指纹}.json，指纹长缓存），
   静态骨架（卡片网格 + 清单 + 140 页静态分页）原样保留，本文件加载失败页面照常完整可用。
   筛选集照抄旧版：数据库(默认全选)/语言(Top8+全部)/属性(维护·官方/社区·有安全通告·AI·Star下限)/功能(默认全选)/排序。
   「弃用/归档」与「高危」两 chip 未抄：前者恒 0 结果（归档仓不进站），后者 severity 已不在管线（改「有安全通告」宽口径）。
   hash 状态可分享：#db=..&cat=..&lang=..&mnt=..&off=..&st=..&sort=..&q=..&p=..（只写非默认键）。 */
(function () {
  var B = window.BR || {};
  var BASE = B.base || "";
  var PS = B.pgsz || 24;                       /* 客户端翻页每页条数（静态页维持 100/页不动） */
  var q = function (s) { return document.querySelector(s); };
  var qa = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  /* ---------- 工具 ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function comma(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function kfmt(n) { return typeof n === "number" && n >= 1000 ? Math.floor(n / 1000) + "k" : (n == null ? "—" : String(n)); }

  /* ---------- 渲染（与服务端 card_tile / row_html 同款） ---------- */
  function cardHTML(it) {
    var stars = typeof it.stars === "number" ? kfmt(it.stars) + "★" : "—";
    var dbs = it.dbs || [], tags = dbs.slice(0, 3).map(function (d) { return '<span class="tag">' + esc(d) + "</span>"; }).join("");
    if (dbs.length > 3) tags += '<span class="tag gray">+' + (dbs.length - 3) + "</span>";
    var cat = it.cat ? '<span class="tag">' + esc(it.cat) + "</span>" : "";
    return '<a class="pcard" href="' + esc(BASE + "/p/" + it.fn + "/") + '">' +
      '<div class="pc-top"><span class="pc-name" title="' + esc(it.fn) + '">' + esc(it.fn.split("/")[1] || it.fn) + "</span>" +
      '<span class="pc-stars mono">' + stars + "</span></div>" +
      '<div class="pc-ol">' + (esc(it.ol) || "&nbsp;") + "</div>" +
      '<div class="pc-meta">' + tags + cat + '<span class="pc-lang">' + esc(it.lang || "") + "</span></div></a>";
  }
  function rowHTML(it) {
    var dbs = it.dbs || [], tags = dbs.slice(0, 3).map(function (d) { return '<span class="tag">' + esc(d) + "</span>"; }).join("");
    if (dbs.length > 3) tags += '<span class="tag gray">+' + (dbs.length - 3) + "</span>";
    var stars = typeof it.stars === "number" ? comma(it.stars) : "—";
    return "<tr><td><a class=\"repo\" href=\"" + esc(BASE + "/p/" + it.fn + "/") + "\">" + esc(it.fn) + "</a>" +
      '<div class="sub">' + (esc(it.ol) || '<span class=muted>（无描述）</span>') + "</div></td>" +
      "<td>" + tags + '</td><td class="small">' + esc(it.cat || "—") + '</td><td class="small mono">' + esc(it.lang || "—") +
      '</td><td class="r mono">' + stars + "</td></tr>";
  }
  function pagerHTML(cur, pages) {          /* 旧版 pager 逻辑同款：1 2 …±2… 末两页 */
    if (pages <= 1) return "";
    var want = [];
    if (pages <= 9) { for (var i = 1; i <= pages; i++) want.push(i); }
    else {
      want = [1, 2];
      if (cur > 4) want.push("…");
      for (var j = Math.max(3, cur - 2); j <= Math.min(pages - 2, cur + 2); j++) want.push(j);
      if (cur < pages - 3) want.push("…");
      want.push(pages - 1, pages);
    }
    var h = cur > 1 ? '<a data-p="' + (cur - 1) + '" href="#p=' + (cur - 1) + '">‹ 上一页</a>' : '<span class="gap">‹ 上一页</span>';
    want.forEach(function (w) {
      h += w === "…" ? '<span class="gap">…</span>'
        : w === cur ? '<span class="cur">' + w + "</span>"
        : '<a data-p="' + w + '" href="#p=' + w + '">' + w + "</a>";
    });
    h += cur < pages ? '<a data-p="' + (cur + 1) + '" href="#p=' + (cur + 1) + '">下一页 ›</a>' : '<span class="gap">下一页 ›</span>';
    return h;
  }

  /* ---------- 状态（默认=旧版缺省：库/类别全选，语言/属性空，Star 降序） ---------- */
  var st = { db: new Set(), cat: new Set(), lang: new Set(), mnt: new Set(), off: new Set(),
             sec: 0, ai: 0, stv: 0, sort: "stars", q: "", p: 1 };
  var DB_ALL = [], CAT_ALL = [], DATA = null, FILTERED = [], applyingHash = false;
  var SORT_LB = { stars: "Star 降序", created: "最新创建", pushed: "最近推送", relpub: "最近发版" };

  function pass(it) {
    if (st.db.size < DB_ALL.length && !(it.dbs || []).some(function (d) { return st.db.has(d); })) return false;
    if (st.cat.size < CAT_ALL.length && !st.cat.has(it.cat)) return false;
    if (st.lang.size && !st.lang.has(it.lang)) return false;
    if (st.mnt.size && !st.mnt.has(it.mnt)) return false;
    if (st.off.size && !st.off.has(String(it.off))) return false;
    if (st.sec && it.sec !== 1) return false;
    if (st.ai && it.ai !== 1) return false;
    if ((it.stars || 0) < st.stv) return false;
    if (st.q && (it.fn + " " + (it.ol || "")).toLowerCase().indexOf(st.q) === -1) return false;
    return true;
  }
  function dkey(k) { return function (a, b) {
    var x = a[k] || "", y = b[k] || "";
    if (x === y) return a.fn < b.fn ? -1 : 1;
    if (!x) return 1; if (!y) return -1;
    return x > y ? -1 : 1;                     /* ISO 日期字符串倒序，缺失垫底 */
  }; }
  function refilter() {
    FILTERED = DATA.filter(pass);
    if (st.sort === "stars") FILTERED.sort(function (a, b) { return (b.stars || 0) - (a.stars || 0) || (a.fn < b.fn ? -1 : 1); });
    else FILTERED.sort(dkey(st.sort));
  }

  /* ---------- chips 同步（.on 类别即真值；单选 chip 全部/独立开关另算） ---------- */
  function syncChips() {
    qa('.fzone a[data-db]').forEach(function (a) { a.classList.toggle("on", st.db.has(a.getAttribute("data-db"))); });
    qa('.fzone a[data-cat]').forEach(function (a) {
      var c = a.getAttribute("data-cat");
      a.classList.toggle("on", c === "" ? st.cat.size === CAT_ALL.length : st.cat.has(c));
    });
    qa('.fzone [data-lang]').forEach(function (b) {
      var lg = b.getAttribute("data-lang");
      b.classList.toggle("on", lg === "" ? !st.lang.size : st.lang.has(lg));
    });
    qa('.fzone [data-mnt]').forEach(function (b) { b.classList.toggle("on", st.mnt.has(b.getAttribute("data-mnt"))); });
    qa('.fzone [data-off]').forEach(function (b) { b.classList.toggle("on", st.off.has(b.getAttribute("data-off"))); });
    qa('.fzone [data-sec]').forEach(function (b) { b.classList.toggle("on", !!st.sec); });
    qa('.fzone [data-ai]').forEach(function (b) { b.classList.toggle("on", !!st.ai); });
    qa("#sort-seg span").forEach(function (s) { s.classList.toggle("on", s.getAttribute("data-sort") === st.sort); });
    q("#f-st").value = String(st.stv);
    /* #q 不回写：输入框归用户，st.q 只在防抖后取值 */
  }
  function activeCount() {
    return (st.db.size < DB_ALL.length ? 1 : 0) + (st.cat.size < CAT_ALL.length ? 1 : 0) +
      (st.lang.size ? 1 : 0) + (st.mnt.size ? 1 : 0) + (st.off.size ? 1 : 0) +
      (st.sec ? 1 : 0) + (st.ai ? 1 : 0) + (st.stv ? 1 : 0) + (st.sort !== "stars" ? 1 : 0) + (st.q ? 1 : 0);
  }

  /* ---------- hash 状态（只写非默认键；replaceState 不灌历史） ---------- */
  function writeHash() {
    if (applyingHash) return;
    var parts = [];
    if (st.db.size < DB_ALL.length) parts.push("db=" + encodeURIComponent(Array.from(st.db).join(",")));
    if (st.cat.size < CAT_ALL.length) parts.push("cat=" + encodeURIComponent(Array.from(st.cat).join(",")));
    if (st.lang.size) parts.push("lang=" + encodeURIComponent(Array.from(st.lang).join(",")));
    if (st.mnt.size) parts.push("mnt=" + Array.from(st.mnt).join(","));
    if (st.off.size) parts.push("off=" + Array.from(st.off).join(","));
    if (st.sec) parts.push("sec=1");
    if (st.ai) parts.push("ai=1");
    if (st.stv) parts.push("st=" + st.stv);
    if (st.sort !== "stars") parts.push("sort=" + st.sort);
    if (st.q) parts.push("q=" + encodeURIComponent(st.q));
    if (st.p > 1) parts.push("p=" + st.p);
    history.replaceState(null, "", location.pathname + location.search + (parts.length ? "#" + parts.join("&") : ""));
  }
  function applyHash() {
    applyingHash = true;
    var h = location.hash.slice(1);
    if (h) {
      h.split("&").forEach(function (kv) {
        var i = kv.indexOf("="), k = kv.slice(0, i), v = kv.slice(i + 1);
        var arr = function () { return decodeURIComponent(v).split(",").filter(Boolean); };
        if (k === "db") { st.db = new Set(arr().filter(function (d) { return DB_ALL.indexOf(d) >= 0; })); }
        else if (k === "cat") { st.cat = new Set(arr().filter(function (c) { return CAT_ALL.indexOf(c) >= 0; })); }
        else if (k === "lang") { st.lang = new Set(arr()); }
        else if (k === "mnt") { st.mnt = new Set(v.split(",")); }
        else if (k === "off") { st.off = new Set(v.split(",")); }
        else if (k === "sec") { st.sec = v === "1" ? 1 : 0; }
        else if (k === "ai") { st.ai = v === "1" ? 1 : 0; }
        else if (k === "st") { st.stv = parseInt(v, 10) || 0; }
        else if (k === "sort" && SORT_LB[v]) { st.sort = v; }
        else if (k === "q") { st.q = decodeURIComponent(v).toLowerCase(); }
        else if (k === "p") { st.p = parseInt(v, 10) || 1; }
      });
    }
    applyingHash = false;
  }

  /* ---------- 渲染接管 ---------- */
  function render() {
    refilter();
    var pages = Math.max(1, Math.ceil(FILTERED.length / PS));
    if (st.p > pages) st.p = pages;
    var slice = FILTERED.slice((st.p - 1) * PS, st.p * PS);
    q("#cards").innerHTML = slice.map(cardHTML).join("");
    q("#listwrap tbody").innerHTML = slice.map(rowHTML).join("");
    q("#spager").hidden = true;
    q("#jpager").hidden = false;
    q("#jpager").innerHTML = pagerHTML(st.p, pages);
    q("#match-n").textContent = "匹配 " + comma(FILTERED.length);
    q("#match-sub").textContent = "第 " + st.p + " / " + pages + " 页 · 本页 " + slice.length + " 项 · " + SORT_LB[st.sort];
    var act = activeCount();
    q("#jreset").hidden = !act;
    q("#jnote").hidden = !act;
    if (act) q("#jnote").textContent = "筛选中 · 条件已写入网址，可直接分享";
    syncChips();
    writeHash();
  }
  function go(p) { st.p = p; render(); q("#match-n").scrollIntoView({ block: "start" }); }

  /* ---------- 事件 ---------- */
  function bind() {
    qa('.fzone a[data-db], .fzone a[data-cat]').forEach(function (a) {   /* 锚点 chips：JS 拦截=筛选，右键/中键仍可导航 */
      a.addEventListener("click", function (e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        var db = a.getAttribute("data-db"), cat = a.getAttribute("data-cat");
        if (db !== null) { st.db.has(db) ? st.db.delete(db) : st.db.add(db); }
        else if (cat === "") { st.cat = new Set(CAT_ALL); }
        else { st.cat.has(cat) ? st.cat.delete(cat) : st.cat.add(cat); }
        st.p = 1; render();
      });
    });
    qa('.fzone [data-lang]').forEach(function (b) {
      b.addEventListener("click", function () {
        var lg = b.getAttribute("data-lang");
        if (lg === "") st.lang.clear();
        else st.lang.has(lg) ? st.lang.delete(lg) : st.lang.add(lg);
        st.p = 1; render();
      });
    });
    qa('.fzone [data-mnt]').forEach(function (b) {
      b.addEventListener("click", function () {
        var v = b.getAttribute("data-mnt");
        st.mnt.has(v) ? st.mnt.delete(v) : st.mnt.add(v);
        st.p = 1; render();
      });
    });
    qa('.fzone [data-off]').forEach(function (b) {
      b.addEventListener("click", function () {
        var v = b.getAttribute("data-off");
        st.off.has(v) ? st.off.delete(v) : st.off.add(v);
        st.p = 1; render();
      });
    });
    qa('.fzone [data-sec]').forEach(function (b) {
      b.addEventListener("click", function () { st.sec = st.sec ? 0 : 1; st.p = 1; render(); });
    });
    qa('.fzone [data-ai]').forEach(function (b) {
      b.addEventListener("click", function () { st.ai = st.ai ? 0 : 1; st.p = 1; render(); });
    });
    q("#f-st").addEventListener("change", function () { st.stv = parseInt(this.value, 10) || 0; st.p = 1; render(); });
    qa("#sort-seg span").forEach(function (s) {
      s.addEventListener("click", function () { st.sort = s.getAttribute("data-sort"); render(); });
    });
    var qt;
    q("#q").addEventListener("input", function () {
      clearTimeout(qt);
      var v = this.value.trim().toLowerCase();
      qt = setTimeout(function () { st.q = v; st.p = 1; render(); }, 200);
    });
    q("#jreset").addEventListener("click", function () {
      st.db = new Set(DB_ALL); st.cat = new Set(CAT_ALL);
      st.lang.clear(); st.mnt.clear(); st.off.clear();
      st.sec = 0; st.ai = 0; st.stv = 0; st.sort = "stars"; st.q = ""; st.p = 1;
      render();
    });
    q("#jpager").addEventListener("click", function (e) {
      var a = e.target.closest("a[data-p]");
      if (a) { e.preventDefault(); go(parseInt(a.getAttribute("data-p"), 10)); }
    });
    window.addEventListener("hashchange", function () { applyHash(); st.p = st.p || 1; render(); });
  }

  /* ---------- 启动：取瘦索引 → 初始化选中集 → hash → 接管 ---------- */
  fetch(BASE + "/assets/" + B.idx)
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      DATA = data;
      DB_ALL = qa('.fzone a[data-db]').map(function (a) { return a.getAttribute("data-db"); });
      CAT_ALL = qa('.fzone a[data-cat]').map(function (a) { return a.getAttribute("data-cat"); }).filter(Boolean);
      st.db = new Set(DB_ALL);
      st.cat = new Set(CAT_ALL);
      bind();
      applyHash();
      if (!st.p || st.p < 1) st.p = 1;
      render();
    })
    .catch(function (err) {
      console.warn("[browse] 瘦索引加载失败，保持静态清单：", err);
    });
})();
