"""第 4.5 步：Org 全量扫描（补 topic 搜索盲区）。

目的：实测发现多个内核 repo 的 topics 为空（mysql-server、openGauss-server），
     topic 搜索完全搜不到。必须扫描官方 org 下全部 public repo 来补采。
方式：GET /orgs/{org}/repos?type=public&per_page=100（Core API，不占 Search 限流）
依据：采集策略清单「第四步半」+ SOP 5.2 / 数据源6

实测证据：
  mysql/mysql-server topics=[] → topic 搜索搜不到
  opengauss-mirror/openGauss-server topics=[] → topic 搜索搜不到
  polardb/PolarDB-for-PostgreSQL topics 含 database+postgresql 但无 polardb
    → topic:polardb 搜不到，且互斥 -topic:database 会误杀
  → 这些都靠 org 扫描兜底
"""

from __future__ import annotations

import logging
from typing import Any

import config
import filters
import storage
from github_client import GitHubClient

log = logging.getLogger(__name__)


def collect_org(
    client: GitHubClient, org: str, *, resume: bool = True, date: str | None = None
) -> list[dict[str, Any]]:
    """扫描单个 org 下全部 public repo，落盘到 orgs/{org}.json。"""
    if resume and storage.org_exists(org, date):
        existing = storage.load_org(org, date)
        if existing is not None:
            log.info("[%s] 当日已扫描（断点续采），%d repo", org, len(existing))
            return existing

    log.info("---- 扫描 org [%s] ----", org)
    raw_repos = client.fetch_all_org_repos(org)
    items = [
        storage.normalize_repo(raw, source_topic=None, source="org")
        for raw in raw_repos
    ]
    # org 扫描会带回该 org 全部 public repo（含无关的），做轻量过滤：
    #   - 剔除 fork（白名单例外由白名单负责，org 这层按通用规则）
    #   - 剔除 archived
    #   - 剔除明显黑名单（docs/site/blog 等）
    # 注意：不做 star 阈值（org 内 repo 本来就少，如 mysql org 24 个）
    items = [it for it in items if filters.pass_gate(it)]
    items = [it for it in items if not filters.is_blacklisted(it)]
    filters.annotate_categories(items)

    storage.save_org(org, items, date)
    log.info("[%s] 扫描完成：%d repo（已落盘）", org, len(items))
    return items


def collect_all_orgs(
    client: GitHubClient,
    orgs: list[str] | None = None,
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, int]:
    """扫描全部 org，返回 {org: count}。"""
    orgs = orgs or config.ORG_SCAN_LIST
    log.info("==== org 扫描：%d 个 ====", len(orgs))
    counts: dict[str, int] = {}
    for org in orgs:
        try:
            items = collect_org(client, org, resume=resume, date=date)
            counts[org] = len(items)
        except Exception as e:  # noqa: BLE001 —— org 扫描失败不应中断整体
            log.error("[%s] 扫描失败: %s", org, e)
            counts[org] = 0
    total = sum(counts.values())
    log.info("org 扫描完成：合计 %d repo", total)
    return counts
