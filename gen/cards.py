# -*- coding: utf-8 -*-
"""cards.py -- 活跃卡进站：cards/{owner}__{repo}.html -> dist/p/{owner}/{repo}/index.html

解耦决策（2026-11-16）：不用 _redirects 做 /p/{fn}/ -> cards/ 映射，而是物理目录布局
p/owner/repo/index.html——URL 天然成立，任何静态托管（CF Pages/GH Pages/任意 nginx）零配置，
平台适配层因此退化为可选。只拷 HTML 不拷 JSON（站上不需要卡片底稿）。

P9.7 部署口径 A（用户裁定 11-21）：部署清单 = site/data/all-*.json 的 fn 全集（build_site 已按
「归属过 dbs 非空」过滤）。周刊活跃集同源（weekly_pages.active_fns 读同一批分片），未部署卡在
刊内自动降级纯文本，永不产站内 404——因此无需白名单，一条规则：活跃集=部署集。
"""
import glob, io, json, os, shutil
import common as C

def _deploy_set(cfg):
    """部署文件名集（正向转换 fn->owner__repo.html 比对；勿反向解析——仓名含 __ 时往返有歧义）。"""
    files = set()
    for f in glob.glob(os.path.join(cfg["data_root"], "data", "all-*.json")):
        for it in json.load(io.open(f, encoding="utf-8"))["items"]:
            files.add(it["fn"].lower().replace("/", "__") + ".html")
    return files

def copy_cards(cfg, out_dir):
    src_dir = cfg["cards_root"]; n = 0; hostile = 0; unattr = 0
    deploy = _deploy_set(cfg)
    live = set()                                    # 本次部署清单（owner, repo）——清孤儿的对照集
    for f in os.listdir(src_dir):
        if not f.endswith(".html"): continue
        owner, repo = f[:-5].split("__", 1)        # 按首个 __ 切分：仓名可含 __（swesmith 教训）
        if repo != repo.rstrip(". "):              # 尾点/尾空格仓名：Windows 建目录被吞（与 build_site hostile 同步，跨仓不 import）
            hostile += 1; continue
        if f not in deploy:                        # P9.7：未归属不部署（源卡保留，归属补证自动回站）
            unattr += 1; continue
        live.add((owner, repo))
        dst = os.path.join(out_dir, "p", owner, repo, "index.html")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(os.path.join(src_dir, f)):
            n += 1; continue                       # 增量：目标不旧于源就跳过
        shutil.copyfile(os.path.join(src_dir, f), dst); n += 1
    removed = 0                                    # P9.5 清孤儿：日更归档/出池/口径剔除后 dist 残留旧页（verify「盘上多出」在此拦）
    p_root = os.path.join(out_dir, "p")
    if os.path.isdir(p_root):
        for owner in os.listdir(p_root):
            od = os.path.join(p_root, owner)
            if not os.path.isdir(od): continue
            for repo in os.listdir(od):
                if (owner, repo) not in live:
                    shutil.rmtree(os.path.join(od, repo), ignore_errors=True); removed += 1
            if not os.listdir(od): os.rmdir(od)   # 空 owner 目录顺手清
    print(f"OK cards: {n} 张卡 -> dist/p/owner/repo/index.html（物理干净 URL，增量拷贝）"
          + (f"；跳过敌对仓名 {hostile} / 未归属 {unattr}" if (hostile or unattr) else "")
          + (f"；清孤儿 {removed} 张（归档/出池/口径剔除旧页）" if removed else ""))
    return n
