"""M5 富集采集器 B：GHSA 安全通告（项目自身披露的漏洞）。

对目标 repo 集拉 GET /repos/{o}/{r}/security-advisories（GitHub 官方安全通告库，
项目自己披露的 CVE），产出快照 meta/security.json，供 site_export 聚合成
档案页记录字段（secn 披露条数 / secw 最高severity / secl 最近披露日）。

边界说明（诚实口径，前端照此展示）：
  - 只覆盖**项目自身披露**的漏洞通告；依赖组件的漏洞（Dependabot）是私有
    数据，GitHub-only 边界下不可采，页面标注「项目自身披露口径」；
  - 404 / 空列表 = 已扫描且无通告（写 {"n": 0}，与「未扫描」区分）；
  - withdrawn（撤回）的通告不计入。
"""

from __future__ import annotations

import logging
from typing import Any

import config
import storage
from github_client import GitHubClient, GitHubError, NotFoundError

log = logging.getLogger(__name__)

_SEV_RANK = {"critical": 4, "high": 3, "moderate": 2, "medium": 2, "low": 1}


def advisory_state(raws: list[dict[str, Any]]) -> dict[str, Any]:
    """advisories 原始列表 → 安全状态摘要。

    口径说明：API 的 first_patched_version 普遍缺失（实测连官网明确给出修复
    版本的通告也返回 null），「未修复数」不可靠，故不产出该断言；用
    条数 / 最高严重级 / 最近披露日期，由前端如实展示。
    """
    live = [a for a in raws if not a.get("withdrawn_at")]
    if not live:
        return {"n": 0}

    worst = ""
    worst_rank = 0
    last = ""
    ids: list[str] = []
    for a in live:
        sev = (a.get("severity") or "unknown").lower()
        rank = _SEV_RANK.get(sev, 0)
        if rank > worst_rank:
            worst, worst_rank = sev, rank

        pub = (a.get("published_at") or "")[:10]
        if pub > last:
            last = pub
        if len(ids) < 8:
            cve = (a.get("cve_id") or "")[4:] if a.get("cve_id") else ""
            ids.append(f"{a.get('ghsa_id') or '?'}({cve},{sev})" if cve
                       else f"{a.get('ghsa_id') or '?'}({sev})")

    return {"n": len(live), "worst": worst, "last": last, "ids": ids}


def collect_security(
    client: GitHubClient,
    targets: list[dict[str, Any]],
    *,
    resume: bool = True,
    date: str | None = None,
    cap: int = config.ENRICH_MAX_REPOS,
) -> dict[str, Any]:
    """对目标 repo 集采集安全通告状态，落盘快照 meta/security.json。"""
    existing: dict[str, Any] = {}
    if resume:
        prev = storage.load_meta("security", date)
        if isinstance(prev, dict):
            existing = prev.get("by_repo") or {}

    todo = [t for t in targets if t.get("full_name") not in existing][:cap]
    log.info("==== GHSA 安全采集：目标 %d（缓存 %d，本次采 %d）====",
             len(targets), len(existing), len(todo))

    by_repo = dict(existing)
    fetched = 0
    for item in todo:
        full = item.get("full_name", "")
        owner, _, repo = full.partition("/")
        if not repo:
            continue
        try:
            raws = client.list_advisories(owner, repo, per_page=config.ENRICH_ADVISORY_PER_PAGE)
            by_repo[full] = advisory_state(raws)
        except NotFoundError:
            by_repo[full] = {"n": 0}   # 无通告 = 干净（与未扫描区分）
        except GitHubError as e:
            log.debug("advisories 失败 %s: %s", full, e)
            continue

        fetched += 1
        if fetched % 50 == 0:
            log.info("  GHSA 进度：%d / %d", fetched, len(todo))
        if fetched % config.ENRICH_SAVE_EVERY == 0:
            _save(by_repo, date, fetched)

    _save(by_repo, date, fetched)
    n_hit = sum(1 for v in by_repo.values() if v and v.get("n"))
    log.info("GHSA 完成：累计 %d repo（有披露 %d）", len(by_repo), n_hit)
    return {"by_repo": by_repo, "fetched": fetched}


def _save(by_repo: dict[str, Any], date: str | None, fetched: int) -> None:
    storage.save_meta("security", {
        "date": config.TODAY_HUMAN,
        "count": len(by_repo),
        "fetched_this_run": fetched,
        "by_repo": by_repo,
    }, date)
