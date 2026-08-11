"""数据源 4：Commit 活跃度（SOP 4.3 每日采集，候选池合并后跑）。

用途：⑤总榜 🔥 活跃标签 + ④重点信号（活跃度突变）
位置：依赖 merged/all_projects.json 候选池 → 必须排在合并之后
主路径：GET /repos/{owner}/{repo}/stats/participation（52 周每日 commit 数）
        取最后一周（7 天）求和 = commit_count_7d
异步坑：participation 首次常返回 202（还在算，无 body）
        → 轮询（间隔几秒，最多 N 次），仍 202 则兜底用 search commits
兜底：GET /search/commits?q=repo:{o}/{r}+committer-date:>{7天前} 算总数
阈值：commit_count_7d >= COMMIT_ACTIVITY_THRESHOLD → 打 🔥（写 is_active 字段）
依据：SOP 4.2 数据源4 + 4.3（每日）+ 采集策略清单 6c
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import config
import storage
from github_client import GitHubClient, GitHubError, QuerySyntaxError

log = logging.getLogger(__name__)


def _cutoff_iso(days: int = config.COMMIT_LOOKBACK_DAYS) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%d")


def _participation_commit_this_week(participation: dict[str, Any] | None) -> int | None:
    """从 participation 响应取【本周】commit 数。

    participation.all = 长度 52 的数组（每周一个），最后一项 = 本周。
    ⚠️ 粒度限制：participation 是按自然周聚合的，最后一项可能不足 7 天
       （如今天是周三，则只含周一至周三的 commit）。SOP ③ 明确 commit_count
       用于「是否打🔥」的阈值判断，不用于精确排序，故接受此近似。
       字段名为 commit_count_7d（语义=活跃度指标），实际是本周 commit 数。
    返回 None 表示数据不可用。
    """
    if not participation:
        return None
    all_weeks = participation.get("all")
    if not isinstance(all_weeks, list) or len(all_weeks) == 0:
        return None
    last_week = all_weeks[-1] if len(all_weeks) >= 1 else 0
    return int(last_week)


def get_commit_count_7d(
    client: GitHubClient, owner: str, repo: str
) -> tuple[int | None, str]:
    """取某 repo 近 7 天 commit 数。

    返回 (count, source)。source 标识数据来源：
      "participation" / "search_fallback" / "none"（无法获取）
    """
    # 主路径：participation（轮询处理 202）
    for attempt in range(config.PARTICIPATION_POLL_MAX_RETRIES):
        try:
            participation = client.get_participation(owner, repo)
        except GitHubError as e:
            log.debug("participation 调用失败 %s/%s: %s", owner, repo, e)
            break
        if participation is None:
            # 202 异步计算中，等待后重试
            time.sleep(config.PARTICIPATION_POLL_INTERVAL_SEC)
            continue
        count = _participation_commit_this_week(participation)
        if count is not None:
            return count, "participation"
        break

    # 兜底：search commits（占 Search 配额，谨慎用）
    cutoff = _cutoff_iso()
    q = f"repo:{owner}/{repo} committer-date:>{cutoff}"
    try:
        count = client.search_commits_count(q)
        return int(count), "search_fallback"
    except QuerySyntaxError as e:
        log.debug("search commits 兜底失败 %s/%s: %s", owner, repo, e)
        return None, "none"
    except GitHubError as e:
        log.debug("search commits 兜底失败 %s/%s: %s", owner, repo, e)
        return None, "none"


def collect_commit_activity(
    client: GitHubClient,
    candidate_pool: list[dict[str, Any]],
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, Any]:
    """对候选池项目采集 commit 活跃度，回写 commit_count_7d / is_active 字段。

    - 读已落盘的 meta/commit_activity.json 做断点续采（resume=True）
    - 结果写 meta/commit_activity.json + 更新 merged/all_projects.json 的字段
    - 返回统计汇总

    候选池规模控制：SOP 原意"对候选池项目采"。候选池可能很大（15000+），
    对全量逐个调 participation 成本高。这里按 star 降序取前 COMMIT_ACTIVITY_MAX_REPOS。
    """
    # 断点续采：读已有结果
    existing = storage.load_meta("commit_activity", date) if resume else None
    results_map: dict[str, dict[str, Any]] = {}
    if isinstance(existing, dict) and "by_full_name" in existing:
        results_map = existing.get("by_full_name", {}) or {}

    # 候选池按 star 降序截断（控制成本）
    pool_sorted = sorted(
        candidate_pool, key=lambda x: x.get("stargazers_count", 0), reverse=True
    )
    cap = config.COMMIT_ACTIVITY_MAX_REPOS
    if len(pool_sorted) > cap:
        log.info("候选池 %d > 上限 %d，按 star 截断", len(pool_sorted), cap)
        pool_sorted = pool_sorted[:cap]

    todo = [it for it in pool_sorted if it.get("full_name") not in results_map]
    log.info(
        "==== commit 活跃度采集：%d 候选（跳过已采 %d）====",
        len(todo), len(results_map),
    )

    fetched = 0
    for item in todo:
        full = item.get("full_name", "")
        if "/" not in full:
            continue
        owner, _, repo = full.partition("/")
        count, src = get_commit_count_7d(client, owner, repo)
        active = (
            count is not None
            and count >= config.COMMIT_ACTIVITY_THRESHOLD
        )
        results_map[full] = {
            "full_name": full,
            "commit_count_7d": count,
            "commit_source": src,
            "is_active": active,
        }
        item["commit_count_7d"] = count
        item["commit_source"] = src
        item["is_active"] = active
        fetched += 1
        if fetched % 50 == 0:
            log.info("  commit 活跃度进度：%d / %d", fetched, len(todo))

    # 对断点续采的项目，把已有结果回写到内存 candidate_pool（保证 merged 一致）
    for item in pool_sorted:
        full = item.get("full_name", "")
        r = results_map.get(full)
        if r and "commit_count_7d" not in item:
            item["commit_count_7d"] = r.get("commit_count_7d")
            item["commit_source"] = r.get("commit_source")
            item["is_active"] = r.get("is_active")

    active_count = sum(1 for v in results_map.values() if v.get("is_active"))
    summary = {
        "snapshot_date": config.TODAY_HUMAN,
        "candidate_count": len(pool_sorted),
        "capped": len(candidate_pool) > cap,
        "fetched_this_run": fetched,
        "total_tracked": len(results_map),
        "active_count": active_count,
        "threshold": config.COMMIT_ACTIVITY_THRESHOLD,
        "by_full_name": results_map,
    }
    storage.save_meta("commit_activity", summary, date)
    # 关键：把 commit 字段回写到 merged/all_projects.json（上面只改了内存对象，需落盘）
    # pool_sorted 内的 item 与 candidate_pool 内是同一对象引用，故 candidate_pool 已被改；
    # 保存完整 candidate_pool 即可（被 cap 截断未采的项目字段仍为缺失，符合预期）。
    storage.save_merged(candidate_pool, date)
    log.info(
        "commit 活跃度完成：追踪 %d，活跃(🔥) %d（阈值>=%d）（已回写 merged）",
        len(results_map), active_count, config.COMMIT_ACTIVITY_THRESHOLD,
    )
    return summary
