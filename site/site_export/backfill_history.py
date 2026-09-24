# -*- coding: utf-8 -*-
"""模块 1：历史库回填（一次性 / 灾备重建）。

从全部观察日（目录 + zip 归档）重建 site_export/history.json：
  - watched：任一日 范围内且 star≥10 的项目 ∪ 历史上榜 ∪ 历史解读对象
    （watched 项目记每日 star 序列，供 sparkline / 连续性 / 月窗计算）；
  - pool_seen：全池项目只记最后出现日；
  - meta.dates：全部观察日（锚点由此推导，zip 缺口自动跳过）。

用法：
  python site_export/backfill_history.py            # 全量重建
  python site_export/backfill_history.py -v         # 显示进度
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_common as sc  # noqa: E402

log = logging.getLogger("backfill")


def board_and_focus_names() -> set[str]:
    """历史索引里上过榜 / 当过解读对象的项目名。"""
    names: set[str] = set()
    try:
        import json
        h = json.loads((sc.V2_ROOT / "reports" / "weekly_history.json").read_text(encoding="utf-8"))
        for e in h.get("entries") or []:
            for sec in (e.get("sections") or {}).values():
                names |= {r.get("full_name") for r in (sec.get("active") or []) if r.get("full_name")}
                f = sec.get("focus") or {}
                if f.get("full_name"):
                    names.add(f["full_name"])
    except (OSError, json.JSONDecodeError) as e:
        log.warning("weekly_history 读取失败（按空处理）：%s", e)
    return names


def main() -> None:
    ap = argparse.ArgumentParser(description="重建 history.json")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-6s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    dates = sc.snapshot_dates()
    if not dates:
        log.error("data/ 下没有任何快照（目录或 zip）。")
        sys.exit(2)
    honored = board_and_focus_names()
    log.info("观察日 %d 个（%s → %s），历史上榜/解读 %d 个",
             len(dates), dates[0], dates[-1], len(honored))

    watched: dict[str, dict] = {}
    pool_seen: dict[str, str] = {}
    valid_dates: list[str] = []
    no_pool_dates: list[str] = []
    for d in dates:
        pool = sc.read_pool(d)
        if not pool:
            no_pool_dates.append(d)
            log.warning("  %s 无 merged 池，不计入观察日（透明记录于 meta.dates_no_pool）", d)
            continue
        valid_dates.append(d)
        scoped = {it.get("full_name") for it in sc.scoped_items(pool)}
        n_new_w = 0
        for it in pool:
            fn = it.get("full_name") or ""
            if not fn:
                continue
            pool_seen[fn] = d
            stars = it.get("stargazers_count") or 0
            if (fn in honored) or (fn in scoped and stars >= sc.WATCH_STAR_MIN):
                w = watched.get(fn)
                if w is None:
                    w = watched[fn] = {"first_seen": d, "last_seen": d,
                                       "stars": stars, "daily": {}}
                    n_new_w += 1
                w["daily"][d] = stars
                w["last_seen"] = d
                w["stars"] = stars
        log.info("  %s 池 %d · watched +%d（累计 %d）", d, len(pool), n_new_w, len(watched))

    hist = {"meta": {"dates": valid_dates, "updated": valid_dates[-1],
                     "dates_no_pool": no_pool_dates,
                     "watch_rule": "scoped+star>=10|board|focus",
                     "anchors": sc.anchor_dates(valid_dates)},
            "watched": watched, "pool_seen": pool_seen}
    sc.save_history(hist)
    anc = hist["meta"]["anchors"]
    log.info("==== 回填完成：有效观察日 %d（另有 %d 天无池不计入）· watched %d · 全池 seen %d · 周锚点 %d 个（%s…%s） ====",
             len(valid_dates), len(no_pool_dates), len(watched), len(pool_seen), len(anc), anc[0], anc[-1])


if __name__ == "__main__":
    main()
