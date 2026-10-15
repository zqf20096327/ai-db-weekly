# -*- coding: utf-8 -*-
"""数据装载层：唯一知道 dbhub_collect 目录布局的模块。

对接 M2b 后的新数据形态：
  池       data/live/pool{,_intl,_cn}.ndjson（NDJSON 活文件；无活文件时
           回退 glob 旧快照 snapshot_*/pool*.json）
  解读缓存 state/interp_cache_shards/00~ff.json（256 分片，键=sha，
           条目内含 fn；同 fn 多条取 generated_at 最新）
  富集缓存 state/enrich_cache_shards/00~ff.json（256 分片，键=fn）
  增星基准 dbhub_collect git 历史里旧版 pool.ndjson（~7 天前 commit；
           找不到时回退最早可用版本并告警——旧 merged/ 管道数据源已消失）

失败策略：池缺失硬失败，缓存缺失软失败
（返回空并在 stderr 告警，页面降级但构建不阻断）。
"""
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

LIVE = "live"
SHARD_DIRS = ("state/interp_cache_shards", "state/enrich_cache_shards")


@dataclass
class SourceBundle:
    """一次构建的全部输入。"""
    collect_dir: str
    snap: str = ""                 # 快照日期 YYYYMMDD
    pool: list = field(default_factory=list)          # 按 (-stars, fn) 排序
    intl_set: set = field(default_factory=set)
    cn_set: set = field(default_factory=set)
    interp: dict = field(default_factory=dict)        # fn -> 最新解读条目
    enrich: dict = field(default_factory=dict)        # fn -> 富集字段
    overrides: dict = field(default_factory=dict)     # fn -> 签发认领
    profiles: list = field(default_factory=list)
    glob: dict = field(default_factory=dict)
    old_stars: dict = field(default_factory=dict)     # 增星基准 fn -> stars
    old_date: str = ""


def _warn(msg):
    print("[sources] 警告: %s" % msg, file=sys.stderr)


