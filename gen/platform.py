# -*- coding: utf-8 -*-
"""platform.py -- 平台适配层（当前两平台差异只剩 404/缓存头，卡 URL 已物理化无需 _redirects）

换托管 = 在这里加一个 elif 分支，其余模块零改动。
"""
import os
import common as C

def emit(out_dir, platform):
    """产出平台文件：404 页全平台通用；_headers 仅 Cloudflare Pages 生效（GH Pages 自动忽略）。"""
    cfg = C.load_config()
    body = ('<h1>404 · 页面不存在</h1>\n<p class="sub">这个地址没有内容。可以去 '
            '<a href="/projects/">项目库</a> 或 <a href="/">首页</a> 看看。</p>')
    C.dump(os.path.join(out_dir, "404.html"),
           C.page(cfg, "404 · 数据库开源生态", "页面不存在", None, body))
    if platform == "cf":
        C.dump(os.path.join(out_dir, "_headers"),
               "/assets/*\n  Cache-Control: public, max-age=604800\n/p/*\n  Cache-Control: public, max-age=3600\n")
        print("OK platform[cf]: 404.html + _headers（静态资产 7 天 / 卡页 1 小时缓存）")
    elif platform == "gh":
        print("OK platform[gh]: 404.html（GH Pages 原生支持）")
    else:
        raise SystemExit(f"未知平台 {platform}（cf | gh）")
