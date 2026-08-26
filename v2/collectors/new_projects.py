"""第 5 步：新生项目采集（30 天窗）。

目的：专门支撑 ②新生项目榜（30 天内创建 + star≥3 + 内容相关性过滤）
查询：GET /search/repositories?q=topic:{topic}+created:>{30天前}+stars:>=3
后置过滤（客户端，不额外调 API）：
  ① 工程语言过滤
  ② 黑名单过滤（教程/作业/镜像/撞名）
  ③ 内容相关性二次过滤（关键，挡伪相关）
  ④ fork 默认剔除
  ⑤ 同作者批量建库只取 1 个
依据：采集策略清单「第五步」+ SOP ②新生项目 / 6.x 新生专用过滤
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import config
import filters
import storage
from github_client import GitHubClient, QuerySyntaxError

log = logging.getLogger(__name__)


def _cutoff_date(days: int = config.NEW_PROJECT_DAYS) -> str:
    """30 天前的日期（GitHub created:> 用 YYYY-MM-DD）。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.strftime("%Y-%m-%d")


def collect_new_projects_topic(
    client: GitHubClient, topic: str, *, resume: bool = True, date: str | None = None
) -> list[dict[str, Any]]:
    """采单个 topic 的 30 天内新生项目，落盘到 new_projects/{topic}.json。"""
    if resume:
        existing = storage.load_new_projects(topic, date)
        if existing:
            log.info("[%s] 新生项目当日已采（断点续采），%d 项目", topic, len(existing))
            return existing

    cutoff = _cutoff_date()
    q = (
        f"topic:{topic} created:>{cutoff} "
        f"stars:>={config.STAR_MIN_NEW}"
    )
    log.info("---- 新生项目 [%s] created:>%s stars:>=%d ----",
             topic, cutoff, config.STAR_MIN_NEW)
    try:
        result = client.fetch_all_pages(q)
    except QuerySyntaxError as e:
        log.error("[%s] 新生项目查询语法错误: %s", topic, e)
        items_raw: list[dict[str, Any]] = []
    else:
        items_raw = result["items"]

    # 标准化
    normalized = [
        storage.normalize_repo(raw, source_topic=topic, source="new")
        for raw in items_raw
    ]

    # 四层过滤（filters.filter_new_projects 已封装）
    filtered = filters.filter_new_projects(normalized)

    # 双档标注（SOP ②双档展示分流，本次仅打标，不拆文件）
    _tag_tier(filtered)

    storage.save_new_projects(topic, filtered, date)
    log.info(
        "[%s] 新生项目：原始 %d → 过滤后 %d（已落盘）",
        topic, len(normalized), len(filtered),
    )
    return filtered


def _tag_tier(items: list[dict[str, Any]]) -> None:
    """给新生项目打双档标签（原地）。

    🆕 新星榜：star 3-30（先露脸）
    🌟 潜力榜：star>=30 + 近 30 天有 push（已发酵）
    判定 push 活跃用 pushed_at（SOP ②：潜力榜用 pushed_at，避免 commit 字段依赖断裂）
    """
    cutoff = _cutoff_date()
    for item in items:
        star = item.get("stargazers_count", 0) or 0
        pushed = item.get("pushed_at")
        recent_push = bool(pushed) and pushed >= cutoff
        if star >= 30 and recent_push:
            item["new_tier"] = "potential"   # 🌟 潜力榜
        elif 3 <= star < 30:
            item["new_tier"] = "rising"      # 🆕 新星榜
        else:
            # star>=30 但无近期 push，仍归潜力（已发酵但不活跃）
            item["new_tier"] = "potential" if star >= 30 else "rising"


def collect_all_new_projects(
    client: GitHubClient,
    topics: list[str] | None = None,
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, int]:
    """采全部 topic 的新生项目，返回 {topic: count}。"""
    topics = topics or config.TOPICS
    log.info("==== 新生项目采集：%d topic ====", len(topics))
    counts: dict[str, int] = {}
    for t in topics:
        try:
            items = collect_new_projects_topic(client, t, resume=resume, date=date)
            counts[t] = len(items)
        except Exception as e:  # noqa: BLE001
            log.error("[%s] 新生项目采集失败: %s", t, e)
            counts[t] = 0
    total = sum(counts.values())
    log.info("新生项目采集完成：合计 %d 项目", total)
    return counts
