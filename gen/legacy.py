# -*- coding: utf-8 -*-
"""legacy.py -- 旧资产进 dist：weekly 周报、首页壳、assets、往期页。

纪律：旧页源文件不动（仍在仓根），dist 里做最小修补——仅 index.html 的 projects.html
链接改指 /projects/（旧 JS 版列表页不进站）。pool.js 及其加载页绝不拷贝。
"""
import os, shutil
import common as C

COPY_DIRS = ["weekly", "assets"]                    # 目录整拷
COPY_FILES = ["index.html", "mystack.html", "archive.html", "compare.html",
              "data/weekly.js", "data/comparisons.js"]
PATCH = [("projects.html", "/projects/")]           # (旧链接, 新链接) 仅作用于 index.html

def copy_legacy(cfg, out_dir):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # dbhub_page 根
    n = 0
    for d in COPY_DIRS:
        src, dst = os.path.join(here, d), os.path.join(out_dir, d)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True); n += 1
    for f in COPY_FILES:
        src, dst = os.path.join(here, f), os.path.join(out_dir, f)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst); n += 1
    idx = os.path.join(out_dir, "index.html")
    if os.path.isfile(idx):
        t = open(idx, encoding="utf-8").read()
        for old, new in PATCH: t = t.replace(old, new)
        open(idx, "w", encoding="utf-8", newline="\n").write(t)
    assert not os.path.exists(os.path.join(out_dir, "data", "pool.js")), "pool.js 混进 dist"
    print(f"OK legacy: {n} 项旧资产进站（weekly/assets/首页等），pool.js 已排除，index 导航修补")
    return n
