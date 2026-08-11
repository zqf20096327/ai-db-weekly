"""第 2-3 步：topic 采集（分级策略的核心）。

分级（采集策略清单 第二/三步）：
  巨型/中型 (big, total>1000)：
    四层组合 = 互斥去重(仅四大库) + star≥10 + star三档 + star10-99按created日期拆
  小型 (small, 100<total<=1000)：直接 base 全采 + 分页
  微型 (micro, 0<total<=100)：直接 base 全采，一次取完
  空 (empty, total==0)：记录跳过

关键点：
  - 互斥仅限 BIG_FOUR（database/mysql/postgresql/oracle），用减号语法 -topic:xxx（不用 NOT）
  - 国产库 topic 不互斥（量小直接全采，且打上游标签会被误杀）
  - mariadb/sqlserver 不互斥，但量较大需按 star 档位拆
  - 动态拆分：每段 total_count>1000 继续按 created 日期细分，直到每段 <= 1000
"""

from __future__ import annotations

import logging
from typing import Any

import config
import filters
import storage
from github_client import GitHubClient, NotFoundError, QuerySyntaxError

log = logging.getLogger(__name__)


# ============================================================
# 查询构造
# ============================================================
def _base_query(topic: str) -> str:
    return f"topic:{topic}"


def _exclusive_query(topic: str) -> str:
    """四大库互斥查询（仅 BIG_FOUR 用）。

    database 互斥 = topic:database -topic:mysql -topic:postgresql -topic:oracle
    国产库 topic 不调用此函数。
    """
    excl = config.MUTUAL_EXCLUDE.get(topic, "")
    return f"{_base_query(topic)} {excl}".strip()


# ============================================================
# 通用：对一条查询跑全分页并标准化落盘片段
# ============================================================
def _collect_query(
    client: GitHubClient,
    q: str,
    *,
    source_topic: str,
    source: str = "topic",
) -> list[dict[str, Any]]:
    """对一条查询跑 fetch_all_pages，返回标准化后的项目列表。"""
    result = client.fetch_all_pages(q)
    items = result["items"]
    normalized = [
        storage.normalize_repo(raw, source_topic=source_topic, source=source)
        for raw in items
    ]
    if result["truncated"]:
        log.warning(
            "查询触达 1000 上限（truncated），需拆分: %s | total=%d fetched=%d",
            q, result["total_count"], result["fetched"],
        )
    log.debug(
        "查询完成 fetched=%-5d total=%-8d | %s",
        result["fetched"], result["total_count"], q,
    )
    return normalized


# ============================================================
# 巨型/中型：四层组合
# ============================================================
# star 三档（采集策略清单 第二步 第③层）
_STAR_BANDS = [
    "stars:>=1000",
    "stars:100..999",
    "stars:10..99",
]

# star10-99 按 created 日期拆的档位（第④层，仅 star10-99 档需要）
# 动态：今年/去年/前年/更早；若某段仍 >1000 再按半年细分
def _created_bands() -> list[str]:
    """生成 created 日期拆分档位（按当前年份动态）。

    GitHub 语法：created:>=YYYY-MM-DD（操作符紧贴，无空格）。
    """
    import datetime as _dt
    now = _dt.datetime.now(_dt.timezone.utc)
    y = now.year
    return [
        f"created:>={y}-01-01",                        # 今年
        f"created:{y-1}-01-01..{y-1}-12-31",           # 去年
        f"created:{y-2}-01-01..{y-2}-12-31",           # 前年
        f"created:<={y-3}-12-31",                      # 更早
    ]


def _created_bands_fine(year: int) -> list[str]:
    """对单一年份按半年细分（当某年仍 >1000 时调用）。"""
    return [
        f"created:{year}-01-01..{year}-06-30",
        f"created:{year}-07-01..{year}-12-31",
    ]


def _split_le_band(le_date: str) -> list[str]:
    """把 created:<=YYYY-12-31 拆成更细的年份档（当该段 >1000 时调用）。

    如 le_date="2023-12-31" → [2023全年, 2022全年, 2021全年, <=2020-12-31]。
    返回的档位供 _try_band 递归处理（最后一段仍是 <=，可能再触发拆分）。
    """
    import datetime as _dt
    try:
        year = int(le_date[:4])
    except ValueError:
        return []
    # 往前拆 3 年 + 一个更早的 <= 档（递归兜底）
    bands: list[str] = []
    for y in range(year, year - 3, -1):
        bands.append(f"created:{y}-01-01..{y}-12-31")
    bands.append(f"created:<={year - 4}-12-31")
    return bands


def _probe_count(client: GitHubClient, q: str) -> int:
    """轻量探总数（per_page=1）。"""
    return client.search_repos(q, per_page=1).get("total_count", 0)


