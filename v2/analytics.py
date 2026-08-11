"""周报分析层 —— 对比计算 / 价值评分 / 信号分 / 榜单归属（纯函数）。

全部为纯函数（不调网络、不读写文件），便于单测。与 filters.py 同级。
依据：
  - SOP 4.1 时间序列对比（动态信号必须靠时间序列，不能靠一次查询）
  - SOP ④本周重点信号分计算
  - SOP 6 第3层价值评分卡（仅用于排序，不写进正文）
  - SOP 6.y 榜单归属分层漏斗（④②①⑧⑤ 五选一，防霸屏）
"""

from __future__ import annotations

import re
from typing import Any

import config


# ============================================================
# 7 天快照对比（SOP 4.1 —— 周报动态信号的技术地基）
# ============================================================
def diff_snapshots(
    today_pool: list[dict[str, Any]],
    prev_pool: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """对齐两个快照候选池，算 star 净增 / 新入榜 / 掉榜。

    返回:
      {
        first_period: bool,        # True=无基准（首期，SOP 4.8 关键说明②）
        star_deltas: {full_name: delta},   # star 净增（负=掉粉）
        new_entries:  [full_name, ...],    # 本周新冒出（基准里没有）
        dropped:      [full_name, ...],    # 本周掉出（基准有、本周没）
      }
    prev 为空 → first_period=True，动态列留空（SOP 4.8：首期只能报绝对值）。
    """
    if not prev_pool:
        return {
            "first_period": True,
            "star_deltas": {},
            "new_entries": [],
            "dropped": [],
        }

    prev_map = {_full(it): it for it in prev_pool if _full(it)}
    today_map = {_full(it): it for it in today_pool if _full(it)}

    star_deltas: dict[str, int] = {}
    new_entries: list[str] = []
    dropped: list[str] = []

    for full, item in today_map.items():
        today_star = _star(item)
        prev_item = prev_map.get(full)
        if prev_item is None:
            new_entries.append(full)
            star_deltas[full] = today_star  # 新入榜，"净增"即当前 star
        else:
            star_deltas[full] = today_star - _star(prev_item)

    for full in prev_map:
        if full not in today_map:
            dropped.append(full)

    return {
        "first_period": False,
        "star_deltas": star_deltas,
        "new_entries": new_entries,
        "dropped": dropped,
    }


def rising_list(
    diffs: dict[str, Any],
    pool_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """①快速上涨榜：按 star 净增降序，排除总榜前 N（只看腰部黑马）。

    SOP ①：7 日 star 净增排序，排除总榜前 5；负值不上榜。
    首期（first_period）→ 返回空列表，由 render 层标注"首期无基准"。
    """
    if diffs.get("first_period"):
        return []

    # 总榜前 N 的 full_name（按当前 star 降序）—— 排除它们
    top_full = sorted(
        pool_map.values(), key=lambda x: _star(x), reverse=True
    )[: config.RISING_EXCLUDE_TOPN]
    top_set = {_full(x) for x in top_full}

    rows: list[dict[str, Any]] = []
    for full, delta in diffs["star_deltas"].items():
        if delta <= 0:
            continue  # 负值不上榜（SOP ①）
        if full in top_set:
            continue  # 排除总榜前 N
        rows.append({"full_name": full, "star_delta": delta})
    rows.sort(key=lambda x: x["star_delta"], reverse=True)
    return rows[: config.RISING_TOPN]


# ============================================================
# 主版本号变更判定（SOP ④"重大版本 +40"）
# ============================================================
_TAG_MAJOR_RE = re.compile(r"v?(\d+)")


def _major(tag: str | None) -> int | None:
    """从 tag_name 取主版本号数字（如 v18.5.2 → 18；4.5 → 4）。失败返回 None。"""
    if not tag:
        return None
    m = _TAG_MAJOR_RE.match(str(tag).strip())
    return int(m.group(1)) if m else None


def detect_major_version_bump(
    releases: list[dict[str, Any]],
    by_repo_all_tags: dict[str, list[str]] | None = None,
) -> set[str]:
    """检测本周发版中发生主版本号变更的 repo（SOP ④ +40 触发条件）。

    releases: 本周 release 列表（collectors/releases 产出）。
    by_repo_all_tags: 可选，每个 repo 历史全部 tag（含本周前），
      用于比较"本周 tag 主版本" vs "上一个 tag 主版本"。
      若缺，则仅按"本周有发版"近似（保守不加分），避免误报。
    返回发生主版本号上升的 repo_full_name 集合。
    """
    bumped: set[str] = set()
    if not releases:
        return bumped
    if not by_repo_all_tags:
        # 无历史 tag 上下文，无法判定主版本号变更，保守返回空
        return bumped

    for rel in releases:
        full = rel.get("repo_full_name")
        if not full:
            continue
        tags = by_repo_all_tags.get(full) or []
        if len(tags) < 2:
            continue
        # tags 假定倒序（最新在前）；取最新两个比 major
        cur_maj = _major(tags[0])
        prev_maj = _major(tags[1])
        if cur_maj is not None and prev_maj is not None and cur_maj > prev_maj:
            bumped.add(full)
    return bumped


# ============================================================
# ④本周重点 信号分（SOP ④信号分计算，权重在 config.SIGNAL_WEIGHTS）
# ============================================================
def signal_score(
    item: dict[str, Any],
    *,
    diffs: dict[str, Any],
    major_bumps: set[str],
    license_changed: set[str],
    rising_top3: set[str],
    new_entries: set[str],
) -> tuple[int, list[str]]:
    """算某项目的信号分（SOP ④）。

    返回 (总分, 触发理由列表)。理由用于④栏目"为什么解读它"。
    影响面加权：× 当前 star 档位系数（config.SIGNAL_STAR_MULTIPLIER）。
    """
    weights = config.SIGNAL_WEIGHTS
    full = _full(item)
    reasons: list[str] = []

    if full in major_bumps:
        reasons.append("重大版本(主版本号变更)")
    if full in rising_top3:
        reasons.append("star 净增进入快速上涨榜前3")
    if full in new_entries:
        reasons.append("首次入榜/star 破阈值")
    if full in license_changed:
        reasons.append("license 本周变更")
    # 活跃度突变：commit 活跃且新入榜/上涨，近似判为活跃度突变（无前周 commit 数据时保守）
    if item.get("is_active") and (full in new_entries or full in rising_top3):
        reasons.append("活跃度较前周显著上升")

    base = sum(weights[k] for k, on in [
        ("major_version", full in major_bumps),
        ("star_anomaly", full in rising_top3),
        ("first_entry", full in new_entries),
        ("license_change", full in license_changed),
        ("activity_spike", item.get("is_active") and (full in new_entries or full in rising_top3)),
    ] if on)

    # 影响面加权系数
    star = _star(item)
    multiplier = 1.0
    for threshold, mult in config.SIGNAL_STAR_MULTIPLIER:
        if star < threshold:
            multiplier = mult
            break
    return int(round(base * multiplier)), reasons


def top_focus_items(
    pool: list[dict[str, Any]],
    *,
    diffs: dict[str, Any],
    releases: list[dict[str, Any]],
    license_changed: set[str],
    major_bumps: set[str],
) -> list[dict[str, Any]]:
    """选信号分最高的前 FOCUS_MAX_ITEMS 项目作"本周重点"。

    返回 [{item, signal_score, reasons}]，信号分降序。
    首期（first_period）：major_bumps/license 仍可用，但 star_anomaly/first_entry 失效。
    """
    if diffs.get("first_period"):
        rising_top3: set[str] = set()
        new_entries: set[str] = set()
    else:
        # 快速上涨榜前 3
        pool_map = {_full(it): it for it in pool}
        rising = rising_list(diffs, pool_map)[:3]
        rising_top3 = {r["full_name"] for r in rising}
        new_entries = set(diffs.get("new_entries", []))

    scored: list[dict[str, Any]] = []
    for item in pool:
        score, reasons = signal_score(
            item,
            diffs=diffs,
            major_bumps=major_bumps,
            license_changed=license_changed,
            rising_top3=rising_top3,
            new_entries=new_entries,
        )
        if score > 0:
            scored.append({"item": item, "signal_score": score, "reasons": reasons})
    scored.sort(key=lambda x: x["signal_score"], reverse=True)
    return scored[: config.FOCUS_MAX_ITEMS]


# ============================================================
# 6 第3层 价值评分卡（仅用于排序，不写进正文）
# ============================================================
def value_score(item: dict[str, Any], diffs: dict[str, Any]) -> int:
    """SOP 6 第3层价值评分卡（满分100，仅排序用）。

    真实性25 + 活跃度25 + 趋势20 + 稀缺性15 + 决策相关15。
    数据有限时按可得信号近似打分（不影响客观性——评分只决定"谁上榜/排序"）。
    """
    score = 0
    full = _full(item)
    star = _star(item)

    # 真实性（25）：官方 org/内核 +15（白名单/分类非 tool/ai 近内核）
    source = item.get("source")
    if source == "whitelist":
        score += 15
    cats = item.get("category") or []
    if isinstance(cats, list) and "core" in cats:
        score += 10

    # 活跃度（25）：近7天有commit 10 + 近7天有release 10 + star高(>1k) 5
    if item.get("is_active"):
        score += 10
    # release 活跃由调用方补 release_repos 集合；此处用 pushed_at 近30天近似
    if _pushed_recent(item, 30):
        score += 10
    if star >= 1000:
        score += 5

    # 趋势（20）：star 净增进品类 TOP 15 + 非一次性爆点(有 push) 5
    if not diffs.get("first_period"):
        deltas = diffs.get("star_deltas", {})
        delta = deltas.get(full, 0)
        # 近似：净增 > 中位数即算头部（这里用绝对阈值 50 简化）
        if delta >= 50:
            score += 15
        if _pushed_recent(item, 90):
            score += 5
    else:
        # 首期无 delta，用 star 档位近似趋势
        if star >= 1000:
            score += 15
        if _pushed_recent(item, 90):
            score += 5

    # 稀缺性（15）：填补品类空白 —— 国产/小众 topic 命中近似
    topics = item.get("source_topics") or [item.get("source_topic")] or []
    rare_topics = {"opengauss", "oceanbase", "polardb", "tdsql", "dm", "gbase", "yashandb", "goldendb"}
    if any(t in rare_topics for t in (topics or [])):
        score += 15

    # 决策相关（15）：license 变更 / 重大架构 —— 无 license 变更上下文时用 NOASSERTION 近似
    lic = item.get("license")
    if isinstance(lic, dict) and lic.get("spdx_id") in ("NOASSERTION", None):
        score += 5  # 自定义协议，选型时需关注

    return score


# ============================================================
# 6.y 榜单归属分层漏斗（④②①⑧⑤ 五选一，防霸屏）
# ============================================================
def assign_main_section(
    pool: list[dict[str, Any]],
    focus_fulls: set[str],
    diffs: dict[str, Any],
    rising_fulls: set[str],
) -> dict[str, str]:
    """每个项目按固定优先级归入唯一主榜（SOP 6.y Step1-5，命中即停）。

    判断顺序：④本周重点 → ②新生(30天内) → ①快速上涨 → ⑧AI头部 → ⑤总榜兜底。
    返回 {full_name: 主榜key}（主榜key: focus/new/rising/ai/topboard）。
    被舍弃的榜由 render 层据归属结果标"见XX榜"（cross_ref）。
    """
    pool_map = {_full(it): it for it in pool}
    new_set = set(diffs.get("new_entries", [])) if not diffs.get("first_period") else set()
    # ②新生：30 天内创建（不依赖 diff，按 created_at 直接判）
    new_created = {full for full, it in pool_map.items() if _created_recent(it, 30)}

    attribution: dict[str, str] = {}
    for item in pool:
        full = _full(item)
        # Step1 ④本周重点
        if full in focus_fulls:
            attribution[full] = "focus"
        # Step2 ②新生（30天内创建）
        elif full in new_created:
            attribution[full] = "new"
        # Step3 ①快速上涨
        elif full in rising_fulls:
            attribution[full] = "rising"
        # Step4 ⑧AI 类且 star 头部
        elif _is_ai_head(item):
            attribution[full] = "ai"
        # Step5 ⑤总榜兜底
        else:
            attribution[full] = "topboard"
    return attribution


# ============================================================
# 辅助
# ============================================================
def _full(item: dict[str, Any]) -> str:
    return str(item.get("full_name") or "")


def _star(item: dict[str, Any]) -> int:
    try:
        return int(item.get("stargazers_count") or 0)
    except (TypeError, ValueError):
        return 0


def _is_ai_head(item: dict[str, Any]) -> bool:
    """⑧AI 类项目且 star 头部（SOP 6.y Step4）。

    AI 类：category 含 'ai'（由 filters.classify 标注）。
    头部：star 进入候选池 AI 类前 N（这里用绝对阈值 1000 近似，可 config 化）。
    """
    cats = item.get("category") or []
    if not (isinstance(cats, list) and "ai" in cats):
        return False
    return _star(item) >= 1000


def _pushed_recent(item: dict[str, Any], days: int) -> bool:
    """近 N 天是否有 push（pushed_at 字符串比较近似）。"""
    pushed = item.get("pushed_at")
    if not pushed:
        return False
    try:
        from datetime import datetime, timedelta, timezone
        pt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        return pt >= datetime.now(timezone.utc) - timedelta(days=days)
    except (ValueError, TypeError):
        return False


def _created_recent(item: dict[str, Any], days: int) -> bool:
    """是否 N 天内创建（②新生项目口径，按 created_at 直接判，不依赖 diff）。"""
    created = item.get("created_at")
    if not created:
        return False
    try:
        from datetime import datetime, timedelta, timezone
        ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
        return ct >= datetime.now(timezone.utc) - timedelta(days=days)
    except (ValueError, TypeError):
        return False
