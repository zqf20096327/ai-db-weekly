"""数据源 3：Release 事件（SOP 4.3「每周一次」，周报生产前采）。

用途：⑥版本速递（拆为 6a 工具版本 / 6b AI 板块版本）
endpoint：GET /repos/{owner}/{repo}/releases?per_page=N（Core API）
⚠️ Releases API 不支持 since：默认按 published_at 倒序返回全部，
   必须客户端按 published_at > N 天前 过滤"本周发布"（SOP 4.2 数据源3）。
范围：只对候选池按 star 头部（白名单 + 上涨榜前 N）拉，不全员（SOP 4.3/4.4）
断点续采：读 weekly/meta/releases.json 跳过已采 repo
依据：SOP 4.2 数据源3 + 4.3 + ⑥版本速递
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import config
import storage
from github_client import GitHubClient, GitHubError, NotFoundError

log = logging.getLogger(__name__)


def _cutoff_iso(days: int = config.RELEASE_LOOKBACK_DAYS) -> str:
    """N 天前的 ISO 日期（published_at 与之字符串比较即可，均为 UTC Z 格式）。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_release(raw: dict[str, Any], repo_full_name: str) -> dict[str, Any]:
    """保留 SOP 4.2 数据源3 字段最小集。"""
    return {
        "repo_full_name": repo_full_name,
        "tag_name": raw.get("tag_name"),
        "name": raw.get("name"),
        "published_at": raw.get("published_at"),
        "body": raw.get("body"),
        "html_url": raw.get("html_url"),
        "prerelease": bool(raw.get("prerelease")),
        "draft": bool(raw.get("draft")),
        # 周报发布前可由 render 层结合项目 category(由采集层 classify 标注)拆 6a/6b
    }


def collect_repo_releases(
    client: GitHubClient, full_name: str, cutoff: str
) -> list[dict[str, Any]]:
    """采单个 repo 的近 N 天 release，返回标准化列表。

    - 过滤 draft:true（SOP 4.2：草稿不展示）
    - 客户端按 published_at > cutoff 过滤"本周发布"
    - 无 release / 404 返回空列表
    """
    owner, _, repo = full_name.partition("/")
    try:
        raws = client.list_releases(owner, repo, per_page=config.RELEASE_PER_PAGE)
    except NotFoundError:
        return []
    except GitHubError as e:
        log.debug("release 采集失败 %s: %s", full_name, e)
        return []

    out: list[dict[str, Any]] = []
    for raw in raws:
        if raw.get("draft"):
            continue
        pub = raw.get("published_at") or ""
        if pub and pub < cutoff:
            # Releases 默认按 published_at 倒序，遇到早于 cutoff 的即可停止
            break
        out.append(_normalize_release(raw, full_name))
    return out


def collect_releases(
    client: GitHubClient,
    candidate_pool: list[dict[str, Any]],
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, Any]:
    """对候选池头部项目采集本周 release，落盘到 weekly/meta/releases.json。

    范围控制（SOP 4.3/4.4 按需采）：候选池按 star 降序取头部 RELEASE_MAX_REPOS。
    断点续采：读 weekly/meta/releases.json，已采 repo 跳过（key 为 repo_full_name）。
    返回汇总（含 by_repo 映射 + 本周全部 release 列表）。
    """
    cutoff = _cutoff_iso()

    # 断点续采
    existing = storage.load_weekly_meta("releases", date) if resume else None
    by_repo: dict[str, list[dict[str, Any]]] = {}
    if isinstance(existing, dict) and "by_repo" in existing:
        by_repo = existing.get("by_repo", {}) or {}

    pool_sorted = sorted(
        candidate_pool, key=lambda x: x.get("stargazers_count", 0), reverse=True
    )
    cap = config.RELEASE_MAX_REPOS
    if len(pool_sorted) > cap:
        log.info("release 采集：候选池 %d > 上限 %d，按 star 截断", len(pool_sorted), cap)
        pool_sorted = pool_sorted[:cap]

    todo = [it for it in pool_sorted if it.get("full_name") not in by_repo]
    log.info(
        "==== release 采集：%d 候选（跳过已采 %d）| 近 %d 天 ====",
        len(todo), len(by_repo), config.RELEASE_LOOKBACK_DAYS,
    )

    fetched = 0
    week_releases: list[dict[str, Any]] = []
    # 先并入已有结果里的本周 release
    for rl in by_repo.values():
        week_releases.extend(rl)

    for item in todo:
        full = item.get("full_name", "")
        if "/" not in full:
            continue
        rels = collect_repo_releases(client, full, cutoff)
        by_repo[full] = rels
        week_releases.extend(rels)
        fetched += 1
        if rels:
            log.info(
                "  release ✓ %-40s 近%d天 %d 条（最新 %s）",
                full, config.RELEASE_LOOKBACK_DAYS, len(rels),
                rels[0].get("tag_name") if rels else "",
            )
        if fetched % 50 == 0:
            log.info("  release 进度：%d / %d", fetched, len(todo))

    summary = {
        "snapshot_date": config.TODAY_HUMAN,
        "lookback_days": config.RELEASE_LOOKBACK_DAYS,
        "cutoff": cutoff,
        "candidate_count": len(pool_sorted),
        "capped": len(candidate_pool) > cap,
        "fetched_this_run": fetched,
        "total_tracked": len(by_repo),
        "week_release_count": len(week_releases),
        "releases": week_releases,   # 扁平列表，render 直接用
        "by_repo": by_repo,           # 溯源用
    }
    storage.save_weekly_meta("releases", summary, date)
    log.info(
        "release 完成：追踪 %d repo，本周发版 %d 条（已落盘 weekly/meta/releases.json）",
        len(by_repo), len(week_releases),
    )
    return summary
