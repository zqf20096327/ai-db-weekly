# -*- coding: utf-8 -*-
"""cards.py -- 活跃卡进站：cards/{owner}__{repo}.html -> dist/p/{owner}/{repo}/index.html

解耦决策（2026-11-16）：不用 _redirects 做 /p/{fn}/ -> cards/ 映射，而是物理目录布局
p/owner/repo/index.html——URL 天然成立，任何静态托管（CF Pages/GH Pages/任意 nginx）零配置，
平台适配层因此退化为可选。只拷 HTML 不拷 JSON（站上不需要卡片底稿）。
"""
import os, shutil
import common as C

def copy_cards(cfg, out_dir):
    src_dir = cfg["cards_root"]; n = 0; hostile = 0
    for f in os.listdir(src_dir):
        if not f.endswith(".html"): continue
        stem = f[:-5]
        owner, repo = stem.split("__", 1)          # 按首个 __ 切分：仓名可含 __（swesmith 教训）
        if repo != repo.rstrip(". "):              # 尾点/尾空格仓名：Windows 建目录被吞（与 build_site hostile 同步，跨仓不 import）
            hostile += 1; continue
        dst = os.path.join(out_dir, "p", owner, repo, "index.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(os.path.join(src_dir, f)):
            n += 1; continue                       # 增量：目标不旧于源就跳过
        shutil.copyfile(os.path.join(src_dir, f), dst); n += 1
    print(f"OK cards: {n} 张卡 -> dist/p/owner/repo/index.html（物理干净 URL，增量拷贝）"
          + (f"；跳过 {hostile} 个 Windows 敌对仓名（站点不部署）" if hostile else ""))
    return n
