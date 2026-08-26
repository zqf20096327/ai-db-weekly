"""存储层 —— 快照读写 / 字段标准化 / 去重合并 / 断点续采。

设计原则：
  - 每次 query 结果立即落盘（SOP 全局规范①：防中断丢数据）
  - 文件按 topic / org 命名（SOP 4.5 ⑦ + 4.6 存储结构）
  - 字段集标准化（SOP 4.7 字段最小集 + snapshot_date + source_topic）
  - 按 full_name 去重，白名单优先（采集策略清单 第四步去重逻辑）
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Iterable

import config

log = logging.getLogger(__name__)


# ============================================================
# 路径辅助
# ============================================================
def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def topics_dir(date: str | None = None) -> str:
    p = os.path.join(config.snapshot_dir(date), "topics")
    _ensure_dir(p)
    return p


def whitelist_dir(date: str | None = None) -> str:
    p = os.path.join(config.snapshot_dir(date), "whitelist")
    _ensure_dir(p)
    return p


def orgs_dir(date: str | None = None) -> str:
    p = os.path.join(config.snapshot_dir(date), "orgs")
    _ensure_dir(p)
    return p


def new_projects_dir(date: str | None = None) -> str:
    p = os.path.join(config.snapshot_dir(date), "new_projects")
    _ensure_dir(p)
    return p


def merged_dir(date: str | None = None) -> str:
    p = os.path.join(config.snapshot_dir(date), "merged")
    _ensure_dir(p)
    return p


def meta_dir(date: str | None = None) -> str:
    p = os.path.join(config.snapshot_dir(date), "meta")
    _ensure_dir(p)
    return p


def topic_file(topic: str, date: str | None = None) -> str:
    return os.path.join(topics_dir(date), f"{topic}.json")


def org_file(org: str, date: str | None = None) -> str:
    return os.path.join(orgs_dir(date), f"{org}.json")


def merged_file(date: str | None = None) -> str:
    return os.path.join(merged_dir(date), "all_projects.json")


def weekly_dir(date: str | None = None) -> str:
    """周报生产根目录：data/snapshot_YYYYMMDD/weekly/

    存放周报最终产物 + 中间计算数据。与快照同目录，diff 时本周/基准周数据
    都在手边（SOP 4.6 存储结构延伸）。
    """
    p = os.path.join(config.snapshot_dir(date), "weekly")
    _ensure_dir(p)
    return p


def weekly_meta_dir(date: str | None = None) -> str:
    """周报中间数据目录：weekly/meta/（diff/scoring/attribution/releases/license）"""
    p = os.path.join(weekly_dir(date), "meta")
    _ensure_dir(p)
    return p


def report_file(date: str | None = None) -> str:
    """最终周报 Markdown 路径：weekly/report.md"""
    return os.path.join(weekly_dir(date), "report.md")


def toolkit_file(date: str | None = None) -> str:
    """工具合辑周报 Markdown 路径：weekly/toolkit.md"""
    return os.path.join(weekly_dir(date), "toolkit.md")


def save_weekly_meta(name: str, data: Any, date: str | None = None) -> None:
    """写周报中间数据到 weekly/meta/{name}.json。"""
    _write_json(os.path.join(weekly_meta_dir(date), f"{name}.json"), data)


def load_weekly_meta(name: str, date: str | None = None) -> Any:
    return _read_json(os.path.join(weekly_meta_dir(date), f"{name}.json"))


# ============================================================
# 历史快照定位（SOP 4.1 时间序列对比 —— 基准快照查找）
# ============================================================
def list_snapshot_dates() -> list[str]:
    """列出 data/ 下所有 snapshot_YYYYMMDD 目录日期（升序）。

    用于查找 N 天前的基准快照做 diff（SOP 4.1：动态信号必须靠时间序列对比）。
    """
    if not os.path.isdir(config.DATA_DIR):
        return []
    dates: list[str] = []
    for fn in os.listdir(config.DATA_DIR):
        full = os.path.join(config.DATA_DIR, fn)
        if not os.path.isdir(full):
            continue
        if fn.startswith("snapshot_") and len(fn) == 8 + len("snapshot_"):
            date = fn[len("snapshot_"):]
            if date.isdigit():
                dates.append(date)
    return sorted(dates)


def find_prev_snapshot_date(
    current_date: str, *, target_days_back: int = 7
) -> str | None:
    """找 current_date 之前、最接近 target_days_back 的已有快照日期。

    SOP 4.1：7 天对比 = diff 两个目录的对应文件。理想是恰好 7 天前的快照，
    实际不一定每天都有；退而求其次取最接近 7 天前（且早于 current_date）的。
    返回 None = 没有可用的基准快照（首期，SOP 4.8 关键说明②）。
    """
    dates = list_snapshot_dates()
    candidates = [d for d in dates if d < current_date]
    if not candidates:
        return None  # 首期：current_date 是最早快照，无基准
    # 优先找恰好 target_days_back 的；否则取最早的可用基准（跨度越长越保守）
    import datetime as _dt
    try:
        cur = _dt.datetime.strptime(current_date, "%Y%m%d")
    except ValueError:
        return candidates[0]
    target = cur - _dt.timedelta(days=target_days_back)
    # 按"距 target 的天数"排序，取最近且早于当前的
    def _dist(d: str) -> int:
        try:
            dd = _dt.datetime.strptime(d, "%Y%m%d")
        except ValueError:
            return 10**9
        return abs((dd - target).days)
    candidates.sort(key=_dist)
    return candidates[0]


def load_snapshot_pool(date: str) -> list[dict[str, Any]]:
    """读某历史快照的候选池（merged/all_projects.json）。

    diff 基准快照用。文件不存在返回空列表（首期场景）。
    """
    data = _read_json(merged_file(date))
    return data if isinstance(data, list) else []


# ============================================================
# 字段标准化（SOP 4.7 字段最小集）
# ============================================================
# 保留这些字段，其余丢弃（减少磁盘占用 + 统一格式）
_REPO_FIELDS = [
    "full_name", "description", "html_url",
    "stargazers_count", "forks_count", "open_issues_count", "watchers_count",
    "language",
    "license",
    "fork", "archived",
    "created_at", "pushed_at", "updated_at",
    "default_branch",
    "topics",
    "homepage",
]


def normalize_repo(
    raw: dict[str, Any],
    *,
    source_topic: str | None = None,
    source: str = "topic",  # topic / whitelist / org / new
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    """把 GitHub 原始 repo JSON 标准化为 SOP 4.7 字段集。

    加自填字段：
      - snapshot_date：采集日期（对比用）
      - source_topic：哪个 topic 搜到的（溯源用，可为 None）
      - source：来源类型（topic/whitelist/org/new）
    """
    out: dict[str, Any] = {k: raw.get(k) for k in _REPO_FIELDS}
    # license 可能是 None（无 license）或 dict
    if out.get("license") and isinstance(out["license"], dict):
        # 只留 spdx_id / name，去掉冗余 url
        lic = out["license"]
        out["license"] = {
            "spdx_id": lic.get("spdx_id"),
            "name": lic.get("name"),
        }
    # topics 可能为 None
    if out.get("topics") is None:
        out["topics"] = []
    out["snapshot_date"] = snapshot_date or config.TODAY_HUMAN
    out["source_topic"] = source_topic
    out["source"] = source
    return out


# ============================================================
# 写盘（每次查询结果立即落盘 —— 防中断）
# ============================================================
def _write_json(path: str, data: Any) -> None:
    """原子写：先写 .tmp 再 rename，避免写到一半被读到。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_topic(topic: str, items: list[dict[str, Any]], date: str | None = None) -> None:
    _write_json(topic_file(topic, date), items)


