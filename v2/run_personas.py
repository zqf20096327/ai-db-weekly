"""M5 人群分类：批量 AI 把工具分到 用库/管库/造库 + AI 叠加标。

分类规则（2026-09-22 用户定案，与 demo 施工图一致）：
  - 主类三选一：use 用库（开发者/使用者）、ops 管库（DBA/运维/平台）、build 造库（内核/基建）；
  - 灰地带：迁移同步/数据治理 → ops；BI/报表 → use；内核级性能库/协议实现 → build；
  - AI 横切：核心能力是 LLM/Agent/text2sql/MCP 等范式时叠加 ai 标，不改变主类。

缓存：site_export/personas.json {fn: {p, ai, why, when}}（只存 AI 成功结果，
增量续跑自动跳过；规则版 persona_of 仍是聚合时的兜底）。
默认只跑默认展示档（≈850 项，30-40 分钟一次性）；--all 扩到全量 watched。

用法：
  python run_personas.py            # tier1 增量
  python run_personas.py --all     # 全量 watched
  python run_personas.py --cap 100  # 本次最多 N 项（试跑）
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

log = logging.getLogger("run_personas")

PERSONAS_FILE = Path(r"D:\db-oss-observer\site_export\personas.json")

_PROMPT = """你是数据库开源工具的分类助手。只依据给出的信息，把项目分给最合适的"使用人群"主类，并判断是否叠加 AI 标。

主类三选一：
- use 用库（应用开发者/最终使用者：客户端、GUI、IDE、ORM、BI、查询与建模、AI 辅助使用）
- ops 管库（DBA/运维/平台：备份、监控、高可用、迁移同步、CDC、数据治理、审计管控平台）
- build 造库（内核/基建：存储引擎、wire protocol 实现、性能原语、数据库重写或再实现）

灰地带规则：迁移同步/数据治理→ops；BI/报表→use；内核级性能库/协议库→build。
AI 叠加标：项目核心能力是 LLM/Agent/text2sql/MCP/RAG 等范式（用于数据库场景）时 ai=true，否则 false；ai=true 不改变主类。

项目：{fn}
描述：{desc}
topics：{topics}
规则版任务分类（仅供参考，可推翻）：{cat}

只输出一行 JSON，格式：{{"p":"use|ops|build","ai":true|false,"why":"不超过16字的理由"}}"""


def load_cache() -> dict:
    if PERSONAS_FILE.is_file():
        try:
            return json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.warning("personas.json 损坏，从空开始")
    return {}


def save_cache(c: dict) -> None:
    tmp = PERSONAS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PERSONAS_FILE)


def parse_answer(text: str) -> dict | None:
    """从模型输出里稳健地抽 JSON（容错多余文字/代码块围栏）。"""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    p = obj.get("p")
    if p not in ("use", "ops", "build"):
        return None
    ai = obj.get("ai")
    return {"p": p, "ai": bool(ai), "why": str(obj.get("why") or "")[:24]}


def main() -> None:
    ap = argparse.ArgumentParser(description="批量 AI 人群分类")
    ap.add_argument("--all", action="store_true", help="全量 watched（默认只 tier1）")
    ap.add_argument("--cap", type=int, default=0, help="本次最多分类 N 项（0=不限）")
    ap.add_argument("--date", help="指定快照日 YYYYMMDD（默认最新）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)

    # 复用 run_enrich 的目标构建（同口径：scoped + star≥10）
    from run_enrich import build_targets  # noqa: PLC0415
    import storage  # noqa: PLC0415
    dates = storage.list_snapshot_dates()
    date = args.date or (dates[-1] if dates else None)
    if not date:
        log.error("无观察日")
        sys.exit(2)
    from storage import _read_json  # noqa: PLC0415
    pool = _read_json(storage.merged_file(date))
    if not isinstance(pool, list):
        log.error("%s 读不到候选池", date)
        sys.exit(2)

    tier1 = config.PERSONA_TIER1_ONLY and not args.all
    targets = build_targets(pool, tier1=tier1)
    log.info("分类目标：%d 项（%s，%s）", len(targets), date, "tier1" if tier1 else "全量")

    cache = load_cache()
    todo = [t for t in targets if t.get("full_name") not in cache]
    if args.cap > 0:
        todo = todo[:args.cap]
    log.info("缓存已有 %d，本次待分类 %d", len(cache), len(todo))
    if not todo:
        log.info("无需分类，退出")
        return

    from ai_client import AIClient  # noqa: PLC0415
    ai = AIClient()
    if not ai.enabled:
        log.error("AI_API_KEY 未配置，无法批量分类（退出码 1）")
        sys.exit(1)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ok = fail = 0
    for i, it in enumerate(todo, 1):
        fn = it.get("full_name") or ""
        desc = (it.get("description") or "")[:200]
        topics = ", ".join(str(t) for t in (it.get("topics") or [])[:12])
        cat = it.get("category") or "其他"
        ans = parse_answer(ai._chat(_PROMPT.format(  # noqa: SLF001 同仓库内部调用
            fn=fn, desc=desc or "（无描述）", topics=topics or "（无）", cat=cat)))
        if ans:
            cache[fn] = {**ans, "when": today}
            ok += 1
        else:
            fail += 1
        if i % 20 == 0:
            log.info("  进度 %d/%d（成功 %d 失败 %d）", i, len(todo), ok, fail)
            save_cache(cache)
        time.sleep(config.PERSONA_SLEEP_SEC)

    save_cache(cache)
    log.info("==== 人群分类完成：成功 %d 失败 %d，缓存累计 %d → %s ====",
             ok, fail, len(cache), PERSONAS_FILE)


if __name__ == "__main__":
    main()
