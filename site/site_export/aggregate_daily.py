# -*- coding: utf-8 -*-
"""模块 2：日聚合（每天采集后跑，秒级）。

  ① 增量更新 history.json：watched 当日 star 序列 / pool_seen / 新 watched；
  ② 重生成站点数据（写入 BLOG_SITE_DIR，默认 blog-site/data/site/）：
       now.json                站点状态与 KPI
       map.json                矩阵计数 + 各库统计（不含明细）
       archive-{db}.json       每库明细（按任务分组，全量 ≥10，tier 标默认档）

用法：
  python site_export/aggregate_daily.py                 # 默认最新观察日
  python site_export/aggregate_daily.py --date 20260922
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_common as sc  # noqa: E402

log = logging.getLogger("daily")


def default_tier(r: dict) -> int:
    """默认展示档（渲染选项，随时可调）：国际/AI ≥300；国产板块 ≥50。"""
    if r["section"] == "国产数据库":
        return 1 if r["stars"] >= sc.TIER_CN_DEFAULT else 0
    return 1 if r["stars"] >= sc.TIER_INTL_DEFAULT else 0


def update_history(h: dict, date: str, pool: list, scoped: list[dict]) -> None:
    scoped_names = {it.get("full_name") for it in scoped}
    watched: dict = h["watched"]
    n_new = 0
    for it in pool:
        fn = it.get("full_name") or ""
        if not fn:
            continue
        h["pool_seen"][fn] = date
        stars = it.get("stargazers_count") or 0
        if fn in scoped_names and stars >= sc.WATCH_STAR_MIN:
            w = watched.get(fn)
            if w is None:
                w = watched[fn] = {"first_seen": date, "last_seen": date,
                                   "stars": stars, "daily": {}}
                n_new += 1
            w["daily"][date] = stars
            w["last_seen"] = date
            w["stars"] = stars
    if date not in h["meta"]["dates"]:
        h["meta"]["dates"].append(date)
        h["meta"]["dates"].sort()
    h["meta"]["updated"] = date
    h["meta"]["anchors"] = sc.anchor_dates(h["meta"]["dates"])
    log.info("history 更新：%s 池 %d · watched +%d（累计 %d）",
             date, len(pool), n_new, len(watched))


def build_outputs(h: dict, date: str, pool: list, scoped: list[dict]) -> None:
    valid_dates = [d for d in h["meta"].get("dates") or [] if d < date]
    # 周环比口径：取 5-10 天窗口内「距 7 天最近」的观察日（无则退回上一个有效日）
    from datetime import datetime as _dt
    lt = _dt.strptime(date, "%Y%m%d")
    cands = []
    for d in valid_dates:
        dd = (lt - _dt.strptime(d, "%Y%m%d")).days
        if 5 <= dd <= 10:
            cands.append((abs(dd - 7), d))
    week_base = min(cands)[1] if cands else None
    prev_date = week_base or (valid_dates[-1] if valid_dates else None)
    log.info("增长基准：周环比 vs %s", prev_date)
    prev_daily = {fn: (h["watched"].get(fn, {}).get("daily") or {}).get(prev_date)
                  for fn in (h["watched"] or {})} if prev_date else {}
    sc.bind_history(h)

    # M5 富集数据（周节奏采集 → 就近取最新一份）
    rel_by, rel_date = sc.find_latest_meta("release_state.json", date)
    sec_by, sec_date = sc.find_latest_meta("security.json", date)
    personas = sc.load_personas()
    log.info("富集数据：release_state@%s（%d）· security@%s（%d）· personas（%d）",
             rel_date or "-", len(rel_by), sec_date or "-", len(sec_by), len(personas))

    recs = []
    for it in scoped:
        fn = it.get("full_name") or ""
        stars = it.get("stargazers_count") or 0
        if stars < sc.WATCH_STAR_MIN:
            continue
        prev = prev_daily.get(fn)
        growth = (stars - prev) if prev is not None else None
        r = sc.record(it, growth)
        r["persona"], r["ai"] = sc.persona_of(r["section"], r["cat"], r["fn"], r["desc"])
        e = rel_by.get(fn)
        if e and not e.get("none"):
            r["ver"] = e.get("ver") or ""
            r["verd"] = e.get("days")
            r["n90"] = e.get("n90")
        s = sec_by.get(fn)
        if s is not None:
            r["secn"] = s.get("n", 0)
            r["secw"] = s.get("worst", "")
            r["secl"] = s.get("last", "")
        p = personas.get(fn)
        if p and p.get("p") in ("use", "ops", "build"):
            r["persona"] = p["p"]
            r["ai"] = bool(p.get("ai"))
        w = h["watched"].get(fn)
        wp, gs = sc.streaks_of(w)
        r["weeks_in_pool"], r["growth_streak"] = wp, gs
        r["spark"] = [(w.get("daily") or {}).get(d) for d in h["meta"]["dates"]] if w else []
        r["tier"] = default_tier(r)
        recs.append(r)

    # map.json：矩阵 + 各库统计（不含明细，明细在 archive-{db}.json）
    matrix: dict[str, dict[str, int]] = {db: {c: 0 for c in sc.CAT_ORDER} for db in sc.KNOWN_DBS}
    per_db_recs: dict[str, list[dict]] = defaultdict(list)
    other_cnt: dict[str, int] = defaultdict(int)
    for r in recs:
        if not r["dbs"]:
            continue
        for db in r["dbs"]:
            per_db_recs[db].append(r)
            if r["cat"] in sc.CAT_ORDER:
                matrix[db][r["cat"]] += 1
            else:
                other_cnt[db] += 1
    db_stats = {}
    for db, rs in per_db_recs.items():
        cats: dict[str, int] = defaultdict(int)
        lic: dict[str, int] = defaultdict(int)
        langs: dict[str, int] = defaultdict(int)
        for r in rs:
            cats[r["cat"]] += 1
            lic[r["license"] or "自定义/无"] += 1
            if r["lang"]:
                langs[r["lang"]] += 1
        db_stats[db] = {
            "total": len(rs), "cats": dict(cats),
            "tier_default": sum(1 for r in rs if r["tier"]),
            "week_up": sum(1 for r in rs if (r["growth"] or 0) > 0),
            "licenses": dict(sorted(lic.items(), key=lambda x: -x[1])),
            "langs": dict(sorted(langs.items(), key=lambda x: -x[1])[:4]),
        }
    db_order = [db for db in sorted(db_stats, key=lambda d: -db_stats[d]["total"])]
    date_h = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    sc.write_site_json("map.json", {
        "date": date_h, "total": len(recs),
        "tier_rule": f"国际/AI≥{sc.TIER_INTL_DEFAULT}；国产≥{sc.TIER_CN_DEFAULT}；数据全集 star≥{sc.WATCH_STAR_MIN}",
        "cat_order": sc.CAT_ORDER, "db_order": db_order,
        "db_slug": {db: sc.db_slug(db) for db in db_order},
        "matrix": {db: matrix[db] for db in db_order},
        "other": dict(other_cnt), "dbs": db_stats,
    })
    for db in db_order:
        rs = sorted(per_db_recs[db], key=lambda r: -r["stars"])
        grouped = {c: [] for c in sc.CAT_ORDER + ["其他"]}
        for r in rs:
            grouped[r["cat"]].append(r)
        sc.write_site_json(f"archive-{sc.db_slug(db)}.json", {
            "db": db, "slug": sc.db_slug(db), "date": date_h, "total": len(rs),
            "stats": db_stats[db],
            "groups": {c: v for c, v in grouped.items() if v},
        })

    # now.json
    def _d8(s: str | None) -> str | None:
        return f"{s[:4]}-{s[4:6]}-{s[6:]}" if s else None
    n_rel = sum(1 for r in recs if r.get("ver"))
    n_sec = sum(1 for r in recs if "secn" in r)
    n_ai = sum(1 for r in recs if r.get("persona") in ("use", "ops", "build")
               and r["fn"] in personas)
    sc.write_site_json("now.json", {
        "updated": datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d"),
        "snapshot_days": len(h["meta"]["dates"]),
        "pool_total": len(pool), "pool_scoped": len(scoped),
        "watched": len(h["watched"]),
        "map_total": len(recs), "db_count": len(db_order),
        "tier_default_total": sum(1 for r in recs if r["tier"]),
        "enrich": {
            "release_date": _d8(rel_date), "release_covered": n_rel,
            "security_date": _d8(sec_date), "security_covered": n_sec,
            "personas_ai": n_ai,
        },
    })


def main() -> None:
    ap = argparse.ArgumentParser(description="日聚合")
    ap.add_argument("--date", help="观察日 YYYYMMDD（默认最新）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-6s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    dates = sc.snapshot_dates()
    date = args.date or (dates[-1] if dates else None)
    if not date or date not in dates:
        log.error("观察日不存在：%s（可用：%s…%s）", args.date,
                  dates[0] if dates else "-", dates[-1] if dates else "-")
        sys.exit(2)
    pool = sc.read_pool(date)
    if not pool:
        log.error("%s 读不到 merged 池。", date)
        sys.exit(2)
    scoped = sc.scoped_items(pool)
    log.info("==== 日聚合 %s：池 %d → 范围内 %d ====", date, len(pool), len(scoped))

    h = sc.load_history()
    if h["meta"].get("updated") == date and date in h["meta"].get("dates", []):
        log.info("history 已含 %s，只重生成输出。", date)
    else:
        update_history(h, date, pool, scoped)
        sc.save_history(h)
    sc.bind_history(h)
    build_outputs(h, date, pool, scoped)
    log.info("==== 日聚合完成（输出目录 %s）====", sc.BLOG_SITE_DIR)


if __name__ == "__main__":
    main()
