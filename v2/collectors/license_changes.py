"""数据源 5：License 变更检测（SOP 4.3「每周一次」，周报生产前采）。

用途：⑨License 雷达（变更才详报，常态周只一行"本期无变更"）
endpoint：GET /repos/{owner}/{repo}/commits?path=LICENSE&since={N天前}
        （Core API，不占 Search 限流）
逻辑：不下载 LICENSE 全文，只检测"本周 LICENSE 文件是否动过"，
     动了才进雷达详报（SOP 4.2 数据源5 + ⑨只报字段+变更事件+选型提示）
红线：只报 license 字段 + 变更事件，不解读法律条款（SOP 7.1/7.3）
断点续采：读 weekly/meta/license_changes.json 跳过已采 repo
依据：SOP 4.2 数据源5 + 4.3 + ⑨License 雷达
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import config
import storage
from github_client import GitHubClient, GitHubError, NotFoundError

log = logging.getLogger(__name__)


def _cutoff_iso(days: int = config.LICENSE_LOOKBACK_DAYS) -> str:
    """N 天前的 ISO 时间戳（commits since 参数）。

    GitHub since 接受 ISO8601，返回 commit date >= since。
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_change(
    commit: dict[str, Any], repo_full_name: str
) -> dict[str, Any]:
    """从 commit 提取变更记录字段（SOP 4.2 数据源5：changed_at/changed_by/sha）。"""
    cinfo = commit.get("commit") or {}
    author = cinfo.get("author") or {}
    committer = cinfo.get("committer") or {}
    return {
        "repo_full_name": repo_full_name,
        "sha": commit.get("sha"),
        "changed_at": author.get("date") or committer.get("date"),
        "changed_by": (author.get("name") or committer.get("name")),
        "message": (cinfo.get("message") or "").splitlines()[0][:120]
        if cinfo.get("message") else "",
    }


def collect_repo_license_change(
    client: GitHubClient, full_name: str, cutoff: str
) -> list[dict[str, Any]]:
    """检单个 repo 本周 LICENSE 文件 commit。返回空 = 本周无变更。

    注：path=LICENSE 只匹配精确文件名 LICENSE，部分项目用 LICENSE.md/.txt，
    本检测以主流的 LICENSE 为主（SOP 未要求覆盖所有变体）。
    """
    owner, _, repo = full_name.partition("/")
    try:
        commits = client.list_commits(owner, repo, path="LICENSE", since=cutoff)
    except NotFoundError:
        return []
    except GitHubError as e:
        log.debug("license 变更检测失败 %s: %s", full_name, e)
        return []
    return [_normalize_change(c, full_name) for c in commits]


def collect_license_changes(
    client: GitHubClient,
    candidate_pool: list[dict[str, Any]],
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, Any]:
    """对候选池头部项目检测本周 LICENSE 变更，落盘到 weekly/meta/license_changes.json。

    范围控制（SOP 4.3/4.4 按需采）：候选池按 star 降序取头部 LICENSE_MAX_REPOS。
    断点续采：读 weekly/meta/license_changes.json，已采 repo 跳过。
    返回汇总（含变更列表 + by_repo 映射 + 各项目当前 license 字段快照）。
    """
    cutoff = _cutoff_iso()

    # 断点续采
    existing = storage.load_weekly_meta("license_changes", date) if resume else None
    by_repo: dict[str, list[dict[str, Any]]] = {}
    if isinstance(existing, dict) and "by_repo" in existing:
        by_repo = existing.get("by_repo", {}) or {}

    pool_sorted = sorted(
        candidate_pool, key=lambda x: x.get("stargazers_count", 0), reverse=True
    )
    cap = config.LICENSE_MAX_REPOS
    if len(pool_sorted) > cap:
        log.info("license 检测：候选池 %d > 上限 %d，按 star 截断", len(pool_sorted), cap)
        pool_sorted = pool_sorted[:cap]

    todo = [it for it in pool_sorted if it.get("full_name") not in by_repo]
    log.info(
        "==== license 变更检测：%d 候选（跳过已采 %d）| 近 %d 天 ====",
        len(todo), len(by_repo), config.LICENSE_LOOKBACK_DAYS,
    )

    fetched = 0
    for item in todo:
        full = item.get("full_name", "")
        if "/" not in full:
            continue
        changes = collect_repo_license_change(client, full, cutoff)
        by_repo[full] = changes
        fetched += 1
        if changes:
            log.info("  license 变更 ⚠ %s 近%d天 %d 次", full, config.LICENSE_LOOKBACK_DAYS, len(changes))
        if fetched % 50 == 0:
            log.info("  license 进度：%d / %d", fetched, len(todo))

    # 汇总：本周发生变更的项目列表（用于 ⑨雷达详报）
    changed = [
        {"repo_full_name": full, "changes": ch}
        for full, ch in by_repo.items() if ch
    ]
    # 当前 license 字段快照（候选池各项目的 license.spdx_id），供文末全景表用
    license_snapshot = {
        it.get("full_name", ""): _license_label(it)
        for it in pool_sorted if it.get("full_name")
    }

    summary = {
        "snapshot_date": config.TODAY_HUMAN,
        "lookback_days": config.LICENSE_LOOKBACK_DAYS,
        "cutoff": cutoff,
        "candidate_count": len(pool_sorted),
        "capped": len(candidate_pool) > cap,
        "fetched_this_run": fetched,
        "total_tracked": len(by_repo),
        "changed_count": len(changed),
        "changed": changed,
        "license_snapshot": license_snapshot,
        "by_repo": by_repo,
    }
    storage.save_weekly_meta("license_changes", summary, date)
    log.info(
        "license 检测完成：追踪 %d repo，本周变更 %d 个（已落盘 weekly/meta/license_changes.json）",
        len(by_repo), len(changed),
    )
    return summary


def _license_label(item: dict[str, Any]) -> str:
    """取项目当前 license 显示名（spdx_id 优先，缺则 NOASSERTION/None）。"""
    lic = item.get("license")
    if isinstance(lic, dict):
        return lic.get("spdx_id") or lic.get("name") or "NOASSERTION"
    return "NOASSERTION"
