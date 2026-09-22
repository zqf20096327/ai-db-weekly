"""M5 富集编排入口：releases 维护信号 + GHSA 安全通告（周节奏，断点续采）。

目标集：最新观察池内 scoped 且 star≥10（≈watched），按 star 降序；--tier1 只采
默认展示档（国际/AI≥300、国产≥50，≈850 项）。

配额账：每 repo 2 次 Core 调用（releases + advisories）；--cap 1500 ≈ 3000 次
≈ 40 分钟。全量 watched（≈5k repo）分 4 次续采跑满（缓存自动跳过已采）。
周度刷新用 --no-resume --tier1 只重采头部。

用法：
  python run_enrich.py                        # 续采，默认 cap
  python run_enrich.py --cap 1500             # 本次最多采 N 个 repo
  python run_enrich.py --only release         # 只跑 releases
  python run_enrich.py --tier1 --no-resume    # 强刷默认展示档
  python run_enrich.py --date 20260922        # 指定快照日
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import config
import filters
import sections
import storage
import tool_registry as reg
from github_client import GitHubClient

from collectors import release_state as rel_mod
from collectors import security as sec_mod

log = logging.getLogger("run_enrich")


def build_targets(pool: list[dict], *, tier1: bool = False) -> list[dict]:
    """观察池 → 富集目标（口径与 site_export.scoped_items / watched 一致）。"""
    out: list[dict] = []
    for it in filters.filter_display_pool(pool):
        fn = it.get("full_name") or ""
        stars = it.get("stargazers_count") or 0
        if not fn or stars < config.ENRICH_STAR_MIN:
            continue
        if (reg.is_kernel(fn) or sections.should_exclude_sop(it)
                or sections.is_out_of_scope(it) or sections.exclusion_reason(it)):
            continue
        sec = sections.assign_section(it)
        if not sec:
            continue
        if tier1:
            thr = 50 if sec == "国产数据库" else 300
            if stars < thr:
                continue
        out.append(it)
    out.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="M5 富集采集（releases + GHSA）")
    ap.add_argument("--only", choices=["release", "security"], help="只跑其中一项（默认都跑）")
    ap.add_argument("--cap", type=int, default=config.ENRICH_MAX_REPOS,
                    help=f"本次最多采 N 个 repo（默认 {config.ENRICH_MAX_REPOS}，断点续采）")
    ap.add_argument("--tier1", action="store_true", help="只采默认展示档（≈850 项）")
    ap.add_argument("--no-resume", action="store_true", help="忽略缓存全量重采（周度刷新）")
    ap.add_argument("--date", help="指定快照日期 YYYYMMDD（默认最新）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    dates = storage.list_snapshot_dates()
    date = args.date or (dates[-1] if dates else None)
    if not date or date not in dates:
        log.error("观察日不存在：%s（可用 %s…%s）", args.date,
                  dates[0] if dates else "-", dates[-1] if dates else "-")
        sys.exit(2)

    from storage import _read_json  # noqa: PLC0415
    pool = _read_json(storage.merged_file(date))
    if not isinstance(pool, list):
        log.error("%s 读不到候选池（先跑 run_daily）", date)
        sys.exit(2)

    targets = build_targets(pool, tier1=args.tier1)
    log.info("富集目标：%d 项（%s，star≥%d%s）", len(targets), date,
             config.ENRICH_STAR_MIN, "，tier1" if args.tier1 else "")

    client = GitHubClient()
    start = time.time()

    if args.only in (None, "release"):
        rel_mod.collect_release_state(
            client, targets, resume=not args.no_resume, date=date, cap=args.cap)
    if args.only in (None, "security"):
        sec_mod.collect_security(
            client, targets, resume=not args.no_resume, date=date, cap=args.cap)

    stats = client.stats.summary()
    log.info("==== 富集完成（%.1f 分钟，Core=%d 调用）====",
             (time.time() - start) / 60, stats["core_calls"])


if __name__ == "__main__":
    main()
