"""README 采集（新 SOP 三板块周报的全部候选，每周 ~9-15 个）。

用途：周报 AI 解读（活跃榜+新锐每条 100 字解读、本周解读四维分析）—— AI 基于
      README 生成中文点评。
方式：GET /repos/{owner}/{repo}/readme（Core API，Accept: raw 直拿原文）
范围：只采传入的候选 repo 列表（三板块活跃榜+新锐+本周解读去重后，不采全量候选池）。
      契合 SOP 两阶段思想：阶段一先定候选清单，阶段二只对这些项目拉 README，省 API。
断点续采：读 weekly/meta/readmes.json 跳过已采 repo
依据：AI 解读信息来源补全（description 一句话不够，需 README 全文）
"""

from __future__ import annotations

import logging
from typing import Any

import config
import storage
from github_client import GitHubClient, GitHubError, NotFoundError

log = logging.getLogger(__name__)


def collect_repo_readme(client: GitHubClient, full_name: str) -> str | None:
    """采单个 repo 的 README 全文。无 README 或失败返回 None（不中断）。"""
    owner, _, repo = full_name.partition("/")
    if not owner or not repo:
        return None
    try:
        return client.get_readme(owner, repo)
    except NotFoundError:
        log.debug("README 不存在: %s", full_name)
        return None
    except GitHubError as e:
        log.debug("README 采集失败 %s: %s", full_name, e)
        return None


def collect_readmes(
    client: GitHubClient,
    repos: list[str],
    *,
    resume: bool = True,
    date: str | None = None,
) -> dict[str, str]:
    """对指定 repo 列表采集 README，落盘到 weekly/meta/readmes.json。

    只采传入的 repos（三板块周报候选，去重后约 9-15 个），不采全量候选池。
    断点续采：读已落盘结果，已采的 repo 跳过。
    返回 {full_name: readme_text} 映射（readme 为 None 的也记 key，表示已尝试）。
    """
    # 断点续采
    existing = storage.load_weekly_meta("readmes", date) if resume else None
    by_repo: dict[str, str | None] = {}
    if isinstance(existing, dict) and "by_repo" in existing:
        by_repo = existing.get("by_repo", {}) or {}

    todo = [fn for fn in repos if fn not in by_repo]
    log.info("==== README 采集：%d 候选（跳过已采 %d）====", len(todo), len(by_repo) - len(todo))

    for fn in todo:
        readme = collect_repo_readme(client, fn)
        by_repo[fn] = readme
        if readme:
            log.info("  README ✓ %-40s %d 字符", fn, len(readme))
        else:
            log.info("  README ✗ %s（无 README 或失败）", fn)

    storage.save_weekly_meta("readmes", {
        "snapshot_date": config.TODAY_HUMAN,
        "by_repo": by_repo,
        "readme_count": sum(1 for v in by_repo.values() if v),
    }, date)

    found = sum(1 for v in by_repo.values() if v)
    log.info("README 采集完成：%d / %d（已落盘 weekly/meta/readmes.json）", found, len(by_repo))

    # 返回时过滤掉 None（调用方只需要有 README 的）
    return {fn: text for fn, text in by_repo.items() if text}
