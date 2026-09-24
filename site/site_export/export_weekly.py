# -*- coding: utf-8 -*-
"""模块 3：周报导出（run_weekly 完成后跑）。

读 data/snapshot_{date}/weekly/meta/ 的定榜结果（sections / ai_reviews / diff）
+ 当日池 + history → 站点周报数据：

  BLOG_SITE_DIR/weekly-{N}.json    周报全字段（demo 契约：kpi/hooks/board_secs/
                                    focus+三维/newfaces/rotated_out）
  BLOG_SITE_DIR/issues-index.json  往期页清单（追加/同日覆盖）

hooks 为自动草稿（draft:true），人工改写文案后置 draft:false 再部署。
用法：
  python site_export/export_weekly.py --date 20260918
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_common as sc  # noqa: E402

log = logging.getLogger("weekly_export")

SECTIONS_META_DIR = "weekly/meta"
PERSONA_LABEL = {"use": "用库", "ops": "管库", "build": "造库"}


def _load_meta(date: str, name: str):
    p = sc.DATA_DIR / f"snapshot_{date}" / SECTIONS_META_DIR / f"{name}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.warning("读 %s 失败：%s", p, e)
        return None


def _last_issue(date: str) -> tuple[dict | None, set[str], set[str], dict]:
    """(最近一期历史条目, 上期上榜名, 上期解读名, focus增长记录 {fn: growth})。"""
    names, focuses, focus_growth = set(), set(), {}
    last = None
    try:
        h = json.loads((sc.V2_ROOT / "reports" / "weekly_history.json").read_text(encoding="utf-8"))
        for e in h.get("entries") or []:
            if e.get("date") == date:
                continue
            last = e  # 取最后一个非当日条目
        # 累计所有期（排他/冷却口径与管道一致取最近一期即可，这里取最近一期）
        if last:
            for sec in (last.get("sections") or {}).values():
                for r in sec.get("active") or []:
                    if r.get("full_name"):
                        names.add(r["full_name"])
                f = sec.get("focus") or {}
                if f.get("full_name"):
                    focuses.add(f["full_name"])
                    if f.get("growth") is not None:
                        focus_growth[f["full_name"]] = f.get("growth")
    except (OSError, json.JSONDecodeError) as e:
        log.warning("weekly_history 读取失败：%s", e)
    return last, names, focuses, focus_growth


def _last_issue_shown_names(last: dict | None) -> set[str]:
    """上期实际展示过的项目（active ∪ newcomers ∪ focus）——新面孔排重用。"""
    shown: set[str] = set()
    if not last:
        return shown
    prev_sections = _load_meta(last["date"], "sections") or {}
    for sec in prev_sections.get("sections") or []:
        for key in ("active", "newcomers"):
            for r in sec.get(key) or []:
                if r.get("full_name"):
                    shown.add(r["full_name"])
        f = sec.get("focus") or {}
        if f.get("full_name"):
            shown.add(f["full_name"])
    for sec in (last.get("sections") or {}).values():
        for r in sec.get("active") or []:
            if r.get("full_name"):
                shown.add(r["full_name"])
        f = sec.get("focus") or {}
        if f.get("full_name"):
            shown.add(f["full_name"])
    return shown


def _official_orgs(date: str) -> set[str]:
    orgs = sc.read_orgs(date) or {}
    return {o.lower() for o in orgs}


def enrich_row(row: dict, pool_map: dict, h: dict, prev_growth: dict | None) -> dict:
    """定榜 row + 池项目 + history → 站点记录。"""
    fn = row.get("full_name") or ""
    it = pool_map.get(fn) or {}
    r = sc.record(it or {"full_name": fn, "description": row.get("description") or "",
                         "topics": row.get("topics") or [], "html_url": row.get("html_url")},
                  growth=row.get("growth"))
    r["category_raw"] = row.get("category")
    r["dbs_raw"] = row.get("databases")
    r["persona"], r["ai"] = sc.persona_of(r["section"], r["cat"], r["fn"], r["desc"])
    w = h["watched"].get(fn)
    wp, gs = sc.streaks_of(w)
    r["weeks_in_pool"], r["growth_streak"] = wp, gs
    r["spark"] = [(w.get("daily") or {}).get(d) for d in h["meta"]["dates"]] if w else []
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description="周报导出")
    ap.add_argument("--date", required=True, help="出刊观察日 YYYYMMDD（须已跑 run_weekly）")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-6s %(name)s | %(message)s",
                        datefmt="%H:%M:%S", stream=sys.stdout)
    date = args.date

    sections_data = _load_meta(date, "sections")
    if not sections_data or not sections_data.get("finalized"):
        log.error("%s 无已定榜的 sections.json——请先跑 run_weekly（--date %s）。", date, date)
        sys.exit(2)
    ai_reviews = _load_meta(date, "ai_reviews") or {}
    diff = _load_meta(date, "diff") or {}
    brief = ai_reviews.get("brief") or {}
    three = ai_reviews.get("three") or {}
    star_deltas: dict = diff.get("star_deltas") or {}
    new_entries: list = diff.get("new_entries") or []

    pool = sc.read_pool(date) or []
    pool_map = {it.get("full_name"): it for it in pool}
    scoped = sc.scoped_items(pool)
    scoped_names = {it.get("full_name") for it in scoped}
    h = sc.load_history()
    sc.bind_history(h)
    last, last_active, last_focus, focus_growth = _last_issue(date)
    shown = _last_issue_shown_names(last)
    officials = _official_orgs(date)

    n = sc.issue_no(date)
    if n <= 0:
        log.error("期号计算失败（config.FIRST_ISSUE_DATE / date）。")
        sys.exit(2)

    # ---- 三板块定榜 ----
    board_secs = {}
    all_active_rows = []
    focus = None
    for sec in sections_data.get("sections") or []:
        key = sec.get("key") or ""
        rows = []
        for row in sec.get("active") or []:
            r = enrich_row(row, pool_map, h, star_deltas)
            r["review"] = brief.get(r["fn"], "")
            rows.append(r)
            all_active_rows.append(r)
        board_secs[key] = rows
        f = sec.get("focus")
        if f and not focus:
            fr = enrich_row(f, pool_map, h, star_deltas)
            fr["three"] = three.get(fr["fn"], {})
            note = ""
            if fr["fn"] in focus_growth and isinstance(fr["growth"], (int, float)):
                if fr["growth"] > (focus_growth[fr["fn"]] or 0):
                    note = f"爆发豁免回归（本周 +{int(fr['growth'])} 超上次解读记录 +{focus_growth[fr['fn']]}）"
            fr["focus_note"] = note
            focus = fr

    # ---- 轮换让位：上期上榜 ∩ 本期范围内有增长 ----
    rotated = []
    for fn in sorted(last_active):
        g = star_deltas.get(fn)
        if g is not None and g > 0 and fn in scoped_names:
            rotated.append({"fn": fn, "growth": g})

    # ---- 新面孔：新入池 ∩ 范围内，未在上期展示，过门槛（≥50 或官方 org 出品）----
    newfaces = []
    for fn in new_entries:
        if fn in shown or fn not in scoped_names:
            continue
        it = pool_map.get(fn)
        if not it:
            continue
        owner = fn.split("/")[0].lower()
        stars = it.get("stargazers_count") or 0
        if stars < 50 and owner not in officials:
            continue
        r = sc.record(it, growth=stars)
        r["persona"], r["ai"] = sc.persona_of(r["section"], r["cat"], r["fn"], r["desc"])
        newfaces.append(r)
    newfaces.sort(key=lambda r: -r["stars"])
    newfaces = newfaces[:5]

    # ---- KPI ----
    with_growth = sum(1 for fn in scoped_names
                      if (star_deltas.get(fn) or 0) > 0)
    new_pool = sum(1 for fn in new_entries if fn in scoped_names)

    # ---- hooks 草稿（人工改写后置 draft:false）----
    top_mover = max(all_active_rows, key=lambda r: (r["growth"] or 0)) if all_active_rows else None
    top_new = newfaces[0] if newfaces else None
    cn_rows = [r for r in all_active_rows if r["section"] == "国产数据库"]
    cn_top = max(cn_rows, key=lambda r: (r["growth"] or 0)) if cn_rows else None
    hooks = []
    if top_mover:
        hooks.append({"title": top_mover["fn"].split("/")[-1],
                      "text": f"本周 +{top_mover['growth']}★（{top_mover['stars']}★），活跃榜首",
                      "draft": True})
    if top_new:
        hooks.append({"title": top_new["fn"].split("/")[-1],
                      "text": f"{top_new['stars']}★ 首入池，{'官方出品' if top_new['fn'].split('/')[0].lower() in officials else ''}",
                      "draft": True})
    if cn_top:
        hooks.append({"title": "国产板块",
                      "text": f"本周最高增长 +{cn_top['growth']}★（{cn_top['fn'].split('/')[-1]}）",
                      "draft": True})

    out = {
        "issue_no": n, "date": f"{date[:4]}-{date[4:6]}-{date[6:]}",
        "snapshot_date": date,
        "window": {"from": sections_data.get("prev_date"), "to": date},
        "pool_total": len(pool), "pool_scoped": len(scoped),
        "with_growth": with_growth, "new_pool": new_pool,
        "rotated_count": len(rotated),
        "hooks": hooks,
        "board_secs": board_secs,
        "focus": focus,
        "newfaces": newfaces,
        "newfaces_note": f"门槛：star≥50 或官方组织出品（过滤后通过 {len(newfaces)} 个）",
        "rotated_out": rotated,
    }
    sc.write_site_json(f"weekly-{n}.json", out)

    # ---- 往期索引（追加 / 同期覆盖）----
    idx_path = sc.BLOG_SITE_DIR / "issues-index.json"
    entries = []
    if idx_path.is_file():
        try:
            entries = json.loads(idx_path.read_text(encoding="utf-8")).get("entries") or []
        except (OSError, json.JSONDecodeError):
            entries = []
    entries = [e for e in entries if e.get("issue_no") != n]
    entries.append({
        "type": "weekly", "issue_no": n, "date": out["date"],
        "status": "draft",
        "summary": " · ".join(h["text"] for h in hooks)[:120],
        "counts": {"board": sum(len(v) for v in board_secs.values()),
                   "newfaces": len(newfaces)},
    })
    entries.sort(key=lambda e: (e.get("date") or ""))
    sc.write_site_json("issues-index.json", {"entries": entries})
    log.info("==== 周报 %d 导出完成（board %d · newfaces %d · rotated %d）====",
             n, sum(len(v) for v in board_secs.values()), len(newfaces), len(rotated))


if __name__ == "__main__":
    main()
