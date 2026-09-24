"""任务分类 AI 兜底（M5·分类体系升级版，2026-09-22 定案）。

三层分类的第③层：对 site_common.task_cat（topics 精确 + 词形关键词）判为
「其他」的 watched 项目批量 AI 分类，缓存到 site_export/categories.json，
aggregate_daily 聚合时消费。第 8 类「开发库」=驱动/ORM/SDK/查询构建/SQL 工具。

护栏（区别于试验版）：
  1. 提示词硬约束「只依据给出的信息，不得使用对项目的既有了解」；
  2. 置信度字段 ev（高/中/低），低置信不采纳（落盘但不进 categories.json
     的消费面——写 ev=低 时聚合端忽略）；
  3. 增量续跑：缓存命中跳过；枚举外输出丢弃。

用法：
  python run_categories.py            # 增量（残余「其他」全量）
  python run_categories.py --cap 100  # 试跑
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import config

SITE_EXPORT = Path(r"D:\db-oss-observer\site_export")
sys.path.insert(0, str(SITE_EXPORT))
import site_common as sc  # noqa: E402

log = logging.getLogger("run_categories")

CATS = ["备份", "监控", "高可用", "迁移", "连接/代理", "管理", "平台", "开发库", "其他"]
# 重判 TTL（天）：缓存条目（含低置信拒绝条目）超过此天数后重新分类，
# 项目转型时标签最迟 90 天自愈；全量 ~4.9k 下稳态重判 ≈54 项/天
RECLASSIFY_DAYS = 90

PROMPT = """你是数据库开源工具的任务分类助手。

【重要】只依据下面给出的信息判断，不得使用你对这些项目的任何既有了解或记忆。信息不足以判断时，直接输出"其他"，不要猜测。

类目（互斥，选一个）：
- 备份：备份/恢复/PITR/WAL 归档
- 监控：监控告警/可观测/慢查询诊断/指标采集
- 高可用：主从复制/故障切换/集群
- 迁移：数据迁移/同步/CDC/ETL/导入导出/结构变更
- 连接/代理：连接池/代理/负载均衡/网关
- 管理：客户端/GUI/IDE/管控入口/审计权限
- 平台：DBaaS/云托管/控制台/一体化平台
- 开发库：驱动/ORM/SDK/查询构建器/SQL 解析转译优化工具
- 其他：以上都不合适或信息不足

项目：{fn}
描述：{desc}
topics：{topics}

只输出一行 JSON：{{"cat":"备份|监控|高可用|迁移|连接/代理|管理|平台|开发库|其他","why":"不超过16字、引用输入中的依据","ev":"高|中|低"}}"""


def main() -> None:
    ap = argparse.ArgumentParser(description="任务分类 AI 兜底（护栏版）")
    ap.add_argument("--cap", type=int, default=0, help="本次最多分类 N 项（0=不限）")
    ap.add_argument("--date", help="快照日 YYYYMMDD（默认最新）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-6s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    # 目标集与 run_enrich 同口径（scoped + star≥10）
    from run_enrich import build_targets  # noqa: PLC0415
    import storage  # noqa: PLC0415
    dates = storage.list_snapshot_dates()
    date = args.date or (dates[-1] if dates else None)
    if not date:
        log.error("无观察日"); sys.exit(2)
    from storage import _read_json  # noqa: PLC0415
    pool = _read_json(storage.merged_file(date))
    if not isinstance(pool, list):
        log.error("%s 读不到候选池", date); sys.exit(2)
    targets = build_targets(pool, tier1=False)
    log.info("目标 %d 项（%s）", len(targets), date)

    # 残余 = 新三层分类（topics+词形+已有缓存）后仍为其他
    # 缓存正本在 v2/data/categories.json（随白名单入仓），聚合端读同步副本
    cache = sc.load_categories()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n_stamped = 0
    for hit in cache.values():
        if isinstance(hit, dict) and not hit.get("when"):
            hit["when"] = today   # 存量迁移：TTL 从今天起算，避免一次性全量重判
            n_stamped += 1
    if n_stamped:
        log.info("存量缓存 %d 条补 when=%s（TTL 起算迁移）", n_stamped, today)

    def _fresh(hit) -> bool:
        """重判 TTL 内的条目跳过（含低置信拒绝条目——退避期内不重试）。"""
        w = str((hit or {}).get("when") or "")
        try:
            d = datetime.strptime(w, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        return (datetime.now(timezone.utc) - d).days < RECLASSIFY_DAYS

    path = Path(config.CATEGORIES_FILE)
    todo = []
    for it in targets:
        fn = it.get("full_name") or ""
        hit = cache.get(fn)
        if sc.task_cat(it) == "其他" and not (hit and _fresh(hit)):
            todo.append(it)
    if args.cap > 0:
        todo = todo[:args.cap]
    log.info("缓存已有 %d，本次待分类 %d", len(cache), len(todo))
    if not todo:
        log.info("无需分类，退出"); return

    from ai_client import AIClient  # noqa: PLC0415
    ai = AIClient()
    if not ai.enabled:
        log.error("AI_API_KEY 未配置"); sys.exit(1)

    path = SITE_EXPORT / "categories.json"
    ok = low = 0
    for i, it in enumerate(todo, 1):
        fn = it.get("full_name") or ""
        desc = (it.get("description") or "")[:200]
        topics = ", ".join(str(t) for t in (it.get("topics") or [])[:12])
        m = re.search(r"\{.*\}", ai._chat(PROMPT.format(  # noqa: SLF001
            fn=fn, desc=desc or "（无描述）", topics=topics or "（无）")) or "")
        try:
            obj = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            obj = {}
        ev = str(obj.get("ev") or "低")
        if obj.get("cat") in CATS and ev in ("高", "中"):
            cache[fn] = {"cat": obj["cat"], "why": str(obj.get("why") or "")[:24], "ev": ev,
                         "when": today}
            ok += 1
        else:
            # 低置信/枚举外：以 cat=其他 落缓存当拒绝条目——聚合端忽略（其他不在
            # CAT_ORDER），TTL 内不重试（退避），过期后自然重判
            cache[fn] = {"cat": "其他", "why": str(obj.get("why") or "")[:24], "ev": "低",
                         "when": today}
            low += 1
        if i % 20 == 0:
            log.info("  进度 %d/%d（采纳 %d 低置信/无效 %d）", i, len(todo), ok, low)
            path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(config.PERSONA_SLEEP_SEC)

    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    dist = Counter(v["cat"] for v in cache.values())
    log.info("==== 任务分类完成：采纳 %d / 低置信 %d，缓存累计 %d → %s",
             ok, low, len(cache), path)
    log.info("缓存分布：%s", dict(dist.most_common()))


if __name__ == "__main__":
    main()