def append_topic(
    topic: str, new_items: list[dict[str, Any]], date: str | None = None
) -> list[dict[str, Any]]:
    """增量落盘：读取已有 topic 文件，合并 new_items（按 full_name 去重），写回。

    实现 SOP 4.5 ⑥「每次查询结果立即写入文件，不要等全部跑完再写（防中断丢数据）」。
    巨型 topic 的多档拆分查询每完成一段就调用此函数，即使中途崩溃也不丢已采数据。
    返回合并后的完整列表（供调用方继续累积）。
    """
    path = topic_file(topic, date)
    existing = _read_json(path)
    merged_map: dict[str, dict[str, Any]] = {}
    if isinstance(existing, list):
        for it in existing:
            full = it.get("full_name")
            if full:
                merged_map[full] = it
    for it in new_items:
        full = it.get("full_name")
        if full:
            merged_map[full] = it  # 新数据覆盖旧的（同 full_name）
    merged = list(merged_map.values())
    _write_json(path, merged)
    return merged


def save_whitelist(items: list[dict[str, Any]], date: str | None = None) -> None:
    _write_json(os.path.join(whitelist_dir(date), "whitelist.json"), items)


def save_org(org: str, items: list[dict[str, Any]], date: str | None = None) -> None:
    _write_json(org_file(org, date), items)


def save_new_projects(
    topic: str, items: list[dict[str, Any]], date: str | None = None
) -> None:
    _write_json(os.path.join(new_projects_dir(date), f"{topic}.json"), items)


def save_merged(items: list[dict[str, Any]], date: str | None = None) -> None:
    _write_json(merged_file(date), items)


def save_meta(name: str, data: Any, date: str | None = None) -> None:
    _write_json(os.path.join(meta_dir(date), f"{name}.json"), data)


