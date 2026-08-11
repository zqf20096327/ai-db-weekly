"""第 1 步：探测 16 topic 规模。

目的：每个 topic 跑一次 base 查询拿 total_count，判断量级，决定采法。
调用数：16 次（每 topic 1 次，per_page=1）
依据：采集策略清单「第一步：探测阶段」+ SOP 4.5 ②
"""

from __future__ import annotations

import logging
from typing import Any

import config
import storage
from github_client import GitHubClient

log = logging.getLogger(__name__)


def probe_topic(client: GitHubClient, topic: str) -> dict[str, Any]:
    """对单个 topic 跑 per_page=1 base 查询，返回 {topic, total_count, tier}。"""
    q = f"topic:{topic}"
    data = client.search_repos(q, per_page=1)
    total = data.get("total_count", 0)
    tier = config.classify_tier(total)
    log.info("探测 %-12s total=%-8d tier=%s", topic, total, tier)
    return {
        "topic": topic,
        "total_count": total,
        "tier": tier,
        "query": q,
    }


def probe_all_topics(
    client: GitHubClient,
    topics: list[str] | None = None,
    date: str | None = None,
) -> dict[str, list[dict[str, Any]] | dict[str, dict[str, Any]]]:
    """探测全部 topic，落盘到 meta/probe_results.json。

    返回 {"results": [...], "by_topic": {topic: {...}}}。
    """
    topics = topics or config.TOPICS
    log.info("==== 探测阶段：%d 个 topic ====", len(topics))
    results = [probe_topic(client, t) for t in topics]

    out = {
        "snapshot_date": config.TODAY_HUMAN,
        "count": len(results),
        "results": results,
        "by_topic": {r["topic"]: r for r in results},
    }
    storage.save_meta("probe_results", out, date)
    log.info(
        "探测完成：%d topic。巨型/中型=%d, 小型=%d, 微型=%d, 空=%d",
        len(results),
        sum(1 for r in results if r["tier"] == "big"),
        sum(1 for r in results if r["tier"] == "small"),
        sum(1 for r in results if r["tier"] == "micro"),
        sum(1 for r in results if r["tier"] == "empty"),
    )
    return out


def load_probe_results(date: str | None = None) -> dict[str, Any] | None:
    """读取已落盘的探测结果（断点续采用）。"""
    return storage.load_meta("probe_results", date)
