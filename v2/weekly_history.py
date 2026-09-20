"""周报历史索引 —— 跨期轮换（活跃榜排他 / 解读冷却）的跨期状态存储。

为什么需要独立索引：快照出窗后以 snapshot_YYYYMMDD.zip 永久归档（2026-09-20 起，
不再删除），但 zip 内的定榜结果 weekly/meta/sections.json 不再直接可读；轮换规则
需要「上期上榜名单 / 上期解读名单」随手可用，故仍落一个随周报一起入库的
追加式索引 reports/weekly_history.json。

文件格式（每期一条，按日期升序，同日重跑覆盖）：
  {"entries": [
     {"date": "20260907", "issue_no": 5,
      "sections": {"国外数据库": {"active": [{"full_name": "...", "growth": 267}, ...],
                                  "focus": {"full_name": "...", "growth": 267}}},
                  ...}}
  ]}

历史缺失时从磁盘残留的 sections.json 自举（每期号取最后一次定榜；8 月多次试跑
属同期迭代，去重后仅保留最新一次）。自举结果与发布版可能有小出入（旧期中间产物
未全部留档），只影响远期冷却深度，不影响 K=1 的相邻期排他。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

import config
import storage

log = logging.getLogger(__name__)

_FIELD = "entries"


def history_file() -> str:
    return os.path.join(config.HERE, "reports", "weekly_history.json")


# ============================================================
# 读写
# ============================================================
def _read_entries() -> list[dict[str, Any]]:
    path = history_file()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("历史索引读取失败（按空处理）：%s %s", path, e)
        return []
    entries = data.get(_FIELD) if isinstance(data, dict) else None
    return [e for e in (entries or []) if isinstance(e, dict) and e.get("date")]


def _write_entries(entries: list[dict[str, Any]]) -> None:
    path = history_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entries.sort(key=lambda e: str(e.get("date", "")))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({_FIELD: entries}, f, ensure_ascii=False, indent=2)


def load_history(exclude_dates: set[str] | None = None) -> list[dict[str, Any]]:
    """读历史索引；文件不存在时从磁盘快照自举并落盘。

    exclude_dates：自举时跳过的快照日期（正在重算的当期不能进自己的冷却基准）。
    已有索引文件则直接使用（不再自举，避免旧中间产物反复回灌）。
    """
    entries = _read_entries()
    if entries:
        return entries
    entries = _bootstrap(exclude_dates or set())
    _write_entries(entries)
    log.info("历史索引自举完成：%d 期（%s）", len(entries), history_file())
    return entries


def save_entry(entry: dict[str, Any]) -> None:
    """按 date upsert 一期记录并保持升序落盘（渲染成功后调用）。"""
    date = str(entry.get("date", ""))
    entries = [e for e in _read_entries() if str(e.get("date", "")) != date]
    entries.append(entry)
    _write_entries(entries)


# ============================================================
# 查询（冷却基准）
# ============================================================
def recent_entries(
    history: list[dict[str, Any]],
    before_date: str,
    k: int,
) -> list[dict[str, Any]]:
    """date < before_date 的最近 k 期（升序返回；k<=0 返回空）。"""
    if k <= 0:
        return []
    prior = [e for e in history if str(e.get("date", "")) < str(before_date)]
    return prior[-k:]


def cooldown_map(
    history: list[dict[str, Any]],
    before_date: str,
    k: int,
    field: str,
) -> dict[str, dict[str, Any]]:
    """最近 k 期某字段（active / focus）出现过的 full_name -> 最近一次记录。

    记录含 growth（上次上榜/被解读当期的净增），供爆发豁免比较。升序遍历、
    后写覆盖，保证拿到的是最近一期的数值。
    """
    out: dict[str, dict[str, Any]] = {}
    for entry in recent_entries(history, before_date, k):
        for sec in (entry.get("sections") or {}).values():
            items = (sec or {}).get(field) or []
            if isinstance(items, dict):
                items = [items]
            for it in items:
                fn = str((it or {}).get("full_name") or "")
                if fn:
                    out[fn] = it
    return out


# ============================================================
# 条目构造 / 自举
# ============================================================
def entry_from_sections(date: str, sections_data: dict[str, Any]) -> dict[str, Any]:
    """从定榜结果（finalized sections.json）构造一条历史记录。"""
    secs: dict[str, Any] = {}
    for sec in sections_data.get("sections") or []:
        active = [
            {"full_name": r.get("full_name", ""), "growth": r.get("growth")}
            for r in (sec.get("active") or [])
        ]
        focus = sec.get("focus") or {}
        secs[sec.get("key", "")] = {
            "active": active,
            "focus": (
                {"full_name": focus.get("full_name", ""), "growth": focus.get("growth")}
                if focus.get("full_name") else None
            ),
        }
    return {"date": date, "issue_no": issue_no(date), "sections": secs}


def issue_no(date: str) -> int:
    """期号：距 config.FIRST_ISSUE_DATE 的满周数 + 1（与 run_weekly._issue_no 同口径）。"""
    try:
        d0 = datetime.strptime(config.FIRST_ISSUE_DATE, "%Y%m%d").date()
        d1 = datetime.strptime(date, "%Y%m%d").date()
    except ValueError:
        return 0
    return max(0, (d1 - d0).days // 7 + 1)


def _bootstrap(exclude_dates: set[str]) -> list[dict[str, Any]]:
    """扫描磁盘快照的 sections.json，按期号去重（每期取最后一次定榜）。"""
    best: dict[int, dict[str, Any]] = {}
    for d in storage.list_snapshot_dates():
        if d in exclude_dates:
            continue
        data = storage.load_weekly_meta("sections", d)
        if not (isinstance(data, dict) and data.get("finalized") and data.get("sections")):
            continue
        entry = entry_from_sections(d, data)
        no = entry["issue_no"]
        if no <= 0:
            continue
        cur = best.get(no)
        if cur is None or str(cur["date"]) < d:
            best[no] = entry
    return [best[no] for no in sorted(best)]