# ============================================================
# 读盘（断点续采 —— 已采的 topic 跳过）
# ============================================================
def _read_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        log.warning("读取失败（当作未采集）: %s: %s", path, e)
        return None


def topic_exists(topic: str, date: str | None = None) -> bool:
    return os.path.exists(topic_file(topic, date))


def org_exists(org: str, date: str | None = None) -> bool:
    return os.path.exists(org_file(org, date))


def load_topic(topic: str, date: str | None = None) -> list[dict[str, Any]] | None:
    data = _read_json(topic_file(topic, date))
    return data if isinstance(data, list) else None


def load_whitelist(date: str | None = None) -> list[dict[str, Any]]:
    data = _read_json(os.path.join(whitelist_dir(date), "whitelist.json"))
    return data if isinstance(data, list) else []


def load_org(org: str, date: str | None = None) -> list[dict[str, Any]]:
    data = _read_json(org_file(org, date))
    return data if isinstance(data, list) else []


def load_new_projects(topic: str, date: str | None = None) -> list[dict[str, Any]]:
    data = _read_json(os.path.join(new_projects_dir(date), f"{topic}.json"))
    return data if isinstance(data, list) else []


def load_all_new_projects(date: str | None = None) -> list[dict[str, Any]]:
    """读全部 topic 的新生项目（合并 16 个 topic 文件）。

    跨 topic 去重：同一项目可能被多个 topic 命中（如 apitap 同时打了 postgresql+mysql），
    按 full_name 去重，保留 star 最高的那条。
    """
    d = new_projects_dir(date)
    merged: dict[str, dict[str, Any]] = {}
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            data = _read_json(os.path.join(d, fn))
            if isinstance(data, list):
                for it in data:
                    full = it.get("full_name")
                    if not full:
                        continue
                    existing = merged.get(full)
                    if existing is None or _star(it) > _star(existing):
                        merged[full] = it
    return list(merged.values())


def _star(item: dict[str, Any]) -> int:
    """star 数（去重比较用）。"""
    try:
        return int(item.get("stargazers_count") or 0)
    except (TypeError, ValueError):
        return 0


def load_meta(name: str, date: str | None = None) -> Any:
    return _read_json(os.path.join(meta_dir(date), f"{name}.json"))


def load_all_topics(date: str | None = None) -> list[dict[str, Any]]:
    d = topics_dir(date)
    out: list[dict[str, Any]] = []
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            data = _read_json(os.path.join(d, fn))
            if isinstance(data, list):
                out.extend(data)
    return out


def load_all_orgs(date: str | None = None) -> list[dict[str, Any]]:
    d = orgs_dir(date)
    out: list[dict[str, Any]] = []
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            data = _read_json(os.path.join(d, fn))
            if isinstance(data, list):
                out.extend(data)
    return out


# ============================================================
# 去重合并（采集策略清单 第四步去重 + 全局规范去重）
# ============================================================
def merge_dedupe(*sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """合并多源，按 full_name 去重。

    优先级：whitelist > org > topic > new。
    同一 full_name 出现多次时，保留优先级最高的那条（含其 source 字段，便于溯源）。
    合并各源的 source_topic（一个项目可能被多个 topic 采到，收集所有 topic）。
    """
    priority = {"whitelist": 0, "org": 1, "topic": 2, "new": 3}
    merged: dict[str, dict[str, Any]] = {}

    for source in sources:
        for item in source:
            full = item.get("full_name")
            if not full:
                continue
            existing = merged.get(full)
            if existing is None:
                merged[full] = dict(item)
                continue
            # 已存在：按优先级决定谁主
            cur_pri = priority.get(str(existing.get("source")), 9)
            new_pri = priority.get(str(item.get("source")), 9)
            if new_pri < cur_pri:
                # 新来的优先级更高 → 它当主体，但保留已有的 source_topic 合集
                base = dict(item)
                base["source_topics"] = _union_topics(existing, item)
                merged[full] = base
            else:
                # 已有的优先级更高 → 保留它，但把新来的 source_topic 并入
                merged[full]["source_topics"] = _union_topics(existing, item)

    return list(merged.values())


def _union_topics(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """合并两个 item 的 source_topic（去 None 去重）。"""
    topics: set[str] = set()
    for item in (a, b):
        t = item.get("source_topic")
        if t:
            topics.add(t)
        # 已合并过的 source_topics 列表
        for st in item.get("source_topics", []) or []:
            if st:
                topics.add(st)
    return sorted(topics)


def write_run_summary(summary: dict[str, Any], date: str | None = None) -> None:
    """写本次运行汇总到 meta/run_summary.json。"""
    save_meta("run_summary", summary, date)
