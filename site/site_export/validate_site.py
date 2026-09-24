# -*- coding: utf-8 -*-
"""模块 5：站点数据校验（部署前闸门，坏数据不上线）。

扫描 BLOG_SITE_DIR 下全部 *.json：
  - 可解析；
  - now / map / weekly-* / monthly-* / issues-index / archive-* 各自必填字段齐全；
  - 日期格式合法；issues-index 期号随日期递增；
任一失败退出码 1（deploy.sh 前置调用即可阻断上传）。

用法：
  python site_export/validate_site.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_common as sc  # noqa: E402

log = logging.getLogger("validate")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fail(msgs: list[str], name: str, cond: bool, msg: str) -> None:
    if not cond:
        msgs.append(f"{name}: {msg}")


def main() -> None:
    ap = argparse.ArgumentParser(description="站点数据校验")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)-6s %(name)s | %(message)s", stream=sys.stdout)

    d = sc.BLOG_SITE_DIR
    if not d.is_dir() or not list(d.glob("*.json")):
        log.error("输出目录为空：%s", d)
        sys.exit(2)
    msgs: list[str] = []
    files = sorted(d.glob("*.json"))
    for p in files:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            msgs.append(f"{p.name}: JSON 解析失败 {e}")
            continue
        name = p.name
        if name == "now.json":
            fail(msgs, name, isinstance(obj.get("updated"), str) and DATE_RE.match(obj["updated"]),
                 "updated 非法")
            fail(msgs, name, isinstance(obj.get("snapshot_days"), int), "snapshot_days 缺失")
        elif name == "map.json":
            fail(msgs, name, isinstance(obj.get("matrix"), dict) and obj["matrix"], "matrix 缺失")
            fail(msgs, name, isinstance(obj.get("db_order"), list) and obj["db_order"], "db_order 缺失")
            fail(msgs, name, DATE_RE.match(str(obj.get("date", ""))), "date 非法")
        elif name.startswith("weekly-"):
            n = name[7:-5]
            fail(msgs, name, n.isdigit() and int(n) >= 1, "文件名期号非法")
            for key in ("issue_no", "date", "hooks", "board_secs", "focus"):
                fail(msgs, name, key in obj, f"缺 {key}")
            fail(msgs, name, isinstance(obj.get("board_secs"), dict) and
                 sum(len(v) for v in obj["board_secs"].values()) > 0, "board_secs 为空")
            fail(msgs, name, bool(obj.get("focus")), "focus 为空")
            fail(msgs, name, DATE_RE.match(str(obj.get("date", ""))), "date 非法")
            fail(msgs, name, obj.get("issue_no") == int(n), "issue_no 与文件名不一致")
        elif name.startswith("monthly-"):
            fail(msgs, name, bool(obj.get("window")) and bool(obj.get("top_gain")), "window/top_gain 缺失")
            fail(msgs, name, bool(re.match(r"^\d{4}-\d{2}$", str(obj.get("month", "")))), "month 非法")
        elif name == "issues-index.json":
            es = obj.get("entries") or []
            fail(msgs, name, len(es) > 0, "entries 为空")
            nos = [e.get("issue_no") for e in es if e.get("type") == "weekly"]
            fail(msgs, name, nos == sorted(set(nos)), "期号乱序或重复")
            for e in es:
                fail(msgs, name, DATE_RE.match(str(e.get("date", ""))), f"entry date 非法 {e}")
        elif name.startswith("archive-"):
            fail(msgs, name, isinstance(obj.get("groups"), dict) and obj["groups"], "groups 为空")
            fail(msgs, name, bool(obj.get("db")), "db 缺失")

    if msgs:
        for m in msgs:
            log.error("✗ %s", m)
        log.error("==== 校验失败：%d 项（阻断部署）====", len(msgs))
        sys.exit(1)
    log.info("==== 校验通过：%d 个文件 ====", len(files))


if __name__ == "__main__":
    main()
