"""GitHub API 客户端 —— 唯一与 GitHub 通信的层。

所有 collector 共享同一个 client，集中处理：
  - 认证（Bearer token，提限流到 Search 30/分 + Core 5000/小时）
  - 动态限流（读 X-RateLimit-Remaining，绝不固定 sleep）
  - 错误处理（403/422/404/5xx/超时，各自策略）
  - 分页（per_page=100，最多 10 页 = 1000 条硬上限）
  - 调用计数（Search / Core 分开统计，便于成本审计）

依据：SOP 4.5（标准结构 ①④⑤）+ 采集策略清单「全局规范：限流/错误」
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

import config

log = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"
REQUEST_TIMEOUT = 30  # 秒（采集策略清单：超时 30 秒重试 1 次）


class GitHubError(Exception):
    """GitHub 调用业务异常基类。"""


class QuerySyntaxError(GitHubError):
    """HTTP 422 —— 查询语法错误（如误用 NOT topic:，应改用减号 -topic:）。"""


class NotFoundError(GitHubError):
    """HTTP 404 —— repo 不存在/已删除，调用方应记录跳过。"""


@dataclass
class CallStats:
    """调用计数 —— 区分 Search / Core 配额，便于成本审计。"""
    search_calls: int = 0
    core_calls: int = 0
    # 限流等待统计（分钟，估算值）
    rate_wait_seconds: float = 0.0
    # 各 HTTP 错误码计数
    errors: dict[int, int] = field(default_factory=dict)

    def bump(self, kind: str) -> None:
        if kind == "search":
            self.search_calls += 1
        else:
            self.core_calls += 1

    def summary(self) -> dict[str, Any]:
        return {
            "search_calls": self.search_calls,
            "core_calls": self.core_calls,
            "total_calls": self.search_calls + self.core_calls,
            "rate_wait_minutes": round(self.rate_wait_seconds / 60, 1),
            "errors": dict(self.errors),
        }


class GitHubClient:
    """认证 + 动态限流 + 重试 + 分页。

    所有 collector 持有同一个实例，共享限流状态与计数。
    """

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os_getenv("GITHUB_TOKEN") or load_env_token()
        if not self.token:
            raise GitHubError(
                "GITHUB_TOKEN 未配置。请写入 .env（GITHUB_TOKEN=ghp_xxx）或设置环境变量。"
            )
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "db-weekly-collector/1.0",
        })
        self.stats = CallStats()

    # --------------------------------------------------------
    # 低层请求（统一处理限流 + 错误 + 重试）
    # --------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        kind: str,  # "search" | "core" —— 决定按哪个配额限流
        params: dict | None = None,
        allow_202: bool = False,  # stats/participation 首次返回 202 是合法的"还在算"
    ) -> requests.Response:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        max_retries = 3

        for attempt in range(max_retries + 1):
            self._wait_for_rate_limit(kind)
            try:
                resp = self.session.request(
                    method, url, params=params, timeout=REQUEST_TIMEOUT
                )
            except requests.Timeout:
                if attempt < 1:  # 超时只重试 1 次
                    log.warning("超时，重试 1 次: %s", url)
                    time.sleep(5)
                    continue
                raise GitHubError(f"请求超时（重试后仍失败）: {url}")
            except requests.RequestException as e:
                if attempt < max_retries:
                    backoff = 2 ** attempt
                    log.warning("网络错误，%ds 后重试: %s", backoff, e)
                    time.sleep(backoff)
                    continue
                raise GitHubError(f"网络错误（重试耗尽）: {e}")

            self.stats.bump(kind)

            # 202：participation 异步计算中（SOP 4.2 数据源4 警告）
            if resp.status_code == 202:
                if allow_202:
                    return resp
                # 非 participation 场景遇到 202 也视为"还在算"，交调用方处理
                return resp

            # 限流
            if resp.status_code == 403 and self._is_rate_limited(resp):
                self._sleep_until_reset(kind)
                continue  # 重试（不计入 max_retries 的"错误"，是预期内的等待）

            # 5xx：指数退避重试
            if 500 <= resp.status_code < 600:
                self.stats.errors[resp.status_code] = (
                    self.stats.errors.get(resp.status_code, 0) + 1
                )
                if attempt < max_retries:
                    backoff = 2 ** attempt * 5
                    log.warning(
                        "HTTP %d（GitHub 服务端），%ds 后重试: %s",
                        resp.status_code, backoff, url,
                    )
                    time.sleep(backoff)
                    continue
                raise GitHubError(f"HTTP {resp.status_code} 重试耗尽: {url}")

            # 4xx 业务错误（不重试）
            if resp.status_code == 422:
                self.stats.errors[422] = self.stats.errors.get(422, 0) + 1
                try:
                    msg = resp.json().get("message", "")
                except ValueError:
                    msg = resp.text[:200]
                raise QuerySyntaxError(f"422 查询语法错误: {msg} | url={url} params={params}")
            if resp.status_code == 404:
                self.stats.errors[404] = self.stats.errors.get(404, 0) + 1
                raise NotFoundError(f"404 不存在: {url}")
            if resp.status_code == 403:
                # 非限流的 403（如 token 权限不足）
                self.stats.errors[403] = self.stats.errors.get(403, 0) + 1
                raise GitHubError(f"403 禁止访问（非限流）: {url} body={resp.text[:200]}")

            if not resp.ok:
                self.stats.errors[resp.status_code] = (
                    self.stats.errors.get(resp.status_code, 0) + 1
                )
                raise GitHubError(
                    f"HTTP {resp.status_code}: {url} body={resp.text[:200]}"
                )

            return resp

        raise GitHubError(f"重试逻辑异常退出: {url}")

    # --------------------------------------------------------
    # 动态限流（SOP 4.5 ④ —— 核心，不固定 sleep）
    # --------------------------------------------------------
    def _wait_for_rate_limit(self, kind: str) -> None:
        """调用前先看上一次响应头的剩余配额。

        两套配额节流策略不同：
          - search（30/分钟，硬瓶颈）：必须卡 min_interval_sec（=2s ≈ 30/分），
            否则连续请求会迅速撞满 Search 限额。
          - core（5000/小时，充足）：跳过预防性 sleep。Core 配额远大于单次采集需求
            （commit 全量 ~4000 次仍 < 5000），且有 X-RateLimit-Remaining 动态兜底
            （剩余 ≤ safety_remaining 时 sleep 到 reset）。原来的固定 2s sleep 会让
            commit 阶段 4000 项白睡 ~133 分钟（GitHub 实际响应只占十几分钟）。
        """
        remaining = self._last_remaining.get(kind)
        # Core 配额：只在剩余不多时动态等待，否则立即发请求（不预防性 sleep）
        if kind == "core":
            if remaining is not None and remaining <= config.RATE_LIMIT["safety_remaining"]:
                self._sleep_until_reset(kind, quiet=True)
            return
        # Search 配额：按 min_interval_sec 节流，避免撞 30/分限额
        if remaining is None:
            # 首次调用或该配额无记录，按正常间隔走
            time.sleep(config.RATE_LIMIT["min_interval_sec"])
            return
        if remaining > config.RATE_LIMIT["safety_remaining"]:
            time.sleep(config.RATE_LIMIT["min_interval_sec"])
            return
        # 剩余不多 → sleep 到 reset（SOP：剩余 <= 5 则 sleep 到 X-RateLimit-Reset）
        self._sleep_until_reset(kind, quiet=True)

    def _sleep_until_reset(self, kind: str, quiet: bool = False) -> None:
        reset_ts = self._last_reset.get(kind)
        if reset_ts is None:
            # 没拿到 reset 头，保守等待 60s
            if not quiet:
                log.warning("未拿到 %s reset 头，保守等待 60s", kind)
            time.sleep(60)
            self.stats.rate_wait_seconds += 60
            return
        wait = int(reset_ts) - int(time.time()) + 2  # +2s 缓冲
        if wait <= 0:
            return
        log.info(
            "[%s] 配额剩余不足，等待 %ds 到重置（约 %.1f 分钟）",
            kind, wait, wait / 60,
        )
        time.sleep(wait)
        self.stats.rate_wait_seconds += wait

    def _is_rate_limited(self, resp: requests.Response) -> bool:
        """403 是否由限流引起（区分权限不足与限流）。"""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) == 0:
            return True
        # 兜底：看 body 提示
        try:
            body = resp.json()
            return "rate limit" in (body.get("message", "")).lower()
        except ValueError:
            return False

    # 实例状态：缓存最近一次响应的限流头（按 kind 分 Search/Core）
    _last_remaining: dict[str, int] = {}
    _last_reset: dict[str, int] = {}

    def _record_rate_headers(self, resp: requests.Response, kind: str) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        # 不同接口可能用不同的 resource 头（X-RateLimit-Resource），
        # 这里按调用方声明的 kind 归类，足够用
        if remaining is not None:
            try:
                self._last_remaining[kind] = int(remaining)
            except ValueError:
                pass
        if reset is not None:
            try:
                self._last_reset[kind] = int(reset)
            except ValueError:
                pass

    # --------------------------------------------------------
    # 高层 API：search_repos / get_repo / get_org_repos / search_commits / participation
    # --------------------------------------------------------
    def search_repos(
        self, q: str, *, per_page: int = config.PER_PAGE, page: int = 1,
        sort: str = "stars", order: str = "desc",
    ) -> dict[str, Any]:
        """单次 repo 搜索（单页）。返回含 total_count 的完整 JSON。

        调用方据此判断 total_count 是否 > 1000 需要拆分。
        """
        params = {
            "q": q, "per_page": per_page, "page": page,
            "sort": sort, "order": order,
        }
        resp = self._request("GET", "/search/repositories", kind="search", params=params)
        self._record_rate_headers(resp, "search")
        return resp.json()

    def fetch_all_pages(self, q: str, *, max_pages: int = config.MAX_PAGES) -> dict[str, Any]:
        """对一条 repo 搜索查询，自动翻页取全部。

        返回 {total_count, items, fetched, truncated}。
        truncated=True 表示触达 1000 条硬上限，调用方应触发拆分逻辑。
        """
        all_items: list[dict] = []
        total_count: int | None = None
        first = self.search_repos(q, page=1)
        total_count = first.get("total_count", 0)
        all_items.extend(first.get("items", []))

        pages_needed = min(max_pages, (total_count + config.PER_PAGE - 1) // config.PER_PAGE)
        for page in range(2, pages_needed + 1):
            r = self.search_repos(q, page=page)
            items = r.get("items", [])
            if not items:
                break
            all_items.extend(items)

        return {
            "total_count": total_count,
            "items": all_items,
            "fetched": len(all_items),
            "truncated": total_count > config.SEARCH_MAX_RESULTS,
        }

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """取单个 repo（Core API，5000/小时，不占 Search 限流）。"""
        resp = self._request("GET", f"/repos/{owner}/{repo}", kind="core")
        self._record_rate_headers(resp, "core")
        return resp.json()

    def get_readme(self, owner: str, repo: str) -> str:
        """取 repo 的 README 全文（Core API）。

        用 Accept: application/vnd.github.raw 直接拿原文，免 base64 解码。
        无 README（404）抛 NotFoundError，调用方捕获。
        """
        self._wait_for_rate_limit("core")
        url = f"{BASE_URL}/repos/{owner}/{repo}/readme"
        resp = self.session.get(
            url,
            headers={"Accept": "application/vnd.github.raw"},
            timeout=REQUEST_TIMEOUT,
        )
        self.stats.bump("core")
        self._record_rate_headers(resp, "core")
        if resp.status_code == 404:
            raise NotFoundError(f"README 不存在: {owner}/{repo}")
        if not resp.ok:
            raise GitHubError(f"get_readme HTTP {resp.status_code}: {owner}/{repo}")
        return resp.text

    def list_org_repos(self, org: str, *, page: int = 1,
                       per_page: int = 100) -> dict[str, Any]:
        """列出 org 下 public repo（Core API）。单页。"""
        params = {
            "type": "public", "sort": "stars", "direction": "desc",
            "per_page": per_page, "page": page,
        }
        resp = self._request("GET", f"/orgs/{org}/repos", kind="core", params=params)
        self._record_rate_headers(resp, "core")
        return resp.json()

    def fetch_all_org_repos(self, org: str) -> list[dict[str, Any]]:
        """翻页取 org 全部 public repo。"""
        all_items: list[dict] = []
        page = 1
        while True:
            items = self.list_org_repos(org, page=page)
            if not items:
                break
            all_items.extend(items)
            if len(items) < 100:
                break
            page += 1
        return all_items

    def search_commits_count(self, q: str) -> int:
        """search commits 拿 total_count（兜底算 commit 数）。

        注意：占用 Search 配额。
        """
        params = {"q": q, "per_page": 1}
        resp = self._request("GET", "/search/commits", kind="search", params=params)
        self._record_rate_headers(resp, "search")
        return resp.json().get("total_count", 0)

    def get_participation(self, owner: str, repo: str) -> dict[str, Any] | None:
        """stats/participation —— 52 周每日 commit 数。

        SOP 4.2 数据源4 警告：首次常返回 202（还在算，无 body）。
        本方法处理 202 轮询：allow_202=True 让 _request 返回 202 响应，
        由调用方（commit_activity）决定轮询或兜底。
        返回 None 表示该次调用处于 202 异步计算中。
        """
        resp = self._request(
            "GET", f"/repos/{owner}/{repo}/stats/participation",
            kind="core", allow_202=True,
        )
        self._record_rate_headers(resp, "core")
        if resp.status_code == 202:
            return None
        return resp.json()

    # --------------------------------------------------------
    # 数据源3 / 数据源5 —— release 与 license 变更（Core API）
    # --------------------------------------------------------
    def list_releases(
        self, owner: str, repo: str, *, per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """列某 repo 的 releases（SOP 4.2 数据源3，⑥版本速递原料）。

        ⚠️ Releases API 不支持 since（since 仅 Commits/Issues 参数），默认按
        published_at 倒序返回全部。调用方（releases collector）按 published_at
        客户端过滤近 N 天。per_page 默认 30（近 N 天的 release 量很小）。
        """
        params = {"per_page": per_page}
        resp = self._request(
            "GET", f"/repos/{owner}/{repo}/releases", kind="core", params=params,
        )
        self._record_rate_headers(resp, "core")
        data = resp.json()
        return data if isinstance(data, list) else []

    def list_commits(
        self, owner: str, repo: str, *,
        path: str | None = None, since: str | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """列某 repo 的 commits（SOP 4.2 数据源5，⑨License 雷达原料）。

        用于检测 LICENSE 文件本周是否动过：path=LICENSE&since={7天前}。
        返回空 = 本周无变更。走 Core API，不占 Search 限流。
        """
        params: dict[str, Any] = {"per_page": per_page}
        if path is not None:
            params["path"] = path
        if since is not None:
            params["since"] = since
        resp = self._request(
            "GET", f"/repos/{owner}/{repo}/commits", kind="core", params=params,
        )
        self._record_rate_headers(resp, "core")
        data = resp.json()
        return data if isinstance(data, list) else []


# ============================================================
# 环境加载（不依赖 python-dotenv，避免第三方依赖；只读 .env）
# ============================================================
def os_getenv(key: str) -> str | None:
    return __import__("os").environ.get(key)


def load_env_token() -> str | None:
    """从 .env 文件读 GITHUB_TOKEN（不覆盖已有环境变量）。"""
    import os
    if not os.path.exists(config.ENV_FILE):
        return None
    try:
        with open(config.ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k == "GITHUB_TOKEN":
                    # 不覆盖已有环境变量
                    if not os.environ.get("GITHUB_TOKEN"):
                        os.environ["GITHUB_TOKEN"] = v
                    return v
    except OSError as e:
        log.warning("读取 .env 失败: %s", e)
    return None
