"""第 4 步：白名单内核项目采集。

目的：数据库内核 repo 往往不打 topic 标签（如 mysql-server、openGauss-server），
     topic 搜索会漏。必须用白名单单独补采。
方式：GET /repos/{owner}/{repo}（Core API，5000/小时，不占 Search 限流）
去重：与 topic 采集结果合并时，按 full_name 去重，白名单优先（权威源）
依据：采集策略清单「第四步」+ SOP 5.1
"""

from __future__ import annotations

import logging
from typing import Any

import config
import filters
import storage
from github_client import GitHubClient, NotFoundError

log = logging.getLogger(__name__)


def collect_whitelist_repo(client: GitHubClient, full_name: str) -> dict[str, Any] | None:
    """采单个白名单 repo。失败（404 等）返回 None。"""
    try:
        owner, _, repo = full_name.partition("/")
        raw = client.get_repo(owner, repo)
    except NotFoundError:
        log.warning("白名单 repo 不存在/已删除，跳过: %s", full_name)
        return None
    return storage.normalize_repo(
        raw, source_topic=None, source="whitelist"
    )


def collect_whitelist(
    client: GitHubClient,
    repos: list[str] | None = None,
    *,
    resume: bool = True,
    date: str | None = None,
) -> list[dict[str, Any]]:
    """采集全部白名单内核 repo，落盘到 whitelist/whitelist.json。

    resume=True 时，若当日已采集则直接读回（白名单稳定，无需每日重采验证）。
    """
    if resume:
        existing = storage.load_whitelist(date)
        if existing:
            log.info("白名单当日已采集（断点续采），%d 项目", len(existing))
            return existing

    repos = repos or config.WHITELIST_REPOS
    log.info("==== 白名单采集：%d 个 repo ====", len(repos))
    items: list[dict[str, Any]] = []
    for full in repos:
        item = collect_whitelist_repo(client, full)
        if item:
            items.append(item)
            log.info("白名单 ✓ %-40s star=%s", full, item.get("stargazers_count"))
        else:
            log.warning("白名单 ✗ %s", full)

    # 标注分类（与其他源一致）
    filters.annotate_categories(items)
    storage.save_whitelist(items, date)
    log.info("白名单采集完成：%d / %d", len(items), len(repos))
    return items
