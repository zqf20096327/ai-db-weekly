# -*- coding: utf-8 -*-
"""assets.py -- 设计资产进站（P7.13 返工：周刊族页面恢复旧版排版，引用仓内 assets/）

只搬样式资产：app.css（设计令牌与组件）+ fonts/（Inter 变量字体）+ 二维码图。
app.js 绝不进站（旧交互抽屉/搜索/主题切换是 JS 增强，静态页不需要，也避免误依赖 pool.js）。
"""
import os, shutil
import common as C

COPY = ["app.css", "fonts", "qr-wechat.jpg", "qr-site.png"]

def copy_assets(cfg, out_dir):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # dbhub_page 根
    src_root = os.path.join(here, "assets")
    dst_root = os.path.join(out_dir, "assets")
    n = 0
    for item in COPY:
        s = os.path.join(src_root, item)
        d = os.path.join(dst_root, item)
        if os.path.isdir(s):
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d); n += 1
        elif os.path.isfile(s):
            os.makedirs(dst_root, exist_ok=True)
            shutil.copyfile(s, d); n += 1
    assert not os.path.exists(os.path.join(out_dir, "assets", "app.js")), "app.js 混进 dist"
    print(f"OK assets: {n} 项设计资产进站（app.css/fonts/二维码，app.js 排除）")
    return n

if __name__ == "__main__":
    cfg = C.load_config()
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    copy_assets(cfg, out_dir)
