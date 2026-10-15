# -*- coding: utf-8 -*-
"""控制台报告：构建摘要（总是打印）与 --report 详细分布。"""
import random

import taxonomy as taxonomy_mod


def print_summary(bundle, stats, wide_dbs):
    """构建尾部摘要：宽归属审计 + 人工认领命中/未命中告警。"""
    print(f"宽归属审计（≥10 库 support）：{len(wide_dbs)} 条 → build/audit_wide_dbs.json")
    ovr_missing = [fn for fn in bundle.overrides if fn not in stats["seen"]]
    print(f"人工认领生效：{stats['override_n']} 条" +
          (f"｜警告 {len(ovr_missing)} 条未命中池（改名/出池？）：{'、'.join(ovr_missing[:5])}"
           if ovr_missing else ""))
    for w in sorted(wide_dbs, key=lambda x: -x["n"])[:12]:
        print(f"  {w['n']:2d} 库  {w['fn']}")


def print_report(records, stats):
    """--report：per-db / per-cat / 置信度 / 未归类 top-star / 随机抽样。"""
    print("\n-- per db --")
    for d in taxonomy_mod.DB_ORDER + ["未归类"]:
        print(f"  {d:12s} {stats['db_cnt'].get(d, 0)}")
    print("\n-- per cat --")
    for c, n in stats["cat_cnt"].most_common():
        print(f"  {c:10s} {n}")
    print("\n-- confidence --", dict(stats["conf_cnt"]))
    random.seed(7)
    print("\n-- sample 未归类 top-star --")
    for r in sorted((r for r in records if not r[5]),
                    key=lambda r: -r[3])[:10]:
        print(f"  {r[0]:50s} {r[3]:>7} {r[7]:6s} {r[22][:30]}")
    print("\n-- random sample 20 --")
    for r in random.sample(records, 20):
        print(f"  {r[0]:50s} st={r[3]:>6} db={r[5] or '-':12s} "
              f"cat={r[7]:8s} conf={r[8]} ev={r[22][:34]}")
