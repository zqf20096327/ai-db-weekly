"""周报生产编排入口（双篇：主周报 + 工具合辑周报）。

与 run_daily.py（每日采集）并列的独立编排。跑通 4 个阶段：
  1. releases    数据源3 Release 采集（对候选池头部）
  2. license     数据源5 License 变更检测（对候选池头部）
  3. compute     analytics：7天diff + 价值评分 + 信号分 + 榜单归属
  4. render      render：两份 Markdown
                   - weekly/report.md   主周报（导语→精选→速递→新生→Top→License）
                   - weekly/toolkit.md  工具合辑周报（六类工具体检→新晋→静默→趋势）

依赖 run_daily 已产出当日候选池（merged/all_projects.json）。

用法：
  python run_weekly.py                       # 全流程（含 releases/license 采集）
  python run_weekly.py --only compute        # 只算（diff/评分/归属），不调 GitHub
  python run_weekly.py --only render         # 只渲染（需已有 compute 结果）
  python run_weekly.py --only releases
  python run_weekly.py --only license
  python run_weekly.py --date 20260806 --prev-date 20260531
  python run_weekly.py --no-resume           # 强制重算（忽略断点）
  python run_weekly.py -v
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Any

import config
import storage
from ai_client import AIClient
from github_client import GitHubClient

from collectors import releases as releases_mod
from collectors import license_changes as license_mod
from collectors import readme as readme_mod

import analytics
import filters
import render
import templates as T

log = logging.getLogger("run_weekly")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def _load_candidate_pool(date: str) -> list[dict[str, Any]]:
    """读当日候选池（run_daily 产出）。不存在则报错退出。"""
    pool = storage.load_snapshot_pool(date)
    if not pool:
        log.error("当日候选池不存在或为空：%s\n请先跑 `python run_daily.py` 完成每日采集。", date)
        sys.exit(2)
    return pool


def stage_releases(client: GitHubClient, pool: list[dict[str, Any]], date: str, resume: bool) -> dict[str, Any]:
    """阶段1：数据源3 Release 采集。"""
    log.info("==== 阶段1：Release 采集 ====")
    return releases_mod.collect_releases(client, pool, resume=resume, date=date)


def stage_license(client: GitHubClient, pool: list[dict[str, Any]], date: str, resume: bool) -> dict[str, Any]:
    """阶段2：数据源5 License 变更检测。"""
    log.info("==== 阶段2：License 变更检测 ====")
    return license_mod.collect_license_changes(client, pool, resume=resume, date=date)


def stage_compute(
    pool: list[dict[str, Any]],
    date: str,
    prev_date: str | None,
    releases_summary: dict[str, Any],
    license_summary: dict[str, Any],
) -> dict[str, Any]:
    """阶段3：对比计算 + 评分 + 信号分 + 榜单归属（纯本地，不调 GitHub）。

    返回所有中间数据，供 render 使用，并落盘到 weekly/meta/。
    """
    log.info("==== 阶段3：计算（diff / 评分 / 信号分 / 归属）====")

    # 3a. 7 天 diff（SOP 4.1）—— 两端都用展示池，保证"本周/基准周"口径一致
    #     候选池含伪相关（plane/twenty 等），展示榜①⑤⑧只看数据库相关项目，
    #     故 diff 也基于过滤后的池，否则伪相关项目会污染上涨榜。
    prev_pool = storage.load_snapshot_pool(prev_date) if prev_date else None
    if prev_pool is not None:
        prev_pool = filters.filter_display_pool(prev_pool)
    diffs = analytics.diff_snapshots(pool, prev_pool)
    log.info(
        "diff：%s（基准 %s），star 增量 %d 项，新入榜 %d，掉榜 %d",
        "首期(无基准)" if diffs["first_period"] else "正常",
        prev_date or "无",
        len(diffs["star_deltas"]),
        len(diffs["new_entries"]),
        len(diffs["dropped"]),
    )
    storage.save_weekly_meta("diff", {
        **diffs,
        "current_date": date,
        "prev_date": prev_date,
    }, date)

    # 3b. 主版本号变更 + 信号分（SOP ④）
    week_releases = releases_summary.get("releases", []) if releases_summary else []
    # by_repo_all_tags 暂无历史 tag 上下文（release 采集未存全量 tag），
    # major_bumps 保守返回空；后续可扩展 release 采集存全量 tag 后启用
    major_bumps = analytics.detect_major_version_bump(week_releases, by_repo_all_tags=None)
    license_changed = {
        c["repo_full_name"] for c in (license_summary.get("changed", []) if license_summary else [])
    }
    focus_items = analytics.top_focus_items(
        pool, diffs=diffs, releases=week_releases,
        license_changed=license_changed, major_bumps=major_bumps,
    )
    log.info("本周重点：%d 个（信号分前 %d）", len(focus_items), config.FOCUS_MAX_ITEMS)

    # 3c. 价值评分（SOP 6 第3层，仅排序用）
    scored_pool = sorted(
        pool, key=lambda it: analytics.value_score(it, diffs), reverse=True
    )

    # 3d. 榜单归属（SOP 6.y 分层漏斗）
    focus_fulls = {f["item"].get("full_name", "") for f in focus_items}
    rising_rows = analytics.rising_list(diffs, {it.get("full_name", ""): it for it in pool})
    rising_fulls = {r["full_name"] for r in rising_rows}
    attribution = analytics.assign_main_section(
        pool, focus_fulls, diffs, rising_fulls,
    )

    scoring_summary = {
        "snapshot_date": config.TODAY_HUMAN,
        "first_period": diffs["first_period"],
        "prev_date": prev_date,
        "major_bumps": sorted(major_bumps),
        "license_changed": sorted(license_changed),
        "focus_items": [
            {"full_name": f["item"].get("full_name"), "signal_score": f["signal_score"], "reasons": f["reasons"]}
            for f in focus_items
        ],
        "rising_top": [{"full_name": r["full_name"], "star_delta": r["star_delta"]} for r in rising_rows],
    }
    storage.save_weekly_meta("scoring", scoring_summary, date)
    storage.save_weekly_meta("attribution", attribution, date)

    return {
        "diffs": diffs,
        "focus_items": focus_items,
        "rising_rows": rising_rows,
        "attribution": attribution,
        "scored_pool": scored_pool,
    }


def stage_render(
    pool: list[dict[str, Any]],
    date: str,
    computed: dict[str, Any],
    releases_summary: dict[str, Any],
    license_summary: dict[str, Any],
) -> tuple[str, str]:
    """阶段4：双篇 Markdown 渲染 → weekly/report.md + weekly/toolkit.md。"""
    log.info("==== 阶段4：渲染（主周报 + 工具合辑周报）====")

    releases = (releases_summary or {}).get("releases", [])
    diffs = computed["diffs"]
    attribution = computed.get("attribution", {})

    # 新生项目榜数据：从 new_projects/ 目录读（不依赖 diff，首期即可完整）
    new_projects = storage.load_all_new_projects(date)

    # ---- 精选候选 README 采集（2-3 个，供 AI 解读）----
    pool_map = {it.get("full_name", ""): it for it in pool}
    latest_rel = render._latest_release_per_repo(releases)
    focus_candidates = render._select_focus_candidates(
        pool_map, diffs.get("star_deltas", {}), latest_rel,
    )
    readmes: dict[str, str] = {}
    if focus_candidates:
        client = GitHubClient()
        readmes = readme_mod.collect_readmes(
            client, focus_candidates, resume=True, date=date,
        )

    # ---- 主周报 ----
    report_md = render.render_main_report(
        snapshot_date=config.TODAY_HUMAN,
        pool=pool,
        diffs=diffs,
        releases=releases,
        license_summary=license_summary or {},
        new_projects=new_projects,
        attribution=attribution,
        readmes=readmes,
    )
    report_path = storage.report_file(date)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    log.info("主周报已生成：%s", report_path)

    # ---- 工具合辑周报 ----
    toolkit_md = render.render_toolkit_report(
        snapshot_date=config.TODAY_HUMAN,
        pool=pool,
        diffs=diffs,
        releases=releases,
    )
    toolkit_path = storage.toolkit_file(date)
    with open(toolkit_path, "w", encoding="utf-8") as f:
        f.write(toolkit_md)
    log.info("工具合辑周报已生成：%s", toolkit_path)

    return report_path, toolkit_path


def run_pipeline(args: argparse.Namespace) -> None:
    date = args.date or config.TODAY
    resume = not args.no_resume

    # release/license 采集上限覆盖（仅本次运行，不改 config.py）
    if args.acquire_cap is not None:
        config.RELEASE_MAX_REPOS = args.acquire_cap
        config.LICENSE_MAX_REPOS = args.acquire_cap

    start = time.time()
    only = args.only

    # 候选池：全量给 release/license 采集；展示池（数据库相关）给 compute/render/diff
    # SOP 6.y 第二层分工：①⑤⑧ 展示榜只收"本身是数据库相关"的项目，防 plane/twenty 这类
    # 靠 topic 弱命中混进来的伪相关项目霸屏。采集层候选池保持全量（release/license 仍按全量采）。
    pool = _load_candidate_pool(date)
    display_pool = filters.filter_display_pool(pool)
    if len(display_pool) < len(pool):
        log.info(
            "展示相关性过滤：候选池 %d → 展示池 %d（剔除 %d 个非数据库相关）",
            len(pool), len(display_pool), len(pool) - len(display_pool),
        )

    # releases / license 采集需要 client —— 用全量候选池（不因展示过滤而漏采版本/license）
    releases_summary: dict[str, Any] | None = None
    license_summary: dict[str, Any] | None = None
    if only in (None, "releases", "compute", "render"):
        client = GitHubClient()
        if only in (None, "releases"):
            releases_summary = stage_releases(client, pool, date, resume)
        else:
            # compute/render 复用已落盘结果
            r = storage.load_weekly_meta("releases", date)
            releases_summary = r if isinstance(r, dict) else {"releases": []}

        if only in (None, "license"):
            license_summary = stage_license(client, pool, date, resume)
        else:
            l = storage.load_weekly_meta("license_changes", date)
            license_summary = l if isinstance(l, dict) else {"changed": [], "license_snapshot": {}}

    # 自动找基准快照（除非显式指定）
    prev_date = args.prev_date
    if prev_date is None and only in (None, "compute", "render"):
        prev_date = storage.find_prev_snapshot_date(date)
        if prev_date:
            log.info("基准快照（自动定位）：%s", prev_date)
        else:
            log.info("无更早快照，本期为首期（动态栏目将标注'首期无基准'）")

    # compute（纯本地）—— 用展示池
    computed: dict[str, Any] | None = None
    if only in (None, "compute", "render"):
        computed = stage_compute(display_pool, date, prev_date, releases_summary or {}, license_summary or {})

    # render
    if only in (None, "render"):
        if computed is None:
            log.error("render 需先有 compute 结果（请先跑 --only compute 或全流程）")
            sys.exit(2)
        report_path, toolkit_path = stage_render(
            display_pool, date, computed, releases_summary or {}, license_summary or {}
        )
        print()
        print("=" * 56)
        print(f"  主周报：        {report_path}")
        print(f"  工具合辑周报：  {toolkit_path}")
        print(f"  采集日：{config.TODAY_HUMAN} ({date})  基准：{prev_date or '无(首期)'}")
        print("=" * 56)

    elapsed = time.time() - start
    log.info("==== 周报生产完成（耗时 %.1f 分钟）====", elapsed / 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="数据库开源周报 · 周报生产（SOP 第十章，对标 run_daily.py）"
    )
    parser.add_argument(
        "--only",
        choices=["releases", "license", "compute", "render"],
        help="只跑指定阶段（默认全流程）",
    )
    parser.add_argument("--date", help="快照日期 YYYYMMDD（默认今天）")
    parser.add_argument(
        "--prev-date",
        help="对比基准快照日期 YYYYMMDD（默认自动找 7 天前最近的）",
    )
    parser.add_argument(
        "--acquire-cap", type=int, default=None,
        help="release/license 采集上限（覆盖 config，候选池按 star 截断）。"
             "快速验证时设小值（如 30），正式生产用默认 200",
    )
    parser.add_argument(
        "--no-resume", action="store_true",
        help="强制重采/重算（忽略断点续采与已落盘中间结果）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")
    args = parser.parse_args()

    _setup_logging(args.verbose)
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        log.warning("用户中断（中间数据已落盘 weekly/meta/，重跑可续）")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        log.exception("周报生产失败：%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
