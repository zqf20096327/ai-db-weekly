/* 数据库开源生态观察 · M2 前端（按 site-demo v2 施工图实现）
 *
 * 路由：#/ #/weekly/{N} 周报（落地页含资产入口卡）· #/past 往期 · #/monthly/{YYYY-MM} 月度速报
 *      #/map 生态地图（矩阵 / 档案双视图，格子下钻）· #/archive/{db} 档案视图
 *      旧路由 #/issue/weekly-N、#/db/{name} 自动跳转兼容。
 * 数据按需 fetch data/site/*.json（no-cache，内存缓存），契约见 v2/site_export/README_site_export.md。 */
(function () {
  'use strict';

  var app = document.getElementById('app');

  /* ================= 工具 ================= */

  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function fmt(n) {
    n = Number(n);
    if (isNaN(n)) return '—';
    return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k' : String(n);
  }
  function fmtFull(n) { n = Number(n); return isNaN(n) ? '—' : n.toLocaleString('en-US'); }
  function fmtDay(s) { s = String(s || ''); return /^\d{8}$/.test(s) ? s.slice(4, 6) + '-' + s.slice(6, 8) : s; }

  function licChip(l) {
    if (!l || l === 'NOASSERTION' || l === '自定义/无') return '<span class="lic warn">自定义</span>';
    if (l === 'MIT' || l === 'Apache-2.0' || l === 'BSD-3-Clause' || l === 'BSD-2-Clause') return '<span class="lic">' + esc(l) + '</span>';
    return '<span class="lic warn">' + esc(l) + '</span>';
  }

  var PLABEL = { use: '用库', ops: '管库', build: '造库', ai: 'AI' };
  function personaChips(p, ai) {
    var h = p ? '<span class="persona p-' + esc(p) + '">' + (PLABEL[p] || p) + '</span>' : '';
    if (ai && p !== 'ai') h += '<span class="persona p-ai">AI</span>';
    return h;
  }

  function isoDaysAgo(days) {
    var d = new Date(Date.now() - days * 864e5);
    return d.toISOString().slice(0, 10);
  }
  function health(r) {
    if (r.archived) return '<span class="stale">已归档</span>';
    var h = '';
    if (r.commit7) h += '<span class="fire">🔥' + r.commit7 + ' c/周</span>';
    if (r.pushed && r.pushed < isoDaysAgo(30)) h += '<span class="stale">30天无推送</span>';
    return h;
  }

  /* 火花线：缺照日断笔，末值≥首值绿色否则警示色 */
  function sparkSVG(pts, w, h) {
    if (!pts || pts.length < 2) return '';
    var v = pts.filter(function (x) { return x != null; });
    if (v.length < 2) return '';
    var mn = Math.min.apply(null, v), mx = Math.max.apply(null, v), rg = (mx - mn) || 1;
    var n = pts.length, x = function (i) { return i * (w - 2) / (n - 1) + 1; }, y = function (val) { return h - 3 - (val - mn) / rg * (h - 6); };
    var d = '', pen = false;
    for (var i = 0; i < n; i++) {
      if (pts[i] == null) { pen = false; continue; }
      d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(pts[i]).toFixed(1) + ' ';
      pen = true;
    }
    return '<svg class="spark" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h +
      '" preserveAspectRatio="none"><path d="' + d + '" fill="none" stroke="' +
      (v[v.length - 1] >= v[0] ? 'var(--ok)' : 'var(--warn)') + '" stroke-width="1.6"/></svg>';
  }

  var cache = {};
  function getJson(path) {
    if (cache[path] !== undefined) return Promise.resolve(cache[path]);
    return fetch(path, { cache: 'no-store' })
      .then(function (res) { return res.ok ? res.json() : null; })
      .catch(function () { return null; })
      .then(function (j) { cache[path] = j; return j; });
  }

  /* ================= 状态 ================= */

  var state = {
    site: null, now: null, idx: null,
    mapTab: 'matrix', db: 'PostgreSQL', cell: null,
    openOther: {}, persona: 'all'
  };
  var navToken = 0;
  function stillCurrent(t) { return t === navToken; }
  var MAPC = null;           /* map.json 缓存（含 cat_order/db_order/db_slug） */
  var knownSlugs = null;

  var SECTION_ORDER = ['国外数据库', '国产数据库', 'AI工具'];
  var SECLABEL = { '国外数据库': '板块一 · 国际主流数据库', '国产数据库': '板块二 · 国内数据库', 'AI工具': '板块三 · AI 工具' };

  function loading(t) { app.innerHTML = '<div class="loading">' + esc(t || '正在加载…') + '</div>'; }
  function emptyBox(title, hint) {
    return '<div class="empty-box"><b>' + esc(title) + '</b>' + (hint || '') + '</div>';
  }

  /* ================= 共用渲染件 ================= */

  function dbLinkChip(r) {
    var dbs = r.dbs || [];
    if (!dbs.length) return '';
    var hit = null;
    if (MAPC) for (var i = 0; i < MAPC.db_order.length; i++) { if (dbs.indexOf(MAPC.db_order[i]) !== -1) { hit = MAPC.db_order[i]; break; } }
    var txt = dbs.slice(0, 3).join('、') + (dbs.length > 3 ? ' 等' + dbs.length + ' 库' : '');
    return hit
      ? '<a class="chip" href="#/archive/' + encodeURIComponent(MAPC.db_slug[hit] || hit) + '" title="进入 ' + esc(hit) + ' 档案">适用 ' + esc(txt) + ' →</a>'
      : '<span class="chip">适用 ' + esc(txt) + '</span>';
  }

  /* M5 富集字段：版本节奏 + 安全披露（数据缺失时静默不显示） */
  function relChip(r) {
    if (!r.ver) return '';
    var t = '最新版本 ' + r.ver + ' · ' +
      (r.verd != null ? (r.verd === 0 ? '今天发布' : r.verd + ' 天前发布') : '') +
      ' · 近 90 天发版 ' + (r.n90 || 0) + ' 次';
    return '<span class="chip rel" title="' + esc(t) + '">' + esc(r.ver) +
      (r.verd != null && r.verd < 30 ? ' · ' + r.verd + '天' : '') + '</span>';
  }

  var _yearAgo = new Date(Date.now() - 365 * 864e5).toISOString().slice(0, 10);
  function secChip(r) {
    if (r.secn == null) return '';            /* 未扫描到该项目 */
    if (!r.secn) return '<span class="sech ok" title="GitHub 安全通告：该项目无自主披露（依赖组件漏洞不在公开口径内）">无已知披露</span>';
    var sevMap = { critical: '严重', high: '高危', medium: '中危', moderate: '中危', low: '低危' };
    var sev = sevMap[r.secw] || r.secw || '';
    var cls = (r.secw === 'critical' || r.secw === 'high') ? 'bad' : 'warn';
    return '<span class="sech ' + cls + '" title="项目自主披露 ' + r.secn + ' 条（最高 ' + esc(sev) +
      '，最近 ' + esc(r.secl || '—') + '）；是否已修复以官方通告为准">披露 ' + r.secn + ' · ' + esc(sev) +
      (r.secl && r.secl >= _yearAgo ? ' · 近一年' : '') + '</span>';
  }

  /* 周报榜单行 */
  function mrow(r, i, weak) {
    return '<div class="mrow"><span class="rk">' + (i + 1) + '</span>' +
      '<div><h3><a href="' + esc(r.url || '') + '" target="_blank" rel="noopener">' + esc(r.fn) + '</a></h3>' +
      (r.review
        ? '<p class="why ai"><small>AI 解读（缓存）</small>' + esc(r.review) + '</p>'
        : '<p class="why">' + esc(r.desc || '') + '</p>') +
      '<div class="tags">' + personaChips(r.persona, r.ai) + licChip(r.license) +
      relChip(r) + secChip(r) +
      (r.cat && r.cat !== '其他' ? '<span class="chip">' + esc(r.cat) + '</span>' : '') +
      dbLinkChip(r) + health(r) + '</div></div>' +
      '<div class="spark-cell">' + sparkSVG(r.spark, 92, 24) + '</div>' +
      '<div class="num"><span class="st">' + fmt(r.stars) + '<small style="color:var(--muted);font-size:10.4px"> ★</small></span><br>' +
      '<span class="growth' + (weak ? ' weak' : '') + '">+' + fmt(r.growth || 0) + '</span></div></div>';
  }

  /* 月度黑马行 */
  function gainRow(e, i) {
    return '<div class="mrow"><span class="rk">' + (i + 1) + '</span>' +
      '<div><h3><a href="' + esc(e.url || '') + '" target="_blank" rel="noopener">' + esc(e.fn) + '</a></h3>' +
      '<p class="why">' + esc(e.cat || '') + (e.section ? ' · ' + esc(e.section) : '') + '</p>' +
      '<div class="tags">' + licChip(e.license) +
      (e.lang ? '<span class="chip">' + esc(e.lang) + '</span>' : '') +
      (e.growth_streak ? '<span class="stk">连涨 ' + e.growth_streak + ' 周</span>' : '') + '</div></div>' +
      '<div></div>' +
      '<div class="num"><span class="g">+' + fmt(e.gain) + '</span><small style="color:var(--muted);font-size:10.4px"> 月增幅</small>' +
      '<br>' + fmt(e.stars) + '<small style="color:var(--muted);font-size:10.4px"> ★ 现值</small></div></div>';
  }

  /* 地图 / 档案项目卡 */
  function mapCard(r) {
    var g = (r.growth != null && r.growth > 0) ? '<span class="growth">+' + fmt(r.growth) + '</span>' : '';
    return '<article class="card"><h4><a href="' + esc(r.url || '') + '" target="_blank" rel="noopener">' + esc(r.fn) + '</a></h4>' +
      '<div class="nums"><span><b>' + fmt(r.stars) + '</b> ★</span>' + g +
      (r.commit7 ? '<span>🔥' + r.commit7 + ' c/周</span>' : '') +
      (r.lang ? '<span>' + esc(r.lang) + '</span>' : '') + '</div>' +
      '<p>' + esc(r.desc || '') + '</p><div class="tags">' + relChip(r) + secChip(r) +
      licChip(r.license) + health(r) + '</div></article>';
  }

  function licBar(lic) {
    var order = ['MIT', 'Apache-2.0', 'AGPL-3.0', '自定义/无'];
    var cols = { 'MIT': '#0f9d58', 'Apache-2.0': '#3b82f6', 'AGPL-3.0': '#d97706', '自定义/无': '#98a2b8' };
    var total = Object.keys(lic).reduce(function (a, k) { return a + (lic[k] || 0); }, 0) || 1;
    var h = '<span class="bar">';
    order.concat(Object.keys(lic).filter(function (k) { return order.indexOf(k) < 0; })).forEach(function (k) {
      if (!lic[k]) return;
      var c = cols[k] || '#7c6ce0';
      for (var i = 0; i < Math.max(1, Math.round(lic[k] / total * 14)); i++) h += '<i style="background:' + c + '"></i>';
    });
    return h + '</span>';
  }

  function assetEntries() {
    var now = state.now || {}, m = MAPC;
    var nDb = m ? m.db_order.length : (now.db_count || '—');
    return '<div class="asset-entries">' +
      '<a class="aentry" href="#/map"><div class="ico">🗺️</div><div class="tx"><b>生态工具地图</b>' +
      '<p>数据库 × 任务矩阵 · 每库档案 · 常备选型资产</p></div>' +
      '<div class="stats"><strong>' + fmt(now.map_total || (m && m.total) || 0) + '</strong><span>个工具 · ' + nDb + ' 库</span></div></a>' +
      '<a class="aentry" href="#/monthly"><div class="ico">📈</div><div class="tx"><b>月度速报</b>' +
      '<p>月度黑马 · 连涨榜 · 官方组织观测</p></div>' +
      '<div class="stats"><strong>' + esc(String(now.updated || '').slice(0, 7) || '—') + '</strong><span>月刊 · 滚动窗口</span></div></a></div>';
  }

  function latestWeeklyNo() {
    var nos = ((state.idx && state.idx.entries) || [])
      .filter(function (e) { return e.type === 'weekly'; })
      .map(function (e) { return Number(e.issue_no) || 0; });
    return nos.length ? Math.max.apply(null, nos) : null;
  }

  /* ================= 周报页 ================= */

  function renderWeekly(n, token) {
    setNav('weekly');
    loading('正在加载第 ' + n + ' 期周报…');
    getJson('data/site/map.json').then(function (m) { MAPC = m; knownSlugs = m && m.db_slug; });
    return getJson('data/site/weekly-' + n + '.json').then(function (w) {
      if (!stillCurrent(token)) return;
      if (!w) { app.innerHTML = emptyBox('未找到第 ' + n + ' 期', '可能尚未发布。<a href="#/past">查看往期</a>'); return; }

      var win = w.window || {};
      var h = '<div class="rhead"><div class="row1"><span class="pill">周报 · 第 ' + w.issue_no + ' 期</span>' +
        '<span class="hint">观察窗口 <b>' + fmtDay(win.from) + ' → ' + fmtDay(win.to) + '</b>' +
        (w.snapshot_date ? ' · 基准快照 ' + esc(w.snapshot_date) : '') + '</span></div>' +
        '<h1>数据库开源生态周报</h1>' +
        '<div class="meta"><span>候选池 <b>' + fmtFull(w.pool_total) + '</b></span>' +
        '<span>范围内 <b>' + fmtFull(w.pool_scoped) + '</b></span>' +
        '<span>口径：GitHub 公开数据 + 本站日快照</span></div></div>';

      /* 活跃榜首 = 三板块中增长最高的一项 */
      var top = null;
      SECTION_ORDER.forEach(function (s) {
        (w.board_secs[s] || []).forEach(function (r) {
          if (!top || (r.growth || 0) > (top.growth || 0)) top = r;
        });
      });
      h += '<section class="blk"><div class="kpis">' +
        '<div class="kpi"><span>本周有增长</span><strong>' + fmtFull(w.with_growth) + '</strong><em>项</em></div>' +
        '<div class="kpi"><span>新入池</span><strong>' + fmtFull(w.new_pool) + '</strong><em>项</em></div>' +
        (top ? '<div class="kpi"><span>活跃榜首</span><strong>+' + fmtFull(top.growth) + '</strong><em>★ ' + esc(top.fn.split('/').pop()) + '</em></div>' : '') +
        (w.rotated_count !== undefined ? '<div class="kpi"><span>上期上榜让位</span><strong>' + w.rotated_count + '</strong><em>项（轮换）</em></div>' : '') +
        '<div class="kpi"><span>本期新面孔</span><strong>' + ((w.newfaces || []).length) + '</strong><em>个</em></div>' +
        '</div>' + assetEntries() + '</section>';

      var hooks = w.hooks || [];
      h += '<section class="blk"><div class="sec-head"><h2>本期看点<span class="auto-tag manual">人工 · 每期唯一必写</span></h2></div><div class="hooks">' +
        (hooks.length ? hooks.map(function (k) {
          return '<div class="hook"><div class="n">' + esc(k.title || '') +
            (k.text && k.text.indexOf('+') === 0 ? '<em>' + esc(k.text.split('·')[0]) + '</em>' : '') + '</div>' +
            '<p>' + esc(k.text || '') + '</p></div>';
        }).join('') : '<div class="hook"><div class="n">看点待补</div><p>出刊时由人工补写本条看点文案。</p></div>') +
        '</div></section>';

      h += '<section class="blk"><div class="sec-head"><h2>本周活跃榜<span class="auto-tag auto">自动定榜 · 人工复核</span></h2>' +
        '<span class="hint">每板块 Top3 · 跨期轮换已应用' + (win.to ? ' · 窗口 ' + fmtDay(win.from) + ' → ' + fmtDay(win.to) : '') + '</span></div>';
      SECTION_ORDER.forEach(function (sn) {
        var rows = w.board_secs[sn] || [];
        var mg = rows.length ? Math.max.apply(null, rows.map(function (r) { return r.growth || 0; })) : 0;
        var weak = sn === '国产数据库' && mg < 30;
        h += '<div><div class="sec-title">' + SECLABEL[sn] +
          (weak ? ' <span class="weak-flag">本周信号偏弱</span>' : '') +
          ' <small>候选 ' + rows.length + (rows.length <= 3 ? '/3' : ' 项') + '</small></div><div class="movers">' +
          (rows.length ? rows.map(function (r, i) { return mrow(r, i, weak); }).join('')
            : '<p class="hint" style="margin:0">本周该板块无符合门槛的项目——如实空缺，不硬凑。</p>') + '</div></div>';
      });
      h += '</div>' +
        ((w.rotated_out || []).length
          ? '<details class="rot"><summary>轮换让位 ' + w.rotated_out.length + ' 项（上期上榜，本期按规则让位，透明可查）</summary>' +
            '<div class="rlist">' + w.rotated_out.map(function (r) {
              return '<span class="rchip">' + esc(r.fn) + (r.growth != null ? ' +' + r.growth : '') + '</span>';
            }).join('') + '</div></details>'
          : '') + '</section>';

      var F = w.focus, T = (F && F.three) || {};
      if (F && F.fn) {
        h += '<section class="blk"><div class="sec-head"><h2>本周深度解读<span class="auto-tag auto">AI 三维 + 人工过目</span></h2>' +
          '<span class="hint">' + esc(F.focus_note || '') + '</span></div>' +
          '<div class="deep"><div class="deep-head"><h3><a href="' + esc(F.url || '') + '" target="_blank" rel="noopener">' + esc(F.fn) + '</a></h3>' +
          '<span class="growth">+' + fmt(F.growth || 0) + ' ★/周</span><span class="chip">' + fmt(F.stars) + ' ★</span>' +
          sparkSVG(F.spark, 80, 20) + licChip(F.license) + '</div>' +
          (T.what || T.highlights || T.scenarios
            ? '<div class="deep-row"><span class="lab">解决了什么</span><p>' + esc(T.what) + '</p></div>' +
            '<div class="deep-row"><span class="lab">核心亮点</span><p>' + esc(T.highlights) + '</p></div>' +
            '<div class="deep-row"><span class="lab">适用场景</span><p>' + esc(T.scenarios) + '</p></div>'
            : '<div class="deep-row"><span class="lab">项目简介</span><p>' + esc(F.desc || '') + '</p></div>') +
          '</div></section>';
      }

      if (w.newfaces && w.newfaces.length) {
        h += '<section class="blk"><div class="sec-head"><h2>新面孔<span class="auto-tag trig">触发式 · 有则展示</span></h2>' +
          '<span class="hint">' + esc(w.newfaces_note || '首次进入观察池') + '</span></div><div class="grid">' +
          w.newfaces.map(function (p) {
            return '<article class="card"><h4><a href="' + esc(p.url || '') + '" target="_blank" rel="noopener">' + esc(p.fn) + '</a></h4>' +
              '<div class="nums"><span><b>' + fmt(p.stars) + '</b> ★ 入池</span>' +
              (p.commit7 ? '<span>🔥' + p.commit7 + ' c/周</span>' : '') + '</div>' +
              '<p>' + esc(p.desc || '') + '</p><div class="tags">' + personaChips(p.persona, p.ai) + licChip(p.license) + '</div></article>';
          }).join('') + '</div></section>';
      }

      h += '<section class="blk"><div class="callout"><b>口径与边界：</b>数据来源仅 GitHub 公开 API 与本站日快照；内核仓库不进榜单；License 分档为机械规则提示，非法律意见；AI 解读为缓存复用并标注。</div>' +
        '<div class="bridge"><div><b>本期上榜项目已自动归入生态工具地图</b>' +
        '<p>' + fmtFull((state.now || {}).map_total) + ' 个工具 · ' + ((MAPC && MAPC.db_order.length) || (state.now || {}).db_count || '—') + ' 种数据库，随每期周报自动沉淀。</p></div>' +
        '<a class="go" href="#/map">进入生态地图 →</a></div>' +
        '<div class="bridge" style="margin-top:10px"><div><b>往期内容</b><p>周报每周归档 · 月度速报每月一期，全部可回溯。</p></div>' +
        '<a class="go" href="#/past">查看往期归档 →</a></div></section>';

      app.innerHTML = h;
    });
  }

  /* ================= 往期页 ================= */

  function renderPast() {
    setNav('past');
    var entries = ((state.idx && state.idx.entries) || []).slice()
      .sort(function (a, b) { return String(b.date).localeCompare(String(a.date)); });
    var latest = latestWeeklyNo();
    var site = state.site || {};

    var h = '<div class="rhead"><div class="row1"><span class="pill">归档</span>' +
      '<span class="hint">周报每周归档 · 月度速报每月一期 · 全部可回溯</span></div>' +
      '<h1>往期归档</h1></div>';

    var wk = entries.filter(function (e) { return e.type === 'weekly'; });
    h += '<section class="blk"><div class="sec-head"><h2>周报 <small>每周四发布</small></h2><span class="hint">共 ' + wk.length + ' 期</span></div><div class="past-list">' +
      (wk.length ? wk.map(function (e) {
        var isCur = Number(e.issue_no) === latest;
        return '<a class="past-row" href="#/weekly/' + e.issue_no + '">' +
          (isCur ? '<span class="badge-cur">本期</span>' :
            e.status === 'draft' ? '<span class="badge-pre">草稿</span>' : '<span class="badge-pub">已发布</span>') +
          '<div class="l"><b>第 ' + e.issue_no + ' 期 · ' + esc(e.date) + '</b>' +
          (e.summary ? '<div class="d">看点：' + esc(e.summary) + '</div>' : '') + '</div>' +
          '<span class="go">阅读 →</span></a>';
      }).join('') : '<p class="hint">暂无归档。</p>') + '</div></section>';

    var mo = entries.filter(function (e) { return e.type === 'monthly'; });
    h += '<section class="blk"><div class="sec-head"><h2>月度速报 <small>每月一期 · org 观测与持续性是招牌</small></h2><span class="hint">共 ' + mo.length + ' 期</span></div><div class="past-list">' +
      (mo.length ? mo.map(function (e) {
        return '<a class="past-row" href="#/monthly/' + encodeURIComponent(String(e.date).slice(0, 7)) + '">' +
          '<span class="badge-pub">已发布</span>' +
          '<div class="l"><b>' + esc(String(e.date).slice(0, 7)) + ' 月度速报</b>' +
          (e.summary ? '<div class="d">' + esc(e.summary) + '</div>' : '') + '</div><span class="go">阅读 →</span></a>';
      }).join('') : '<a class="past-row" href="#/monthly"><span class="badge-cur">最新</span>' +
        '<div class="l"><b>本期月度速报</b><div class="d">月度黑马 · 连涨榜 · 官方组织观测</div></div><span class="go">阅读 →</span></a>') +
      '</div>' +
      '<div class="callout"><b>归档机制：</b>每期周报发布后自动入库；上榜项目同时沉淀进生态地图与数据库档案；往期页按时间倒序，期数多后按年折叠。</div></section>';

    var c = site.contact || {};
    if (c.items && c.items.length) {
      var lines = c.items.filter(function (it) { return !it.qr; }).map(function (it) {
        var v = it.href ? '<a href="' + esc(it.href) + '">' + esc(it.value) + '</a>' : esc(it.value || '');
        return (it.label ? esc(it.label) + ' ' : '') + v;
      }).join(' · ');
      h += '<div class="callout" style="background:color-mix(in srgb,var(--accent) 6%,transparent);border-color:color-mix(in srgb,var(--accent) 20%,transparent)">' +
        '<b style="color:var(--accent)">联系我们：</b>' + lines + (lines ? ' · ' : '') + '扫码见周报页脚</div>';
    }

    app.innerHTML = h;
    return Promise.resolve();
  }

  /* ================= 月度速报页 ================= */

  function probeMonths() {
    var out = [], d = new Date(String((state.now || {}).updated || '').replace(/-/g, '/') || Date.now());
    if (isNaN(d.getTime())) d = new Date();
    for (var k = 0; k < 3; k++) {
      out.push(d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2));
      d.setMonth(d.getMonth() - 1);
    }
    return out;
  }
  function latestMonthly() {
    return probeMonths().reduce(function (p, m) {
      return p.then(function (found) {
        return found ? found : getJson('data/site/monthly-' + m + '.json').then(function (j) { return j ? { month: m, data: j } : null; });
      });
    }, Promise.resolve(null));
  }

  function renderMonthly(month, token) {
    setNav('monthly');
    var job = month
      ? getJson('data/site/monthly-' + month + '.json').then(function (d) { return d ? { month: month, data: d } : null; })
      : latestMonthly();
    loading('正在加载月度速报…');
    return job.then(function (m) {
      if (!stillCurrent(token)) return;
      if (!m) { app.innerHTML = emptyBox('月度速报尚未生成', '每月 1 日聚合产出。<a href="#/">返回首页</a>'); return; }
      var d = m.data, win = d.window || {};
      var orgActive = (d.orgs || []).reduce(function (s, o) { return s + (o.active || 0); }, 0);
      var top1 = (d.top_gain || [])[0] || {};

      var h = '<div class="rhead"><div class="row1"><span class="pill m">月度速报 · ' + esc(d.month) + '</span>' +
        '<span class="hint">观察窗口 <b>' + fmtDay(win.from) + ' → ' + fmtDay(win.to) + '</b>（滚动）</span></div>' +
        '<h1>月度速报</h1>' +
        '<div class="meta"><span>月度涨幅冠军 <b>' + esc(top1.fn ? top1.fn.split('/').pop() : '—') + ' +' + fmt(top1.gain) + '</b></span>' +
        '<span>Top10 门槛 <b>+' + fmt(((d.top_gain || []).slice(-1)[0] || {}).gain) + '</b></span>' +
        '<span>口径：GitHub 公开数据 + 日快照</span></div></div>';

      h += '<section class="blk"><div class="kpis">' +
        '<div class="kpi"><span>月度新入池</span><strong>' + fmtFull(d.month_new_count) + '</strong><em>项</em></div>' +
        '<div class="kpi"><span>连涨 ≥3 周</span><strong>' + ((d.streaks || []).length) + '</strong><em>项</em></div>' +
        '<div class="kpi"><span>官方组织月活跃仓</span><strong>' + fmtFull(orgActive) + '</strong><em>个</em></div>' +
        (top1.fn ? '<div class="kpi"><span>黑马榜首</span><strong>+' + fmt(top1.gain) + '</strong><em>★ ' + esc(top1.fn.split('/').pop()) + '</em></div>' : '') +
        '</div></section>';

      if (d.top_gain && d.top_gain.length) {
        h += '<section class="blk"><div class="sec-head"><h2>月度黑马榜 Top 10 <small>窗口内 Star 净增</small></h2>' +
          '<span class="hint">与周报轮换无关的「真一个月谁涨最多」</span></div><div class="movers">' +
          d.top_gain.map(function (e, i) { return gainRow(e, i); }).join('') + '</div></section>';
      }

      if (d.streaks && d.streaks.length) {
        h += '<section class="blk"><div class="sec-head"><h2>持续性榜单 <small>连涨 ≥3 周</small></h2>' +
          '<span class="hint">基于日快照锚点 · 不是谁蹿红，是谁一直在涨</span></div>' +
          '<table class="tb"><tbody>' + d.streaks.map(function (e, i) {
            return '<tr><td><span class="rank">' + (i + 1) + '</span></td>' +
              '<td class="nm"><b><a href="' + esc(e.url || '') + '" target="_blank" rel="noopener">' + esc(e.fn) + '</a></b><span>' + esc(e.cat || '') + '</span></td>' +
              '<td class="num"><b>' + fmt(e.stars) + '</b></td><td class="num"><span class="stk">' + e.streak + ' 周</span></td>' +
              '<td class="num hide-sm">' + e.weeks + ' 周在池</td><td class="num hide-sm">+' + fmt(e.growth) + '</td></tr>';
          }).join('') + '</tbody></table></section>';
      }

      if (d.month_new_top && d.month_new_top.length) {
        h += '<section class="blk"><div class="sec-head"><h2>月度新入池 Top 5</h2><span class="hint">入池即此星数，非单周增长</span></div><div class="grid">' +
          d.month_new_top.map(function (e) {
            return '<article class="card"><h4><a href="' + esc(e.url || '') + '" target="_blank" rel="noopener">' + esc(e.fn) + '</a></h4>' +
              '<div class="nums"><span><b>' + fmt(e.stars) + '</b> ★ 入池</span></div>' +
              '<div class="tags">' + licChip(e.license) + '<span class="chip">' + esc(e.section || '') + '</span></div></article>';
          }).join('') + '</div></section>';
      }

      if (d.orgs && d.orgs.length) {
        h += '<section class="blk"><div class="sec-head"><h2>官方组织月度观测</h2>' +
          '<span class="hint">「月活跃」= 窗口内有推送的仓库 · 含内核仓库（仅统计不推荐）</span></div>' +
          '<table class="tb"><tbody>' + d.orgs.map(function (o) {
            var rate = o.repos ? Math.round((o.active || 0) / o.repos * 100) : 0;
            var nw = o.new === null ? '<span class="firstscan">本月首次扫描</span>'
              : (o.new > 0 ? '<b style="color:var(--ok)">' + o.new + ' 个</b>' : '<span style="color:var(--muted)">无</span>');
            var nl = (o.new_list || []).map(function (x) { return esc(String(x).split('/').pop()); }).join('、');
            return '<tr><td class="nm"><b><a href="https://github.com/' + esc(o.org) + '" target="_blank" rel="noopener">' + esc(o.org) + '</a></b>' +
              (nl ? '<span>新开：' + nl + '</span>' : '') + '</td>' +
              '<td class="num">' + o.repos + ' 仓</td><td class="num"><b>' + o.active + '</b> 活跃</td>' +
              '<td class="num">' + rate + '%</td><td>' + nw + '</td></tr>';
          }).join('') + '</tbody></table>' +
          '<div class="callout"><b>口径：</b>月窗取最近可用快照对（' + fmtDay(win.from) + ' → ' + fmtDay(win.to) + '）；黑马榜为窗口 Star 净增，新入池不计入；连涨周数跳过缺照周；首次纳入扫描的组织标注「首次扫描」，下月起进入月环比。</div></section>';
      }

      app.innerHTML = h;
    });
  }

  /* ================= 生态地图页（矩阵 + 档案双视图） ================= */

  function mxcLevel(n) {
    if (!n) return 'n0';
    if (n === 1) return 'n1';
    if (n < 10) return 'n2';
    if (n < 100) return 'n3';
    return 'n4';
  }

  function tier1(list) { return (list || []).filter(function (r) { return r.tier === 1; }); }

  function renderMap(token) {
    setNav('map');
    loading('正在加载生态地图…');
    return getJson('data/site/map.json').then(function (m) {
      if (!stillCurrent(token)) return;
      if (!m) { app.innerHTML = emptyBox('地图数据加载失败', '<a href="#/">返回首页</a>'); return; }
      MAPC = m; knownSlugs = m.db_slug || {};
      var now = state.now || {};
      var CATS = m.cat_order, DBS = m.db_order;
      var cells = 0;
      DBS.forEach(function (db) { CATS.forEach(function (c) { if ((m.matrix[db][c] || 0) >= 2) cells++; }); });

      var h = '<div class="rhead"><div class="row1"><span class="pill m">资产页 · 自动生成</span>' +
        '<span class="hint">数据日期 <b>' + esc(m.date) + '</b> · 与周报同源，上榜自动沉淀</span></div>' +
        '<h1>生态工具地图</h1>' +
        '<div class="meta"><span><b>' + fmtFull(m.total) + '</b> 个工具（star≥10）</span>' +
        '<span><b>' + DBS.length + '</b> 种数据库</span>' +
        '<span><b>' + cells + '</b> 个有效任务格</span>' +
        '<span><b>' + fmtFull(now.tier_default_total) + '</b> 精选层</span>' +
        '<span>分层：' + esc(m.tier_rule || '') + '</span></div></div>';

      h += '<div style="padding-top:16px"><div class="vtabs-big">' +
        '<button class="vtab-big' + (state.mapTab === 'matrix' ? ' is-active' : '') + '" data-t="matrix"><b>矩阵视图</b><small>数据库 × 任务 · 点击格子下钻</small></button>' +
        '<button class="vtab-big' + (state.mapTab === 'arch' ? ' is-active' : '') + '" data-t="arch"><b>数据库档案</b><small>每库一页 · 按任务分组浏览</small></button>' +
        '</div></div>';

      if (state.mapTab === 'matrix') {
        h += '<section class="blk" style="padding-top:8px"><div class="mx-wrap"><table class="mx"><thead><tr><th>任务 \\ 数据库</th>' +
          DBS.map(function (db) {
            var thin = (m.dbs[db] || {}).total < 15 ? ' class="dbcol-thin"' : '';
            return '<th' + thin + '><a href="#/archive/' + encodeURIComponent(m.db_slug[db] || db) + '">' + esc(db) + '</a></th>';
          }).join('') + '</tr></thead><tbody>';
        CATS.concat(['其他']).forEach(function (cat) {
          h += '<tr><td class="cat-name">' + esc(cat) + (cat === '其他' ? ' <small>待分类</small>' : '') + '</td>';
          DBS.forEach(function (db) {
            var n = cat === '其他' ? (m.other[db] || 0) : (m.matrix[db][cat] || 0);
            var sel = state.cell && state.cell.db === db && state.cell.cat === cat ? ' sel' : '';
            h += '<td>' + (n ? '<span class="mxc ' + mxcLevel(n) + sel + '" data-db="' + esc(db) + '" data-cat="' + esc(cat) + '">' + n + '</span>'
              : '<span class="mxc n0">·</span>') + '</td>';
          });
          h += '</tr>';
        });
        h += '</tbody></table></div>' +
          '<p class="mx-note">色深 = 工具数量；虚线头部列为适用库标注薄弱区，随标注补齐自动充实。点击格子查看项目，点击列头进入该库档案。</p>';
        h += '<div id="drill"></div></section>';
      } else {
        h += '<section class="blk" style="padding-top:8px"><div class="dbtabs">' + DBS.map(function (db) {
          return '<button class="dbtab' + (state.db === db ? ' is-active' : '') +
            ((m.dbs[db] || {}).total < 15 ? ' thin' : '') + '" data-db="' + esc(db) + '">' +
            esc(db) + '<em>' + fmt((m.dbs[db] || {}).total) + '</em></button>';
        }).join('') + '</div><div id="arch-body"><div class="loading">正在加载 ' + esc(state.db) + ' 档案…</div></div></section>';
      }

      h += '<div class="bridge" style="margin-top:18px"><div><b>地图与周报同源</b><p>每期周报的上榜项目自动沉淀进地图与档案——周报是节奏，地图是资产。</p></div>' +
        '<a class="go" href="#/weekly">返回本期周报 →</a></div>';
      app.innerHTML = h;

      app.querySelectorAll('.vtab-big').forEach(function (t) {
        t.addEventListener('click', function () {
          state.mapTab = t.getAttribute('data-t');
          state.cell = null;
          /* tab 切换同步 URL：否则「URL 停在档案地址、界面在矩阵」时，
             同目标档案链接与当前 hash 相同，浏览器不触发 hashchange（点击无反应） */
          var want = state.mapTab === 'matrix' ? '#/map'
            : '#/archive/' + encodeURIComponent((knownSlugs && knownSlugs[state.db]) || state.db);
          if (location.hash !== want) { location.hash = want; return; }
          renderMap(token);
        });
      });
      app.querySelectorAll('.mxc:not(.n0)').forEach(function (el) {
        el.addEventListener('click', function () {
          var db = el.getAttribute('data-db'), cat = el.getAttribute('data-cat');
          if (state.cell && state.cell.db === db && state.cell.cat === cat) { state.cell = null; }
          else { state.cell = { db: db, cat: cat }; }
          renderMap(token);
        });
      });
      app.querySelectorAll('.dbtab').forEach(function (b) {
        b.addEventListener('click', function () {
          state.db = b.getAttribute('data-db');
          state.persona = 'all';
          /* 库切换也同步 URL，保证 URL 与当前档案一致（同 vtab-big 的 hash 同步） */
          var want = '#/archive/' + encodeURIComponent((knownSlugs && knownSlugs[state.db]) || state.db);
          if (location.hash !== want) { location.hash = want; return; }
          renderMap(token);
        });
      });

      if (state.mapTab === 'matrix' && state.cell) renderDrill(token);
      if (state.mapTab === 'arch') renderArchBody(token);
    });
  }

  /* 矩阵格子下钻：按 Star 降序前 16 个（不足则全显），完整清单跳档案页 */
  function renderDrill(token) {
    var host = document.getElementById('drill');
    if (!host || !state.cell) return;
    var c = state.cell;
    var slug = (knownSlugs && knownSlugs[c.db]) || c.db;
    host.innerHTML = '<div class="loading">正在加载 ' + esc(c.db) + ' 的工具清单…</div>';
    getJson('data/site/archive-' + slug + '.json').then(function (arc) {
      if (!stillCurrent(token)) return;
      if (!arc) { host.innerHTML = emptyBox('档案加载失败'); return; }
      var all = (arc.groups[c.cat] || []).slice().sort(function (a, b) { return (b.stars || 0) - (a.stars || 0); });
      var rs = all.slice(0, 16);
      host.innerHTML = '<div class="dhead"><h3>' + esc(c.db) + ' · ' + esc(c.cat) + '</h3>' +
        '<span class="hint">按 Star 降序 · 共 ' + all.length + ' 项' + (all.length > 16 ? '（只列前 16）' : '') + '</span>' +
        '<button class="close-x" id="cell-close">收起</button></div>' +
        '<div class="grid">' + rs.map(mapCard).join('') + '</div>' +
        '<p class="hint" style="margin-top:10px">完整 ' + all.length + ' 项（star≥10）见 <a style="color:var(--accent)" href="#/archive/' + encodeURIComponent(arc.slug) + '">' + esc(c.db) + ' 档案页</a></p>';
      var cc = document.getElementById('cell-close');
      if (cc) cc.addEventListener('click', function () { state.cell = null; renderMap(token); });
    });
  }

  /* 档案视图主体：库统计头 + 人群/tier 筛选 + 任务分组 */
  function renderArchBody(token) {
    var host = document.getElementById('arch-body');
    if (!host) return;
    var m = MAPC;
    var slug = (knownSlugs && knownSlugs[state.db]) || state.db;
    getJson('data/site/archive-' + slug + '.json').then(function (arc) {
      if (!stillCurrent(token)) return;
      if (!arc) { host.innerHTML = emptyBox('档案加载失败'); return; }
      var st = arc.stats || {};
      var all = [];
      Object.keys(arc.groups).forEach(function (c) { all = all.concat(arc.groups[c]); });

      /* 主要语言：按记录统计 top3 */
      var langCnt = {};
      all.forEach(function (r) { if (r.lang) langCnt[r.lang] = (langCnt[r.lang] || 0) + 1; });
      var topLangs = Object.keys(langCnt).sort(function (a, b) { return langCnt[b] - langCnt[a]; }).slice(0, 3);

      var h = '<div class="arch-head">' +
        '<div class="arch-stat"><span>收录工具（star≥10）</span><strong>' + fmtFull(arc.total) + '</strong></div>' +
        '<div class="arch-stat"><span>精选层（国际/AI≥300 · 国产≥50）</span><strong>' + fmtFull(st.tier_default) + '</strong></div>' +
        '<div class="arch-stat"><span>本周上涨</span><strong>' + fmtFull(st.week_up) + '</strong></div>' +
        '<div class="arch-stat"><span>License 构成</span>' + licBar(st.licenses || {}) +
        '<br><small style="color:var(--muted)">' + Object.keys(st.licenses || {}).slice(0, 3).map(function (k) {
          return esc(k) + ' ' + (st.licenses[k]);
        }).join(' · ') + '</small></div>' +
        (topLangs.length ? '<div class="arch-stat"><span>主要语言</span><strong style="font-size:13px">' +
          topLangs.map(function (k) { return esc(k) + ' ' + langCnt[k]; }).join(' / ') + '</strong></div>' : '') +
        '</div>';

      h += '<div class="filter-line">' +
        ['all', 'ops', 'use', 'build'].map(function (p) {
          return '<button class="dbtab' + (state.persona === p ? ' is-active' : '') + '" data-persona="' + p + '">' +
            (p === 'all' ? '全部人群' : PLABEL[p]) + '</button>';
        }).join('') +
        '<span class="hint">' + esc(arc.db) + ' 档案 · 全部 ' + fmtFull(arc.total) + ' 项（star≥10）· 更新于 ' + esc(arc.date) + '</span></div>';

      function filtered(list) {
        return (list || []).filter(function (r) {
          if (state.persona !== 'all' && r.persona !== state.persona) return false;
          return true;
        }).sort(function (a, b) { return (b.stars || 0) - (a.stars || 0); });
      }

      var order = (m ? m.cat_order : []).concat(['其他']);
      var shownAny = false;
      order.forEach(function (cat) {
        if (!arc.groups[cat]) return;
        var list = filtered(arc.groups[cat]);
        if (!list.length) return;
        shownAny = true;
        h += '<div class="group-label">' + esc(cat) + (cat === '其他' ? ' <small style="color:var(--muted)">' + list.length + ' 个 · 批量 AI 分类后归位</small>'
          : '<small>' + list.length + ' 个</small>') + '</div>' +
          '<div class="grid">' + list.slice(0, 8).map(mapCard).join('') + '</div>' +
          (list.length > 8 ? '<div class="more-line"><button class="more-btn" data-g="' + esc(cat) + '">还有 ' + (list.length - 8) + ' 个 · 展开</button></div>' : '');
      });
      if (!shownAny) h += emptyBox('当前筛选下没有项目', '试试切换人群。');

      host.innerHTML = h;

      host.querySelectorAll('[data-persona]').forEach(function (b) {
        b.addEventListener('click', function () {
          state.persona = b.getAttribute('data-persona');
          renderArchBody(token);
        });
      });
      host.querySelectorAll('.more-btn[data-g]').forEach(function (b) {
        b.addEventListener('click', function () {
          var cat = b.getAttribute('data-g');
          var list = filtered(arc.groups[cat]);
          var g = document.createElement('div');
          g.className = 'grid';
          g.style.marginTop = '11px';
          g.innerHTML = list.slice(8).map(mapCard).join('');
          b.closest('.more-line').replaceWith(g);
        });
      });
    });
  }

  /* ================= 导航 / 主题 / 页脚 ================= */

  function setNav(key) {
    document.querySelectorAll('.nav a[data-nav]').forEach(function (a) {
      a.classList.toggle('is-active', a.getAttribute('data-nav') === key);
    });
  }

  function bindTheme() {
    var btn = document.getElementById('theme-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme') ||
        (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) { /* 忽略 */ }
    });
  }

  function fillChrome() {
    var now = state.now || {};
    var bw = document.getElementById('bdg-weekly'), bp = document.getElementById('bdg-past'), bm = document.getElementById('bdg-map');
    var n = latestWeeklyNo();
    if (bw) bw.textContent = n ? '第 ' + n + ' 期' : '—';
    if (bp) bp.textContent = ((state.idx && state.idx.entries) || []).length + ' 篇';
    if (bm) bm.textContent = fmt(now.map_total) + ' 工具';
    var sub = document.getElementById('brand-sub');
    if (sub && now.updated) sub.textContent = '更新于 ' + now.updated + ' · 日更';
    var brand = document.getElementById('brand');
    if (brand) brand.addEventListener('click', function () { location.hash = '#/weekly'; });

    var foot = document.getElementById('foot');
    if (foot) {
      var c = (state.site || {}).contact || {};
      var mail = (c.items || []).filter(function (it) { return it.href; })[0];
      var mp = (c.items || []).filter(function (it) { return /公众号/.test(it.label || '') || it.value === 'DB智能体'; })[0];
      foot.innerHTML = '<div class="frow"><span><b style="color:var(--ink)">数据库开源生态观察</b> · ' +
        '四个入口：周报（节奏）/ 往期（回溯）/ 月度速报（纵深）/ 生态地图（资产）· 数据来源：GitHub 公开数据' +
        (now.updated ? ' · 更新至 ' + esc(now.updated) : '') + '</span><span>' +
        (mail ? '<a href="' + esc(mail.href) + '">' + esc(mail.value) + '</a>' : '') +
        (mp ? ' · 公众号 ' + esc(mp.value) : '') + '</span></div>';
    }
  }

  /* ================= 路由 ================= */

  function render(r) {
    var token = ++navToken;
    if (r.weekly !== undefined) {
      var n = r.weekly !== null ? r.weekly : latestWeeklyNo();
      if (n === null) { renderPast(); return; }
      renderWeekly(n, token);
    } else if (r.past) {
      renderPast();
    } else if (r.monthly !== undefined) {
      renderMonthly(r.monthly, token);
    } else if (r.map) {
      renderMap(token);
    }
    window.scrollTo(0, 0);
  }

  function parseHash() {
    var h = decodeURIComponent(location.hash.replace(/^#/, ''));
    var m;
    if ((m = h.match(/^\/issue\/(?:weekly|monthly)-(\w+)$/))) { location.replace('#/weekly/' + m[1]); return null; }
    if (h.indexOf('/db/') === 0) {
      var name = h.slice(4);
      if (knownSlugs) {
        location.replace('#/archive/' + (knownSlugs[name] || encodeURIComponent(name)));
        return null;
      }
      getJson('data/site/map.json').then(function (mm) {
        knownSlugs = mm && mm.db_slug || {};
        location.replace(knownSlugs[name] ? '#/archive/' + knownSlugs[name] : '#/map');
      });
      return null;
    }
    if ((m = h.match(/^\/weekly\/(\d+)$/))) return { weekly: Number(m[1]) };
    if (h === '/weekly' || h === '') return { weekly: null };
    if (h === '/past') return { past: true };
    if ((m = h.match(/^\/monthly\/(\d{4}-\d{2})$/))) return { monthly: m[1] };
    if (h === '/monthly') return { monthly: null };
    if (h === '/map') return { map: true };
    if (h.indexOf('/archive/') === 0) {
      var slug = h.slice('/archive/'.length);
      state.mapTab = 'arch';
      /* slug → 真实库名（db_slug 反查） */
      var found = slug;
      getJson('data/site/map.json').then(function (mm) {
        if (!mm) return;
        MAPC = mm; knownSlugs = mm.db_slug || {};
        Object.keys(mm.db_slug).forEach(function (db) { if (mm.db_slug[db] === slug) found = db; });
        state.db = found;
        var token = ++navToken;
        renderMap(token);
      });
      return { map: true };
    }
    return { weekly: null };
  }

  function route() {
    var r = parseHash();
    if (r) render(r);
  }

  /* ================= 启动 ================= */

  bindTheme();
  Promise.all([getJson('data/site.json'), getJson('data/site/now.json'), getJson('data/site/issues-index.json')])
    .then(function (trio) {
      state.site = trio[0] || {};
      state.now = trio[1] || {};
      state.idx = trio[2] || { entries: [] };
      if (state.site.title) document.title = state.site.title;
      fillChrome();
      window.addEventListener('hashchange', route);
      route();
    })
    .catch(function () {
      app.innerHTML = emptyBox('数据加载失败', '请通过本地服务器或线上地址打开，确保 data/site/ 目录可访问。');
    });
})();
