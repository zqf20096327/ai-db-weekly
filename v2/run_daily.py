"""每日采集编排入口（SOP 4.3「每日凌晨」全部 4 个数据源）。

流程顺序：
  1. 读 .env（GITHUB_TOKEN）
  2. 探测 16 topic 规模           → meta/probe_results.json      （数据源1前置）
  3. topic 采集（分级）           → topics/{topic}.json          （数据源1）
  4. 白名单内核采集               → whitelist/whitelist.json     （数据源1补）
  5. org 全量扫描                 → orgs/{org}.json              （数据源6）
  6. 新生项目 30 天窗             → new_projects/{topic}.json    （数据源2）
  7. 去重合并 → 候选池            → merged/all_projects.json
  8. commit 活跃度（候选池）      → meta/commit_activity.json    （数据源4）
  9. 打印汇总                     → meta/run_summary.json

用法：
  python run_daily.py                        # 全流程
  python run_daily.py --only probe           # 只探测
  python run_daily.py --only topic           # 只采 topic（依赖已有 probe 结果）
  python run_daily.py --only whitelist
  python run_daily.py --only org
  python run_daily.py --only new
  python run_daily.py --only commit          # 只跑 commit 活跃度（需先有候选池）
  python run_daily.py --only merge           # 只合并（不采新数据）
  python run_daily.py --topics tidb,oceanbase --only topic
  python run_daily.py --no-resume            # 强制重采（忽略断点续采）
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

import config
import storage
from github_client import GitHubClient

from collectors import probe as probe_mod
from collectors import topic as topic_mod
from collectors import whitelist as whitelist_mod
from collectors import org_scan as org_mod
from collectors import new_projects as new_mod
from collectors import commit_activity as commit_mod

log = logging.getLogger("run_daily")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def _parse_topics(arg: str | None) -> list[str] | None:
    if not arg:
        return None
    return [t.strip() for t in arg.split(",") if t.strip()]


def build_candidate_pool(date: str | None = None) -> list[dict[str, Any]]:
    """合并 topic + whitelist + org 三源为候选池（不含 new_projects，新生单独成榜）。

    返回合并后的项目列表，并落盘到 merged/all_projects.json。
    """
    topics_items = storage.load_all_topics(date)
    whitelist_items = storage.load_whitelist(date)
    org_items = storage.load_all_orgs(date)

    merged = storage.merge_dedupe(topics_items, whitelist_items, org_items)
    # 按 star 降序排（候选池默认序，便于后续榜单截取）
    merged.sort(key=lambda x: x.get("stargazers_count", 0), reverse=True)
    storage.save_merged(merged, date)
    log.info(
        "候选池合并：topic=%d + whitelist=%d + org=%d → 去重后 %d（已落盘）",
        len(topics_items), len(whitelist_items), len(org_items), len(merged),
    )
    return merged


def run_pipeline(args: argparse.Namespace) -> None:
    date = args.date
    resume = not args.no_resume
    topics = _parse_topics(args.topics)

    start = time.time()
    client = GitHubClient()

    only = args.only

    # ---- 探测 ----
    probe_results: dict[str, Any] | None = None
    if only in (None, "probe"):
        probe_results = probe_mod.probe_all_topics(client, topics, date)

    # ---- topic 采集 ----
    if only in (None, "topic"):
        # 复用本次或已落盘的 probe 结果（拿 tier）
        pr = probe_results or probe_mod.load_probe_results(date)
        topic_mod.collect_all_topics(
            client, topics, probe_results=pr, resume=resume, date=date
        )

    # ---- 白名单 ----
    if only in (None, "whitelist"):
        whitelist_mod.collect_whitelist(client, resume=resume, date=date)

    # ---- org 扫描 ----
    if only in (None, "org"):
        org_mod.collect_all_orgs(client, resume=resume, date=date)

    # ---- 新生项目 ----
    if only in (None, "new"):
        new_mod.collect_all_new_projects(client, topics, resume=resume, date=date)

    # ---- 合并候选池 ----
    candidate_pool: list[dict[str, Any]] | None = None
    if only in (None, "merge", "commit"):
        candidate_pool = build_candidate_pool(date)

    # ---- commit 活跃度（数据源4，依赖候选池）----
    if only in (None, "commit"):
        if candidate_pool is None:
            # 单独跑 commit 时，从磁盘读候选池
            from storage import _read_json  # noqa: PLC0415
            data = _read_json(storage.merged_file(date))
            if not isinstance(data, list):
                log.error("候选池不存在，请先跑 --only merge 或完整流程")
                return
            candidate_pool = data
        commit_mod.collect_commit_activity(
            client, candidate_pool, resume=resume, date=date
        )

    elapsed = time.time() - start
    stats = client.stats.summary()
    log.info("==== 完成（耗时 %.1f 分钟）====", elapsed / 60)

    # 汇总落盘
    summary = {
        "snapshot_date": config.TODAY_HUMAN,
        "elapsed_minutes": round(elapsed / 60, 1),
        "api_calls": stats,
        "stage": only or "full",
    }
    # 若有候选池，补条数
    if candidate_pool is not None:
        summary["candidate_pool_size"] = len(candidate_pool)
    storage.write_run_summary(summary, date)

    # 打印
    print()
    print("=" * 56)
    print(f"  快照日期：{config.TODAY_HUMAN} ({config.TODAY})")
    print(f"  阶段：{only or 'full'}    耗时：{elapsed / 60:.1f} 分钟")
    print(f"  API 调用：Search={stats['search_calls']}  "
          f"Core={stats['core_calls']}  合计={stats['total_calls']}")
    if stats["errors"]:
        print(f"  错误计数：{stats['errors']}")
    if candidate_pool is not None:
        print(f"  候选池：{len(candidate_pool)} 项目（merged/all_projects.json）")
    print("=" * 56)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="数据库开源周报 · 每日采集（SOP 4.3 每日凌晨全数据源）"
    )
    parser.add_argument(
        "--only",
        choices=["probe", "topic", "whitelist", "org", "new", "merge", "commit"],
        help="只跑指定阶段（默认全流程）",
    )
    parser.add_argument("--topics", help="只采指定 topic（逗号分隔，如 tidb,oceanbase）")
    parser.add_argument(
        "--no-resume", action="store_true",
        help="强制重采（忽略断点续采，覆盖当日已有结果）",
    )
    parser.add_argument("--date", help="指定快照日期 YYYYMMDD（默认今天）")
    parser.add_argument(
        "--commit-cap", type=int, default=None,
        help="commit 活跃度采集上限（覆盖 config.COMMIT_ACTIVITY_MAX_REPOS）。"
             "候选池 ~1300+ 项目全量约 45 分钟；设 500 只跑 star 头部大幅省时",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")
    args = parser.parse_args()

    # commit cap 覆盖（不改 config.py，仅本次运行生效）
    if args.commit_cap is not None:
        import config as _cfg  # noqa: PLC0415
        _cfg.COMMIT_ACTIVITY_MAX_REPOS = args.commit_cap

    _setup_logging(args.verbose)
    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        log.warning("用户中断（数据已部分落盘，可断点续采重跑）")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        log.exception("采集失败：%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
