"use strict";
/* compare.js P10.1 -- /compare/ 自选对比（渐进增强）：任选两个部署项目并排比较。
   与旧 pool.js 对比篮的区别：数据不进 HTML——异步 fetch 与 /projects/ 同一份瘦索引
   （assets/browse-{指纹}.json，浏览器缓存共享），静态骨架（热门 chips + 529 组清单 +
   AI 长文）原样保留，本文件加载失败页面照常完整可用。只收录站内部署集（归属过 17 库，
   2026-11-22 基线 11,993 项）。选择结果写入 hash（#a=owner/repo&b=owner/repo）可分享。 */
(function () {
  var B = window.CMP || {};
  var BASE = B.base || "";
  var q = function (s) { return document.querySelector(s); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function comma(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function kfmt(n) { return typeof n === "number" && n >= 1000 ? Math.floor(n / 1000) + "k" : String(n); }
  function d10(s) { return s ? String(s).slice(0, 10) : "—"; }

  var DATA = null, BY = {};                       /* fn 小写 -> item */
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

  /* 输入框状态机：sel=已选定 item（点选/回车才定）；菜单开着 ↑↓ 移动、Enter 选取、Esc 关 */
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

  /* ---------- 并排表（字段与 /vs/ 擂台页画像同源：瘦索引 12 键客户端派生） ---------- */
  function tags(it) {
    var d = it.dbs || [], h = d.slice(0, 4).map(function (x) { return '<span class="tag">' + esc(x) + "</span>"; }).join("");
    if (d.length > 4) h += '<span class="tag gray">+' + (d.length - 4) + "</span>";
    return h || '<span class="muted">—</span>';
  }
  function vcard(it) {
    return '<b><a class="repo" href="' + esc(BASE + "/p/" + it.fn + "/") + '">' + esc(it.fn) + "</a></b>" +
      '<div class="sub">' + (esc(it.ol) || '<span class="muted">（无描述）</span>') + "</div>";
  }
  function mnt(it) { return it.mnt === "stale" ? '<span style="color:var(--warn)">疑似停维</span>' : "活跃"; }
  function secv(it) { return it.sec ? '<span style="color:var(--sev)">有</span>' : "无"; }
  function row(k, va, vb) { return "<tr><td class='small muted'>" + k + "</td><td>" + va + "</td><td>" + vb + "</td></tr>"; }
  function render(a, b) {
    q("#cmp-out").innerHTML =
      '<div class="tblwrap"><table class="rows"><thead><tr><th style="width:110px">维度</th><th>A</th><th>B</th></tr></thead><tbody>' +
      row("项目", vcard(a), vcard(b)) +
      row("Star", '<span class="mono">' + comma(a.stars) + "★</span>", '<span class="mono">' + comma(b.stars) + "★</span>") +
      row("语言", esc(a.lang || "—"), esc(b.lang || "—")) +
      row("类别", esc(a.cat || "—"), esc(b.cat || "—")) +
      row("适配库", tags(a), tags(b)) +
      row("维护", mnt(a), mnt(b)) +
      row("属性", a.off ? "官方" : "社区", b.off ? "官方" : "社区") +
      row("安全通告", secv(a), secv(b)) +
      row("AI", a.ai ? "AI 项目" : "—", b.ai ? "AI 项目" : "—") +
      row("创建于", '<span class="mono">' + d10(a.created) + "</span>", '<span class="mono">' + d10(b.created) + "</span>") +
      row("最近推送", '<span class="mono">' + d10(a.pushed) + "</span>", '<span class="mono">' + d10(b.pushed) + "</span>") +
      row("最近发版", esc(a.relpub || "—"), esc(b.relpub || "—")) +
      "</tbody></table></div>";
  }
  function hint(msg) { q("#cmp-out").innerHTML = '<p class="small muted" style="margin-top:10px">' + esc(msg) + "</p>"; }

  function resolve(v) { return v ? BY[v.trim().toLowerCase()] || null : null; }
  function go() {
    var ia = q("#cmp-a").sel || resolve(q("#cmp-a").value);
    var ib = q("#cmp-b").sel || resolve(q("#cmp-b").value);
    if (!ia) return hint("项目 A 不在站内部署集内（只收录归属过 17 库的项目；输入 owner/repo 或仓名）");
    if (!ib) return hint("项目 B 不在站内部署集内");
    if (ia.fn === ib.fn) return hint("两边是同一个项目");
    q("#cmp-a").value = ia.fn; q("#cmp-b").value = ib.fn;
    render(ia, ib);
    history.replaceState(null, "", location.pathname + "#a=" + encodeURIComponent(ia.fn) + "&b=" + encodeURIComponent(ib.fn));
  }

  q("#cmp-go").addEventListener("click", go);
  q("#cmp-swap").addEventListener("click", function () {
    var a = q("#cmp-a"), b = q("#cmp-b"), t = a.value; a.value = b.value; b.value = t;
    var s = a.sel; a.sel = b.sel; b.sel = s;
    if (q("#cmp-out").querySelector("table")) go();
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".cmp-cell")) { q("#cmp-a")._close(); q("#cmp-b")._close(); }
  });
  attach("cmp-a", "cmp-am"); attach("cmp-b", "cmp-bm");

  /* ---------- 启动：取瘦索引 → hash 预填（分享链直达结果） ---------- */
  fetch(BASE + "/assets/" + B.idx)
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      DATA = data;
      data.forEach(function (it) { BY[it.fn.toLowerCase()] = it; });
      var m = location.hash.match(/[#&]a=([^&]+)&b=([^&]+)/);
      if (m) {
        var a = decodeURIComponent(m[1]), b = decodeURIComponent(m[2]);
        q("#cmp-a").value = a; q("#cmp-b").value = b;
        var ia = BY[a.toLowerCase()], ib = BY[b.toLowerCase()];
        if (ia && ib && ia.fn !== ib.fn) render(ia, ib);
      }
    })
    .catch(function (err) { console.warn("[compare] 瘦索引加载失败，保持静态索引：", err); });
})();
