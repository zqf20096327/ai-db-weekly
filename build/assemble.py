# -*- coding: utf-8 -*-
"""主流水线：归属并集 + 信号计算 + records/detail 组装。

归属五通道并集（顺序无关，最终按 DB_ORDER 排序）：
  ① source_topic（topic/org 通道词） ② topics 主题/别名 ③ owner org
  ④ overrides 人工签发（优先级最高，≥10 库进宽审计）⑤ AI 解读 dbs
（已过 interp.merge_interp 的证据条件式护栏）。

records 为 32 列紧凑数组——列序是前端 assets/app.js 的 I 常量契约，不可变。
detail 仅收录 star>=100 的仓（readme 摘要 + 富集明细 + AI 解读文本）。
"""
from collections import Counter

import classify as classify_mod
import interp as interp_mod
import sources as sources_mod


def _db_sort_key(tax):
    order = tax.db_order

    def key(d):
        return order.index(d) if d in order else 99
    return key


def build_records(bundle, tax):
    """返回 (records, detail, stats, wide_dbs)。"""
    key = _db_sort_key(tax)
    topic2db, org2db = tax.topic2db, tax.org2db
    watch2db, alias2db = tax.watch2db, tax.alias2db

    seen = set()
    records, detail = [], {}
    db_cnt, cat_cnt, conf_cnt = Counter(), Counter(), Counter()
    wide_dbs = []          # ≥10 库 support 审计清单（护栏条件式的人工周检底册）
    stats = {"override_n": 0, "ai_n": 0, "sec_n": 0, "stale_n": 0, "g7cov": 0,
             "interp_n": 0, "ai_cat_n": 0, "eco_app_n": 0,
             "db_cnt": db_cnt, "cat_cnt": cat_cnt, "conf_cnt": conf_cnt}

    for it in bundle.pool:
        fn = it["full_name"]
        if fn in seen:
            continue
        seen.add(fn)
        e = bundle.enrich.get(fn) or {}
        st = it.get("stars") or 0
        # ---- 归属（source_topic 可能带引号，如 '"gbase 8s"'）
        stopic = (it.get("source_topic") or "").strip().strip('\'"').strip().lower()
        db = topic2db.get(stopic, "")
        if not db and it.get("source") == "org":
            db = org2db.get(stopic, "")
        dbs = {db} if db else set()
        for t in it.get("topics") or []:
            tl = t.lower()
            if tl in topic2db:
                dbs.add(topic2db[tl])
            elif tl in alias2db:
                dbs.add(alias2db[tl])
        ow = (it.get("owner") or "").lower()
        if ow in org2db:
            dbs.add(org2db[ow])
        dbs.discard("")
        dbs = sorted(dbs, key=key)
        db = db or (dbs[0] if dbs else "")
        # ---- 人工签发认领（第四通道：与规则/AI 并集、优先级最高）
        ovr = bundle.overrides.get(fn)
        if ovr:
            ovr_dbs = [d for d in ovr.get("dbs", []) if d in tax.db_order]
            dbs = sorted(set(dbs) | set(ovr_dbs), key=key)
            db = db or (dbs[0] if dbs else "")
            stats["override_n"] += 1
            if len(ovr_dbs) >= 10:                   # 人工认领同样进宽归属审计
                wide_dbs.append({"fn": fn, "n": len(ovr_dbs),
                                 "dbs": ovr_dbs, "gen": "override"})
        # ---- 分类 / AI / 信号（+ AI 解读合并：cat 高/中置信优先，规则兜底）
        cat, conf, ev = classify_mod.classify(it, watch2db, org2db)
        if ovr:                                       # 证据串前缀（修复旧版
            ev = "override" + ("|" + ev if ev else "")   # 拼上条残留的 bug）
        cat_src, eco, persona, status = "rule", "", "", ""
        entry = bundle.interp.get(fn)
        mi = interp_mod.merge_interp(entry, tax.db_order)
        if mi:
            stats["interp_n"] += 1
            if mi["wide_n"]:
                wide_dbs.append({"fn": fn, "n": mi["wide_n"],
                                 "dbs": list(mi["dbs"]),
                                 "gen": (entry or {}).get("generated_at", "")})
            if mi["cat"]:
                cat, conf, cat_src = mi["cat"], mi["conf"], "ai"
                stats["ai_cat_n"] += 1
            dbs = sorted(set(dbs) | set(mi["dbs"]), key=key)
            eco, persona, status = mi["eco"], mi["persona"], mi["status"]
            if eco == "app":
                stats["eco_app_n"] += 1
        db = db or (dbs[0] if dbs else "")
        if not db and not dbs:                      # 未归类：范围外提示
            oos = sorted({t for t in (it.get("topics") or [])}
                         & tax.oos_tokens)[:2]
            if oos:
                hint = "范围外:" + ",".join(oos)
                ev = hint + ("|" + ev if ev else "")
        aik = classify_mod.ai_flag(it, tax.ai_keywords)
        if mi and mi["aik"]:
            aik = mi["aik"]
        official = 1 if (ow in org2db or fn.lower() in watch2db) else 0
        if mi:
            official = official or mi["official"]
        c7, c90 = e.get("commit_7d"), e.get("commit_90d")
        rv, rd = e.get("rel_ver"), e.get("rel_days")
        sn, sw, ct = e.get("sec_n") or 0, e.get("sec_worst"), e.get("contrib_n")
        g7 = (st - bundle.old_stars[fn]) if fn in bundle.old_stars else None
        if g7 is not None:
            stats["g7cov"] += 1
        if aik:
            stats["ai_n"] += 1
        if sn:
            stats["sec_n"] += 1
        if st >= 1000 and c90 == 0 and e:
            stats["stale_n"] += 1
        section = "cn" if fn in bundle.cn_set else "i"
        rec = [fn, (it.get("description") or "")[:80],
               it.get("language") or "", st, it.get("forks") or 0,
               db, dbs, cat, conf, aik, official, section,
               it.get("created_at") or "", (it.get("pushed_at") or "")[:10],
               c7, c90, rv or "", rd, sn, sw, ct, g7, ev,
               it.get("license") or "",
               it.get("homepage") or "", 1 if it.get("archived") else 0,
               e.get("sec_last") or "", (e.get("rel_pub") or "")[:10],
               status, eco, persona, cat_src]
        records.append(rec)
        db_cnt[db or "未归类"] += 1
        cat_cnt[cat] += 1
        conf_cnt[conf] += 1
        # ---- detail（全量，无 star 门槛；AI 解读文本并入同一条目）
        d = {
            "rm": sources_mod.readme_head(bundle.collect_dir, fn),
            "si": ";".join(e.get("sec_ids") or [])[:300],
            "lg": ", ".join(f"{k} {v}%" for k, v in
                            list((e.get("lang") or {}).items())[:3]),
            "rp": e.get("rel_pub") or "",
            "ev": ev,
        }
        if mi and (mi["rw"] or mi["ol"]):
            d.update({k: mi[k] for k
                      in ("ol", "rw", "hl", "uc", "ins", "ew", "oe", "cg", "src")})
        detail[fn] = d

    stats["seen"] = seen
    return records, detail, stats, wide_dbs
