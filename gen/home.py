# -*- coding: utf-8 -*-
"""home.py -- 首页（P7.3/P7.13）：最新一期周刊整版静态直出，排版=旧版 index.html 原样。

P7.13 用户令「严格按照之前排版」：撤掉 P7.3 自创的门面板块（Top10/入口矩阵），
首页回到旧版单刊版面（hero + 一句话情报 + 深读卡 + 速览四卡），版面渲染复用 weekly_pages。
与旧版的差别只有三处（皆为死链修复，视觉不变）：
  1. CTA「设置我的关注」->「浏览 N 个项目档案」（mystack 已随 pool.js 退役）；
  2. 深读卡点击=原卡内 <details> 展开全文（旧为 JS 抽屉）；
  3. data-fn 假链 -> /p/ 真卡链。
"""
import io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import weekly_pages as W

def gen_home(cfg, ct, out_dir):
    issues = W.load_weekly()
    nos = sorted(issues)
    d = issues[nos[-1]]
    act = W.active_fns(cfg)
    cnt = {"j_link": 0, "j_drop": 0, "c_link": 0, "g_link": 0}
    p = os.path.join(out_dir, "index.html")
    C.dump(p, C.page_legacy(cfg, f"数据库开源生态周刊 · 第 {d['no']} 期", W.issue_desc(d),
                            ct["base"] + "/", W.issue_html(d, act, cfg, cnt, nos, home=True),
                            "/", W.EXTRA_CSS))
    t = io.open(p, encoding="utf-8").read()
    txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[\s\S]*?</\1>", "", t))
    n = len(" ".join(txt.split()))
    assert n >= 1500, f"首页正文仅 {n} 字（<1500）"
    assert "data/weekly.js" not in t and "app.js" not in t, "首页仍引用旧 JS"
    assert 'class="hero issue-hero"' in t and "本期深读" in t and "本周速览" in t, "首页旧版版面板块缺失"
    print(f"OK home: 首页=第 {d['no']} 期整版（旧版排版静态直出），正文 {n} 字")
    return n

if __name__ == "__main__":
    cfg = C.load_config(); ct = C.load_contract(cfg)
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", cfg["out"]))
    gen_home(cfg, ct, out_dir)
