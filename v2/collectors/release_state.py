"""M5 富集采集器 A：Release 维护信号（状态版，非周报"版本速递"用途）。

对目标 repo 集拉 GET /repos/{o}/{r}/releases，产出**当前状态**（最新版本、
距今天数、90 天发版数），写入快照 meta/release_state.json，供 site_export
聚合成档案页记录字段（ver / verd / n90）。

与旧 collectors/releases.py 的区别：
  - 旧版服务周报栏目⑥版本速递（近 7 天事件，白名单+上涨榜头部 ≤200）；
  - 本版服务资产页信任字段（全量 watched 断点续采，覆盖式状态，非事件）。

断点续采：已写入 by_repo 的 repo 跳过；--no-resume 全量重采（周度刷新用）。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import config
import storage
from github_client import GitHubClient, GitHubError, NotFoundError

log = logging.getLogger(__name__)


def release_state(raws: list[dict[str, Any]], today: datetime) -> dict[str, Any]:
    """releases 原始列表 → 维护信号状态。

    - draft 一律忽略；最新正式版优先于预发布版（都取：ver=最新正式，pre 顺手记）
    - days = 距采集日天数；n90 = 近 90 天发布次数（发版节奏）
    """
    rels = [r for r in raws if not r.get("draft")]
    if not rels:
        return {"none": True}

    latest = rels[0]  # API 默认按 published_at 倒序
    stable = next((r for r in rels if not r.get("prerelease")), latest)

    pub = (stable.get("published_at") or "")[:10]
    days = None
    if pub:
        try:
            dt = datetime.strptime(pub, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days = max(0, (today - dt).days)
        except ValueError:
            pass

    cutoff = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    n90 = sum(1 for r in rels if (r.get("published_at") or "")[:10] >= cutoff)

    return {
        "ver": stable.get("tag_name") or "",
        "pub": pub,
        "days": days,
        "n90": n90,
        "pre": bool(latest.get("prerelease")) and latest is not stable,
    }


def _load_cached(name: str, date: str | None, resume: bool) -> tuple[dict[str, Any], str]:
    """读已采缓存；条目无 ts 时用文件级 date 回填（旧数据兼容）。"""
    if not resume:
        return {}, ""
    prev = storage.load_meta(name, date)
    if not isinstance(prev, dict):
        return {}, ""
    by_repo = prev.get("by_repo") or {}
    fdate = (prev.get("date") or "").replace("-", "")
    for v in by_repo.values():
        if isinstance(v, dict) and not v.get("ts"):
            v["ts"] = fdate
    return by_repo, fdate


def _todo_list(
    targets: list[dict[str, Any]], by_repo: dict[str, Any],
    refresh_days: int, cap: int,
) -> list[dict[str, Any]]:
    """增量待采：未采过的优先（star 序），再补超过 refresh_days 未刷新的旧条目。"""
    cutoff = (
        (datetime.now(timezone.utc) - timedelta(days=refresh_days)).strftime("%Y%m%d")
        if refresh_days > 0 else "")
    fresh_missing = [t for t in targets if t.get("full_name") not in by_repo]
    stale = []
    if cutoff:
        stale = [t for t in targets
                 if t.get("full_name") in by_repo
                 and str(by_repo[t["full_name"]].get("ts") or "") <= cutoff]
    return (fresh_missing + stale)[:cap]


def collect_release_state(
    client: GitHubClient,
    targets: list[dict[str, Any]],
    *,
    resume: bool = True,
    date: str | None = None,
    cap: int = config.ENRICH_MAX_REPOS,
    refresh_days: int = 0,
) -> dict[str, Any]:
    """对目标 repo 集采集 release 状态，落盘快照 meta/release_state.json。

    增量滚动：未采过的优先；refresh_days>0 时，超过 N 天未刷新的旧条目重采
    （ver/verd 等时效字段的保鲜机制，稳态 ≈ watched/refresh_days 个/天）。
    """
    today = datetime.now(timezone.utc)
    today_s = today.strftime("%Y%m%d")
    existing, _ = _load_cached("release_state", date, resume)

    todo = _todo_list(targets, existing, refresh_days, cap)
    log.info("==== release 状态采集：目标 %d（缓存 %d，本次采 %d，refresh=%d 天）====",
             len(targets), len(existing), len(todo), refresh_days)

    by_repo = dict(existing)
    fetched = 0
    for item in todo:
        full = item.get("full_name", "")
        owner, _, repo = full.partition("/")
        if not repo:
            continue
        try:
            raws = client.list_releases(owner, repo, per_page=config.ENRICH_RELEASE_PER_PAGE)
            st = release_state(raws, today)
            st["ts"] = today_s
            by_repo[full] = st
        except NotFoundError:
            by_repo[full] = {"none": True, "ts": today_s}
        except GitHubError as e:
            log.debug("release 状态失败 %s: %s", full, e)
            continue  # 失败不写缓存，下次续采重试

        fetched += 1
        if fetched % 50 == 0:
            log.info("  release 进度：%d / %d", fetched, len(todo))
        if fetched % config.ENRICH_SAVE_EVERY == 0:
            _save(by_repo, date, fetched)

    _save(by_repo, date, fetched)
    n_ver = sum(1 for v in by_repo.values() if v and not v.get("none"))
    log.info("release 状态完成：累计 %d repo（有版本 %d，无 release %d）",
             len(by_repo), n_ver, len(by_repo) - n_ver)
    return {"by_repo": by_repo, "fetched": fetched}


def _save(by_repo: dict[str, Any], date: str | None, fetched: int) -> None:
    storage.save_meta("release_state", {
        "date": config.TODAY_HUMAN,
        "count": len(by_repo),
        "fetched_this_run": fetched,
        "by_repo": by_repo,
    }, date)