# ---------------------------------------------------------------- 池
def _iter_ndjson(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _sorted_pool(items):
    """stars 降序、同星按 fn —— 对齐旧管道 pool.json 的排序行为。"""
    return sorted(items, key=lambda it: (-(it.get("stars") or 0), it["full_name"]))


def load_pool_sections(collect_dir):
    """返回 (pool, intl_set, cn_set)。活文件优先，回退最新旧格式快照。"""
    base = os.path.join(collect_dir, "data")
    live = os.path.join(base, LIVE)
    if os.path.isfile(os.path.join(live, "pool.ndjson")):
        pool = _sorted_pool(_iter_ndjson(os.path.join(live, "pool.ndjson")))
        intl = {p["full_name"] for p in
                _iter_ndjson(os.path.join(live, "pool_intl.ndjson"))}
        cn = {p["full_name"] for p in
              _iter_ndjson(os.path.join(live, "pool_cn.ndjson"))}
        return pool, intl, cn
    # 回退：最新旧快照（无时间窗；M2b 切换过渡期语义）
    cands = []
    for d in os.listdir(base):
        m = re.fullmatch(r"snapshot_(\d{8})", d)
        if m:
            pj = os.path.join(base, d, "pool.json")
            if os.path.isfile(pj) and os.path.getsize(pj) > 1000:
                cands.append((os.path.join(base, d), m.group(1)))
    if not cands:
        raise SystemExit("no pool found: data/live/pool.ndjson 与旧快照均缺失")
    snap_dir, _ = max(cands)
    pool = _sorted_pool(json.load(open(os.path.join(snap_dir, "pool.json"),
                                      encoding="utf-8")))
    intl = {p["full_name"] for p in json.load(
        open(os.path.join(snap_dir, "pool_intl.json"), encoding="utf-8"))}
    cn = {p["full_name"] for p in json.load(
        open(os.path.join(snap_dir, "pool_cn.json"), encoding="utf-8"))}
    return pool, intl, cn


def snap_date(collect_dir):
    """快照日期：snapshot_YYYYMMDD 目录名（轻量标记随 git 走，不受 git
    pull 刷新 mtime 影响）。目录全无 = 本地数据未就绪，硬失败。"""
    base = os.path.join(collect_dir, "data")
    dates = sorted((m.group(1) for d in os.listdir(base)
                    if (m := re.fullmatch(r"snapshot_(\d{8})", d))), reverse=True)
    if dates:
        return dates[0]
    raise SystemExit("cannot determine snapshot date: no snapshot_YYYYMMDD dir")


# ---------------------------------------------------------------- 缓存分片
def load_sharded(shard_dir):
    """256 分片合并为单 dict。"""
    out = {}
    if not os.path.isdir(shard_dir):
        return out
    for name in sorted(os.listdir(shard_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(shard_dir, name), encoding="utf-8") as f:
            out.update(json.load(f))
    return out


def load_interp(collect_dir):
    """interp_state(fn→sha) 主索引 × 缓存(sha→条目)——镜像复用仓（reused:true）也能取到内容。

    10-10 前旧版按缓存条目内 fn 字段建索引：fork/搬家仓与原仓 readme 同 sha、
    解读条目的 fn 只写原仓名，镜像仓在全站索引中不存在（oceanbase/goInception
    即此例）。interp_state 是权威账目（33,806 done fn，含 412 镜像补账），
    天然一 fn 一 sha，无需 generated_at 比较；state 缺失时回退旧语义。"""
    raw = load_sharded(os.path.join(collect_dir, SHARD_DIRS[0]))
    if not raw:
        _warn("interp 缓存为空：%s" % os.path.join(collect_dir, SHARD_DIRS[0]))
        return {}
    st_path = os.path.join(collect_dir, "state", "interp_state.json")
    if os.path.isfile(st_path):
        with open(st_path, encoding="utf-8") as f:
            items = (json.load(f).get("items") or {})
        byfn, missing = {}, 0
        for fn, v in items.items():
            if v.get("status") != "done":
                continue
            e = raw.get(v.get("sha"))
            if e is None:
                missing += 1
                continue
            byfn[fn] = e
        if missing:
            _warn("interp_state %d 个 done fn 的 sha 不在缓存（跳过）" % missing)
        return byfn
    byfn = {}
    for v in raw.values():
        fn = v.get("fn")
        if not fn:
            continue
        cur = byfn.get(fn)
        if cur is None or (v.get("generated_at") or "") >= (cur.get("generated_at") or ""):
            byfn[fn] = v
    return byfn


def load_enrich(collect_dir):
    raw = load_sharded(os.path.join(collect_dir, SHARD_DIRS[1]))
    if not raw:
        _warn("enrich 缓存为空：%s" % os.path.join(collect_dir, SHARD_DIRS[1]))
    return raw


def load_overrides(collect_dir):
    """config/overrides.json（人工签发认领，第五通道），剥离 _ 开头说明键。"""
    path = os.path.join(collect_dir, "config", "overrides.json")
    if not os.path.isfile(path):
        return {}
    data = json.load(open(path, encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


# ---------------------------------------------------------------- 增星基准
def _git(collect_dir, *args):
    """跑 git 子命令，失败返回 None（rebase 中/浅克隆/损坏均降级）。"""
    try:
        r = subprocess.run(["git", "-C", collect_dir, *args],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _pool_stars_from_rev(collect_dir, rev):
    """git show <rev>:data/live/pool.ndjson → {fn: stars}。"""
    content = _git(collect_dir, "show", "%s:data/live/pool.ndjson" % rev)
    if content is None:
        return {}
    out = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            it = json.loads(line)
        except json.JSONDecodeError:
            continue
        fn, st = it.get("full_name"), it.get("stars")
        if fn and st is not None:
            out[fn] = st
    return out


def _find_rev_before(collect_dir, want_iso, path):
    """git 历史中 ≤want(UTC) 的最新 commit（改动指定路径）；无则 None。

    --before 必须带 Z 后缀按 UTC 解释：采集 commit 均为 UTC 时区（CI 提交，
    常在 UTC 傍晚），无后缀时 git 按本地时区(+8)解释，窗口被砍 8 小时——
    M2b 后 pool.ndjson 的全部历史恰好都落在被砍掉的时段内，通道①整体失效。
    日期取 %aI（ISO 原始时区）换算 UTC，与 snap 目录名（UTC 日期）同口径。
    """
    out = _git(collect_dir, "log", "--pretty=format:%H %aI",
               "--before=%sT23:59:59Z" % want_iso,
               "-1", "--", path)
    if out and out.strip():
        parts = out.strip().splitlines()[-1].split(" ", 1)
        if len(parts) == 2:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(parts[1]).astimezone(timezone.utc)
                return parts[0], dt.strftime("%Y%m%d")
            except ValueError:
                pass
    return None, None


def _legacy_snapshot_stars(collect_dir, want8):
    """M2b 前的旧格式快照池（git 历史树里 2026-08-05～10-03）作基准。

    取 ≤want 的最新 snapshot_YYYYMMDD/pool.json。工作区中这些目录已
    被滚动归档清理，仅存在于 git 历史中。
    """
    out = _git(collect_dir, "log", "--pretty=format:%H",
               "--before=%s-%s-%sT23:59:59Z" % (want8[:4], want8[4:6], want8[6:]),
               "-1")
    rev = (out or "").strip().splitlines()[-1].strip() if out and out.strip() else ""
    if not rev:
        return {}, ""
    tree = _git(collect_dir, "ls-tree", "--name-only", rev, "data/") or ""
    days = sorted(m.group(1) for line in tree.splitlines()
                  if (m := re.fullmatch(r"data/snapshot_(\d{8})", line.strip())))
    ok = [d for d in days if d <= want8]
    if not ok:
        return {}, ""
    day = ok[-1]
    content = _git(collect_dir, "show", "%s:data/snapshot_%s/pool.json" % (rev, day))
    if not content:
        return {}, ""
    try:
        arr = json.loads(content)
    except json.JSONDecodeError:
        return {}, ""
    stars = {}
    for r in arr:
        fn, st = r.get("full_name"), r.get("stargazers_count", r.get("stars"))
        if fn and st is not None:
            stars[fn] = st
    return stars, day


def growth_base(collect_dir, snap):
    """~7 天前的池快照作增星基准（g7 = 今日星 − 基准星）。

    三级回退，全部只在 git 历史里找（工作区的旧格式数据已被滚动归档清理）：
      ① data/live/pool.ndjson 的 ≤want 历史版本（M2b 后主力通道）
      ② M2b 前旧格式 snapshot_YYYYMMDD/pool.json（过渡期池）
      ③ live 活文件的最早历史版本（基准天数偏短，告警标注）
    git 不可用时返回空——g7 全空、构建不阻断（与旧管道软失败语义一致）。
    """
    from datetime import date, timedelta
    d = date(int(snap[:4]), int(snap[4:6]), int(snap[6:]))
    want_iso = (d + timedelta(days=-7)).strftime("%Y-%m-%d")
    want8 = want_iso.replace("-", "")
    live = "data/live/pool.ndjson"

    rev, date8 = _find_rev_before(collect_dir, want_iso, live)
    if rev:
        stars = _pool_stars_from_rev(collect_dir, rev)
        if stars:
            return stars, date8
    stars, day = _legacy_snapshot_stars(collect_dir, want8)
    if stars:
        return stars, day
    # 回退：live 活文件的最早历史版本（--follow 追 M2b 切换的 rename 链；
    # 不用 --reverse——与 --follow 不兼容，全量取最后一行即最早提交）
    out = _git(collect_dir, "log", "--pretty=format:%H %ad",
               "--date=format:%Y%m%d", "--follow", "--", live)
    if out and out.strip():
        parts = out.strip().splitlines()[-1].split(" ", 1)
        if len(parts) == 2:
            stars = _pool_stars_from_rev(collect_dir, parts[0])
            if stars:
                _warn("增星基准无 7 天窗内版本，回退最早 live 版本 %s（%s）"
                      % (parts[1], parts[0][:8]))
                return stars, parts[1]
    _warn("增星基准不可用（git 历史缺失）——g7 将全部为空")
    return {}, ""


# ---------------------------------------------------------------- README
RM_NOISE = re.compile(r"(!\[[^\]]*\]\([^)]*\)|<[^>]+>|\[!\[[^\]]*\]\([^)]*\)\]"
                      r"\([^)]*\)|\[|\]|#{1,6} |\*{1,3})")


def readme_head(collect_dir, fn, n=400):
    path = os.path.join(collect_dir, "data", "readmes",
                        fn.replace("/", "__") + ".md")
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            txt = f.read(1200)
    except OSError:
        return ""
    txt = RM_NOISE.sub(" ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:n]


# ---------------------------------------------------------------- 编排
def load_bundle(collect_dir):
    """装载全部输入，返回 SourceBundle。"""
    import taxonomy
    bundle = SourceBundle(collect_dir=collect_dir)
    bundle.snap = snap_date(collect_dir)
    bundle.pool, bundle.intl_set, bundle.cn_set = load_pool_sections(collect_dir)
    bundle.interp = load_interp(collect_dir)
    bundle.enrich = load_enrich(collect_dir)
    bundle.overrides = load_overrides(collect_dir)
    bundle.profiles, bundle.glob = taxonomy.load_profiles(collect_dir)
    bundle.old_stars, bundle.old_date = growth_base(collect_dir, bundle.snap)
    return bundle
