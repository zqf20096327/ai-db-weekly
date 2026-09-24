# -*- coding: utf-8 -*-
"""模块 4：月度速报聚合（每月 1 日跑，或任意时候预览当月）。

从 history 周锚点 + org 首末日快照计算：
  BLOG_SITE_DIR/monthly-{YYYY-MM}.json
    top_gain     月窗 Star 净增 Top10（watched ∩ 当日范围内）
    streaks      连涨 ≥3 周
    orgs         官方组织月度观测（活跃/活跃率/月内新开，首扫标注）
    month_new    月度新入池 Top5

用法：
  python site_export/aggregate_monthly.py                # 最新观察日所在月，滚动 26-38 天窗
  python site_export/aggregate_monthly.py --date 20260921
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_common as sc  # noqa: E402

log = logging.getLogger("monthly")


def main() -> None:
    ap = argparse.ArgumentParser(description="月度聚合")
    ap.add_argument("--date", help="观察日 YYYYMMDD（默认最新）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-6s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    dates = sc.snapshot_dates()
    latest = args.date or (dates[-1] if dates else None)
    if not latest or latest not in dates:
        log.error("观察日不存在：%s", args.date)
        sys.exit(2)
    base = sc.month_window(latest, dates)
    if not base:
        log.error("找不到 %s 之前 26-38 天的基准观察日（数据积累不足）。", latest)
        sys.exit(2)
    h = sc.load_history()
    sc.bind_history(h)
    log.info("月窗：%s → %s", base, latest)

    pool = sc.read_pool(latest) or []
    scoped_names = {it.get("full_name") for it in sc.scoped_items(pool)}
    pool_map = {it.get("full_name"): it for it in pool}

    # ---- 月度涨幅（watched ∩ 当日范围内，两端都有数据）----
    gains = []
    for fn in scoped_names:
        w = h["watched"].get(fn)
        if not w:
            continue
        a, b = sc.star_at(w, dates, base), sc.star_at(w, dates, latest)
        if a is None or b is None or b <= a:
            continue
        it = pool_map.get(fn) or {}
        r = sc.record(it, growth=b - a)
        _, gs = sc.streaks_of(w)
        r["gain"] = b - a
        r["growth_streak"] = gs
        gains.append(r)
    gains.sort(key=lambda r: -r["gain"])
    top_gain = [{k: r[k] for k in ("fn", "url", "stars", "gain", "section", "cat",
                                   "license", "lang", "growth_streak")}
                for r in gains[:10]]

    # ---- 连涨 ≥3 周 ----
    streaks = []
    for fn in scoped_names:
        w = h["watched"].get(fn)
        if not w:
            continue
        wp, gs = sc.streaks_of(w)
        if gs >= 3:
            it = pool_map.get(fn) or {}
            r = sc.record(it, growth=(w.get("daily") or {}).get(latest))
            streaks.append({"fn": r["fn"], "url": r["url"], "stars": r["stars"],
                            "streak": gs, "weeks": wp, "growth": r["growth"], "cat": r["cat"]})
    streaks.sort(key=lambda x: (-x["streak"], -x["stars"]))
    streaks = streaks[:10]

    # ---- 月度新入池（watched 首见日 ≥ base）----
    month_new = [fn for fn, w in h["watched"].items()
                 if fn in scoped_names and (w.get("first_seen") or "99999999") >= base]
    month_new_top = []
    for fn in sorted(month_new, key=lambda f: -(h["watched"][f].get("stars") or 0))[:5]:
        it = pool_map.get(fn) or {}
        r = sc.record(it)
        month_new_top.append({k: r[k] for k in ("fn", "url", "stars", "section", "license")})

    # ---- org 月度观测 ----
    cur_orgs = sc.read_orgs(latest) or {}
    org_base = sc.org_base_date(base, dates) or base
    base_orgs = sc.read_orgs(org_base) or {}
    log.info("org 基准日：%s（月窗基准 %s 无 orgs 时就近回退）", org_base, base)
    orgs = []
    for org, cur in cur_orgs.items():
        cur_map = {(r.get("full_name") or ""): r for r in cur}
        prev_names = None
        if org in base_orgs:
            prev_names = {(r.get("full_name") or "") for r in base_orgs[org]}
        base_iso = f"{base[:4]}-{base[4:6]}-{base[6:]}"
        active = [r for r in cur_map.values() if (r.get("pushed_at") or "") >= base_iso]
        new_list = None
        if prev_names is not None:
            new_list = [fn for fn in cur_map
                        if fn not in prev_names and not fn.split("/")[-1].startswith(".")]
        orgs.append({
            "org": org, "repos": len(cur_map), "active": len(active),
            "new": len(new_list) if new_list is not None else None,
            "first_scan": prev_names is None,
            "new_list": (new_list or [])[:3],
        })
    orgs.sort(key=lambda o: (-o["active"], -o["repos"]))
    orgs = orgs[:12]

    month_key = f"{latest[:4]}-{latest[4:6]}"
    out = {
        "month": month_key,
        "window": {"from": f"{base[:4]}-{base[4:6]}-{base[6:]}",
                   "to": f"{latest[:4]}-{latest[4:6]}-{latest[6:]}"},
        "top_gain": top_gain, "streaks": streaks,
        "month_new_count": len(month_new), "month_new_top": month_new_top,
        "orgs": orgs,
    }
    sc.write_site_json(f"monthly-{month_key}.json", out)
    log.info("==== 月度 %s 完成：黑马 %d · 连涨≥3周 %d · 月新入池 %d · org %d ====",
             month_key, len(top_gain), len(streaks), len(month_new), len(orgs))


if __name__ == "__main__":
    main()
