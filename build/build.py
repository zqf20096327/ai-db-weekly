# -*- coding: utf-8 -*-
"""DBHub Pages 数据构建入口（纯标准库）。

从 dbhub_collect 读取采集数据（M2b 新形态：NDJSON 活文件 + 缓存分片 +
git 历史增星基准），推导归属/类别/信号，产出前端可直接 <script> 加载的
data/pool.js 与 data/detail.js，及 build/audit_wide_dbs.json 宽归属审计。

模块划分：sources 装载 / taxonomy 库口径 / classify 规则分类 /
interp AI 解读护栏 / assemble 主流水线 / emit 输出 / report 报告。

用法:
  python build/build.py [--collect-dir D:/dbhub_collect] [--out .] [--report]
"""
import argparse
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect-dir", default="D:/dbhub_collect")
    ap.add_argument("--out", default=".")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    import sources, taxonomy, assemble, emit, report
    t0 = time.time()
    bundle = sources.load_bundle(args.collect_dir)
    print("snapshot:", bundle.snap,
          "| interp:", len(bundle.interp),
          "| growth base:", bundle.old_date or "none", len(bundle.old_stars))
    tax = taxonomy.build_taxonomy(bundle.profiles, bundle.glob)
    records, detail, stats, wide_dbs = assemble.build_records(bundle, tax)
    emit.write_outputs(args.out, bundle, records, detail, stats, wide_dbs)
    report.print_summary(bundle, stats, wide_dbs)
    print(f"elapsed={time.time()-t0:.1f}s")
    if args.report:
        report.print_report(records, stats)


if __name__ == "__main__":
    main()
