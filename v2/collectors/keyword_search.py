"""数据源7：关键词搜索采集（补"社区工具不打 topic"盲区）。

背景（2026-09-23 实测）：板块二国产库的社区生态工具（nacos-plus 292★、
db-migration 79★、OracleSync2MySQL 86★ 等）topics 全空，topic 搜索、
org 扫描、白名单三条路径都够不着；关键词全文搜索是唯一覆盖手段。

方式：search/repositories?q=<关键词> stars:>=10 fork:false（Search API）。
     关键词清单与选词依据见 config.KEYWORD_SEARCH_QUERIES 注释。

与 topic 采集的区别：不按 topic 分级拆分（star>=10 门槛后每个关键词
总量只有几十到几百，fetch_all_pages 一遍翻完即可）。

噪音防线（复用既有层，不新写）：
  - 撞名/课程/比赛 → filters.is_blacklisted（采集黑名单）
  - 归档/fork → filters.pass_gate
  - 混合多库工具的去留 → 周报期范围外排斥层（sections.is_out_of_scope）
"""

from __future__ import annotations

import logging
from typing import Any

import config
import filters
import storage
from github_client import GitHubClient, GitHubError

log = logging.getLogger(__name__)


def collect_keyword(
    client: GitHubClient, name: str, query: str,
    *, resume: bool = True, date: str | None = None,
) -> list[dict[str, Any]]:
    """按单条关键词查询采集，落盘到 keywords/{name}.json。"""
    if resume and storage.keyword_exists(name, date):
        existing = storage.load_keyword(name, date)
        if existing is not None:
            log.info("[keyword:%s] 当日已采集（断点续采），%d repo", name, len(existing))
            return existing

    log.info("---- 关键词采集 [%s]: %s ----", name, query)
    result = client.fetch_all_pages(query)
    items = [
        storage.normalize_repo(raw, source_topic=None, source="keyword")
        for raw in result.get("items", [])
    ]
    # 与 org 扫描同规格的轻过滤：剔 fork/archived（pass_gate）+ 黑名单词
    items = [it for it in items if filters.pass_gate(it)]
    items = [it for it in items if not filters.is_blacklisted(it)]
    filters.annotate_categories(items)

    storage.save_keyword(name, items, date)
    log.info(
        "[keyword:%s] 采集完成：%d repo（total=%d，已落盘）",
        name, len(items), result.get("total_count", 0),
    )
    return items


def collect_all_keywords(
    client: GitHubClient,
    queries: dict[str, str] | None = None,
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, int]:
    """跑全部关键词查询。单条失败不中断（记录后继续，断点续采可补）。"""
    queries = queries or config.KEYWORD_SEARCH_QUERIES
    counts: dict[str, int] = {}
    for name, query in queries.items():
        try:
            items = collect_keyword(client, name, query, resume=resume, date=date)
            counts[name] = len(items)
        except GitHubError as e:
            log.error("[keyword:%s] 采集失败（跳过，明日重采）: %s", name, e)
            counts[name] = -1
    log.info("关键词采集汇总：%d 条查询，命中 %d repo",
             len(queries), sum(v for v in counts.values() if v > 0))
    return counts
