# -*- coding: utf-8 -*-
"""输出层：pool.js / detail 分片 / audit_wide_dbs.json 写盘。

输出格式是前端契约：window.META + window.POOL（32 列数组）由页面 <script> 直载；
detail 按需分片为 data/d/s{0..511}.json（assets/app.js 的 shardOf 用同一 djb2
算法定位片号，双端一致性由 selftest 抽样对答案钉死），键序与序列化参数不可变。
"""
import json
import os
from datetime import datetime

import classify as classify_mod
import taxonomy as taxonomy_mod

SHARD_N = 512


def shard_of(fn):
    """djb2 32 位（与 app.js shardOf 逐字符一致；fn 全 ASCII 由 selftest 断言）。"""
    h = 5381
    for ch in fn:
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return h % SHARD_N


def build_meta(bundle, records, stats):
    meta = {
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "snap": bundle.snap, "growthBase": bundle.old_date,
        "total": len(records),
        "attributed": len(records) - stats["db_cnt"].get("未归类", 0),
        "unattr": stats["db_cnt"].get("未归类", 0),
        "enriched": len(bundle.enrich), "ai": stats["ai_n"],
        "sec": stats["sec_n"], "stale": stats["stale_n"],
        "g7cov": stats["g7cov"], "interp": stats["interp_n"],
        "aiCat": stats["ai_cat_n"], "app": stats["eco_app_n"],
        "dbOrder": taxonomy_mod.DB_ORDER,
        "catOrder": classify_mod.CAT_ORDER,
    }
    return meta


def write_outputs(out, bundle, records, detail, stats, wide_dbs):
    """三件输出写盘，返回 (meta, 各文件路径)。"""
    meta = build_meta(bundle, records, stats)
    data_dir = os.path.join(out, "data")
    os.makedirs(data_dir, exist_ok=True)
    pool_path = os.path.join(data_dir, "pool.js")
    with open(pool_path, "w", encoding="utf-8") as f:
        f.write("window.META=" + json.dumps(meta, ensure_ascii=False,
                                            separators=(",", ":")))
        f.write(";\nwindow.POOL=")
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    shard_dir = os.path.join(data_dir, "d")
    os.makedirs(shard_dir, exist_ok=True)
    for old in os.listdir(shard_dir):          # 清旧片：防快照缩量后残留孤儿文件
        os.remove(os.path.join(shard_dir, old))
    buckets = [dict() for _ in range(SHARD_N)]
    for fn, dv in detail.items():
        buckets[shard_of(fn)][fn] = dv
    for n, bucket in enumerate(buckets):
        with open(os.path.join(shard_dir, "s%d.json" % n), "w", encoding="utf-8") as f:
            json.dump(bucket, f, ensure_ascii=False, separators=(",", ":"))
    sizes = [len(b) for b in buckets]
    print(f"shards: {SHARD_N} 片 · 每片均值 {len(detail)//SHARD_N} 条 · "
          f"最厚 {max(sizes)} / 最薄 {min(sizes)} · 空片 {sizes.count(0)}")
    detail_path = os.path.join(shard_dir, "s0.json")   # 代表路径，仅供返回占位
    audit_dir = os.path.join(out, "build")
    os.makedirs(audit_dir, exist_ok=True)
    audit_path = os.path.join(audit_dir, "audit_wide_dbs.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({"built": meta["built"], "snap": bundle.snap,
                   "count": len(wide_dbs), "items": wide_dbs},
                  f, ensure_ascii=False, indent=1)

    sz1 = os.path.getsize(pool_path) / 1e6
    sz2 = sum(os.path.getsize(os.path.join(shard_dir, f))
              for f in os.listdir(shard_dir)) / 1e6
    print(f"records={len(records)} detail={len(detail)} "
          f"pool.js={sz1:.1f}MB shards合计={sz2:.1f}MB")
    print("META:", json.dumps({k: v for k, v in meta.items()
                               if k not in ("dbOrder", "catOrder")},
                              ensure_ascii=False))
    return meta, (pool_path, detail_path, audit_path)