def _collect_and_flush(
    client: GitHubClient,
    q: str,
    *,
    topic: str,
    source_topic: str,
    date: str | None,
    accumulated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """跑一条查询 → 标准化 → 过滤(fork/黑名单) → 标注分类 → 增量落盘。

    实现 SOP 4.5 ⑥「每次查询结果立即写入文件（防中断丢数据）」：
    每条子查询完成后立即调 storage.append_topic 落盘，即使巨型 topic
    中途崩溃也保留已采片段。返回累积后的完整列表。
    """
    items = _collect_query(client, q, source_topic=source_topic)
    # 子查询粒度过滤（fork/黑名单），落盘的就是已过滤的
    items = [it for it in items if filters.pass_gate(it)]
    items = [it for it in items if not filters.is_blacklisted(it)]
    filters.annotate_categories(items)
    accumulated.extend(items)
    storage.append_topic(topic, items, date)  # 立即落盘
    return accumulated


def _split_star10_99(
    client: GitHubClient,
    base_q: str,
    *,
    topic: str,
    source_topic: str,
    date: str | None,
    accumulated: list[dict[str, Any]],
) -> None:
    """对 star10-99 档按 created 日期动态拆分，直到每段 <= 1000。

    每段查完立即通过 _collect_and_flush 落盘（防中断）。
    base_q 已含互斥(如适用)，本函数追加 stars:10..99。
    """
    star_seg = "stars:10..99"

    def _try_band(band: str, depth: int = 0) -> None:
        # band 形如 "created:>=2025-01-01" / "created:2024-01-01..2024-12-31" / "created:<=2023-12-31"
        q = f"{base_q} {star_seg} {band}".strip()
        try:
            total = _probe_count(client, q)
        except QuerySyntaxError as e:
            log.error("created 拆分查询语法错误，跳过: %s | %s", q, e)
            return
        if total == 0:
            return
        if total <= config.SEARCH_MAX_RESULTS:
            _collect_and_flush(
                client, q, topic=topic, source_topic=source_topic,
                date=date, accumulated=accumulated,
            )
            return
        # 仍 > 1000：按 band 格式细分
        band_str = band.replace("created:", "")
        if depth >= 6:  # 递归深度保护（避免无限拆分）
            log.warning("递归深度达上限，接受截断: %s total=%d", q, total)
            _collect_and_flush(
                client, q, topic=topic, source_topic=source_topic,
                date=date, accumulated=accumulated,
            )
            return
        if ".." in band_str:
            # 区间格式：取起始年按半年细分
            try:
                year = int(band_str[:4])
                for fb in _created_bands_fine(year):
                    _try_band(fb, depth + 1)
                return
            except ValueError:
                pass
        if band_str.startswith("<="):
            # <= 格式：按年份往前拆（递归处理最后的 <= 档）
            for sb in _split_le_band(band_str[2:]):
                _try_band(sb, depth + 1)
            return
        # >= 单边格式无法细分，直接采（会 truncated）
        log.warning("无法进一步拆分（单边格式），接受截断: %s total=%d", q, total)
        _collect_and_flush(
            client, q, topic=topic, source_topic=source_topic,
            date=date, accumulated=accumulated,
        )

    for band in _created_bands():
        _try_band(band)


def collect_big_topic(
    client: GitHubClient, topic: str, date: str | None = None
) -> list[dict[str, Any]]:
    """巨型/中型 topic 四层组合采集。

    - BIG_FOUR（database/mysql/postgresql/oracle）：互斥
    - mariadb/sqlserver：不互斥（base + star档位 + 日期拆）

    落盘策略（SOP 4.5 ⑥）：每条子查询完成立即增量落盘，防中断丢数据。
    若该 topic 当日已有数据（resume），先清空再采，避免残留。
    """
    is_big_four = topic in config.BIG_FOUR
    base = _exclusive_query(topic) if is_big_four else _base_query(topic)
    log.info(
        "---- 采集 [%s] (big) %s ----",
        topic, "互斥" if is_big_four else "非互斥",
    )

    # resume 场景下重采：先清空当日 topic 文件，避免旧数据残留
    storage.save_topic(topic, [], date)
    accumulated: list[dict[str, Any]] = []

    # star≥100 档（合并 100-999 + ≥1000，基本可一次采完）
    for band in ["stars:>=1000", "stars:100..999"]:
        q = f"{base} {band}".strip()
        try:
            total = _probe_count(client, q)
        except QuerySyntaxError as e:
            log.error("查询语法错误，跳过 %s: %s", q, e)
            continue
        if total == 0:
            continue
        if total <= config.SEARCH_MAX_RESULTS:
            _collect_and_flush(
                client, q, topic=topic, source_topic=topic,
                date=date, accumulated=accumulated,
            )
        else:
            # ≥100 档也可能超（罕见），按 created 细分
            log.info("[%s] %s total=%d >1000，按 created 拆分", topic, band, total)
            _split_with_band(
                client, base, band, topic=topic, source_topic=topic,
                date=date, accumulated=accumulated,
            )

    # star10-99 档（按 created 日期动态拆）
    _split_star10_99(
        client, base, topic=topic, source_topic=topic,
        date=date, accumulated=accumulated,
    )

    log.info("[%s] 采集完成：%d 项目（每段已即时落盘）", topic, len(accumulated))
    return accumulated


def _split_with_band(
    client: GitHubClient, base: str, band: str, *,
    topic: str, source_topic: str, date: str | None,
    accumulated: list[dict[str, Any]],
) -> None:
    """对 star≥100 档若仍 >1000，按 created 拆分（每段即时落盘）。"""
    def _try_band(band_c: str, depth: int = 0) -> None:
        q = f"{base} {band} {band_c}".strip()
        total = _probe_count(client, q)
        if total == 0:
            return
        if total <= config.SEARCH_MAX_RESULTS:
            _collect_and_flush(
                client, q, topic=topic, source_topic=source_topic,
                date=date, accumulated=accumulated,
            )
            return
        band_str = band_c.replace("created:", "")
        if depth >= 6:
            log.warning("递归深度达上限，接受截断: %s total=%d", q, total)
            _collect_and_flush(
                client, q, topic=topic, source_topic=source_topic,
                date=date, accumulated=accumulated,
            )
            return
        if ".." in band_str:
            try:
                year = int(band_str[:4])
                for fb in _created_bands_fine(year):
                    _try_band(fb, depth + 1)
                return
            except ValueError:
                pass
        if band_str.startswith("<="):
            for sb in _split_le_band(band_str[2:]):
                _try_band(sb, depth + 1)
            return
        log.warning("无法进一步拆分（单边格式），接受截断: %s total=%d", q, total)
        _collect_and_flush(
            client, q, topic=topic, source_topic=source_topic,
            date=date, accumulated=accumulated,
        )

    for band_c in _created_bands():
        _try_band(band_c)


# ============================================================
# 小型 / 微型：直接 base 全采
# ============================================================
def collect_small_topic(
    client: GitHubClient, topic: str, date: str | None = None
) -> list[dict[str, Any]]:
    """小型/微型 topic：直接 base 全采 + 分页，不互斥不拆 star。"""
    log.info("---- 采集 [%s] (small/micro) base 全采 ----", topic)
    q = _base_query(topic)
    try:
        items = _collect_query(client, q, source_topic=topic)
    except QuerySyntaxError as e:
        log.error("查询语法错误: %s | %s", q, e)
        items = []

    items = [it for it in items if filters.pass_gate(it)]
    items = [it for it in items if not filters.is_blacklisted(it)]
    filters.annotate_categories(items)

    storage.save_topic(topic, items, date)
    log.info("[%s] 采集完成：%d 项目（已落盘）", topic, len(items))
    return items


# ============================================================
# 分派入口
# ============================================================
def collect_topic(
    client: GitHubClient,
    topic: str,
    tier: str | None = None,
    *,
    resume: bool = True,
    date: str | None = None,
) -> list[dict[str, Any]]:
    """按 tier 分派到对应采集函数。

    tier 可由 probe 结果传入；不传则先探测。
    resume=True 时，若当日已采集过该 topic 则跳过（断点续采）。
    """
    if resume and storage.topic_exists(topic, date):
        existing = storage.load_topic(topic, date)
        if existing is not None:
            log.info("[%s] 当日已采集（断点续采跳过），%d 项目", topic, len(existing))
            return existing

    if tier is None:
        total = _probe_count(client, _base_query(topic))
        tier = config.classify_tier(total)

    if tier == "empty":
        log.info("[%s] total=0，GitHub 无项目，记录跳过", topic)
        storage.save_topic(topic, [], date)
        return []
    if tier in ("small", "micro"):
        return collect_small_topic(client, topic, date)
    return collect_big_topic(client, topic, date)


def collect_all_topics(
    client: GitHubClient,
    topics: list[str] | None = None,
    probe_results: dict[str, Any] | None = None,
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, int]:
    """采集全部 topic，返回 {topic: count}。"""
    topics = topics or config.TOPICS
    by_topic = (probe_results or {}).get("by_topic", {}) if probe_results else {}
    log.info("==== topic 采集：%d 个 ====", len(topics))
    counts: dict[str, int] = {}
    for t in topics:
        tier = by_topic.get(t, {}).get("tier") if by_topic else None
        try:
            items = collect_topic(client, t, tier, resume=resume, date=date)
            counts[t] = len(items)
        except (QuerySyntaxError, NotFoundError) as e:
            log.error("[%s] 采集失败（跳过）: %s", t, e)
            counts[t] = 0
    total = sum(counts.values())
    log.info("topic 采集完成：合计 %d 项目", total)
    return counts
