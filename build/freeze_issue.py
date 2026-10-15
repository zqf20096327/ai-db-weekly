#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周刊冻结与选题日历（2026-10-03 定案：三席轮换制 + 冻结存储）。

用法：
  python build/freeze_issue.py --plan 2                 # 第 2 期选题日历（轮值/候选/事件信号/AI 保底/冷却/速览轮换）
  python build/freeze_issue.py --freeze 1               # 读 weekly/issues/issue-001.json + data/pool.js
                                                         # 冻结数据段 → data/weekly.js（按期号覆盖，幂等可重跑）
  python build/freeze_issue.py --freeze 2 --date 2026-10-06

规则（与定案一致）：
  深读三席 = 类别席（13 周轮盘，弱类别 <8 项不入盘；当前仅「其他」被排除）
           + 板块席（单期国际 / 双期国产主打，硬配额：≥1 篇归属该板块）
           + 事件席（四级优先序：千星停维归档 > 官方重大发版 > critical 新披露 > 增星≥500；
             全落空时回落类别席候选第一名，事件席永不开天窗）
  AI 保底：连续 4 期内至少 1 篇 sec=ai（freeze 缺席则警告）
  冷却：同一项目 90 天内不重复深读（违反则警告）
  速览轮换：单期 增星榜=全站总榜 + 版本动态=官方优先全类别；双期 增星榜=国产榜 + 版本动态=内核优先
存储：data/weekly.js 由本脚本独占写入（对象键幂等）；build/build.py 只产 pool.js/detail.js，互不相扰。
往期数据段冻结不重算（论据冻结、探索实时：文章内嵌数字为发刊快照，页面点开项目看到的才是现状）。
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEEKLY_JS = ROOT / "data" / "weekly.js"
DRAFTS = ROOT / "weekly" / "issues"

ANCHOR = date(2026, 9, 29)          # 第 1 期（样刊）
WHEEL = ["备份", "开发库", "内核/引擎", "监控", "建模/设计", "测试/质量",
         "高可用", "连接/代理", "迁移", "安全/审计", "平台", "应用", "管理"]  # 管理=轮盘末位（期1 已写 2 篇客户端，冷启动避让）
CN_AT = 7                            # dbOrder[7:] = 国产 10 库
TOOL_HEAD = 12                       # CATS.slice(0,12) = 功能类（其他不参与）
SEV_CN = {"critical": "严重", "high": "高危", "moderate": "中危", "low": "低危"}

# 与 app.js 的 I 索引表严格一致（勿单方面改动）
I = dict(FN=0, DESC=1, LANG=2, ST=3, FK=4, DB=5, DBS=6, CAT=7, CC=8, AIK=9, O=10,
         SEC=11, CR=12, PU=13, C7=14, C90=15, RV=16, RD=17, SN=18, SW=19, CT=20,
         G7=21, EV=22, LIC=23, HP=24, ARC=25, SL=26, RP=27, STAT=28, ECO=29, PF=30, CS=31)


# ---------- 基础工具（镜像 app.js，口径勿漂移） ----------
def fmtk(n):
    n = n or 0
    if abs(n) >= 10000:
        return f"{n / 1000:.0f}k"
    if abs(n) >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def act(r):
    a = (r[I["C7"]] or 0) * 2 + (15 if (r[I["RD"]] is not None and r[I["RD"]] <= 30) else 0) \
        + min(20, (r[I["CT"]] or 0) // 20)
    return min(100, a)


def dbs_of(r):
    d = r[I["DBS"]]
    if d:
        return d
    return [r[I["DB"]]] if r[I["DB"]] else []


def isna(r):
    return not r[I["DB"]]


def snap_minus(snap, days):
    d = date(int(snap[:4]), int(snap[4:6]), int(snap[6:8])) - timedelta(days=days)
    return d.isoformat()


def load_pool():
    src = (ROOT / "data" / "pool.js").read_text(encoding="utf-8")
    i = src.index("window.POOL=")
    meta = json.loads(src[len("window.META="):i].strip().rstrip(";"))
    pool = json.loads(src[i + len("window.POOL="):].strip().rstrip(";"))
    return meta, pool


def load_weekly():
    if not WEEKLY_JS.exists():
        return {}
    out = {}
    for m in re.finditer(r"WEEKLY\[(\d+)\] = (\{.*\});\n", WEEKLY_JS.read_text(encoding="utf-8")):
        out[int(m.group(1))] = json.loads(m.group(2))
    return out


def save_weekly(no, rec):
    line = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
    block = f"/* 第 {no} 期 · {rec['date']} · 冻结于快照 {rec['snap']} */\nWEEKLY[{no}] = {line};\n"
    if WEEKLY_JS.exists():
        txt = WEEKLY_JS.read_text(encoding="utf-8")
        pat = re.compile(rf"/\* 第 {no} 期 .*?\*/\nWEEKLY\[{no}\] = \{{.*\}};\n")
        if pat.search(txt):
            txt = pat.sub(lambda _: block, txt)
        else:
            txt = txt.rstrip("\n") + "\n" + block
    else:
        txt = "window.WEEKLY = window.WEEKLY || {};\n" + block
    WEEKLY_JS.write_text(txt, encoding="utf-8", newline="\n")


# ---------- 当期数据统计（镜像 index.html 旧口径） ----------
def stats(meta, pool):
    cut7 = snap_minus(meta["snap"], 7)
    new_cut = snap_minus(meta["snap"], 45)
    tools = set(meta["catOrder"][:TOOL_HEAD])
    cn = set(meta["dbOrder"][CN_AT:])

    sec_e = [r for r in pool if r[I["SL"]] and r[I["SL"]] >= cut7
             and r[I["SW"]] in ("critical", "high")]
    sec_e.sort(key=lambda r: -r[I["ST"]])
    rel_e = [r for r in pool if r[I["RP"]] and r[I["RP"]] >= cut7 and r[I["RV"]]]
    rel_e.sort(key=lambda r: (-(r[I["O"]] or 0), -r[I["ST"]]))
    topg = [r for r in pool if (r[I["G7"]] or 0) > 0]
    topg.sort(key=lambda r: (-(r[I["G7"]] or 0), -r[I["ST"]]))
    topg_cn = [r for r in topg if set(dbs_of(r)) & cn]
    news = [r for r in pool if not isna(r) and r[I["CAT"]] in tools and (r[I["CR"]] or "") >= new_cut]
    news.sort(key=lambda r: -r[I["ST"]])
    stales = [r for r in pool if not isna(r) and r[I["CAT"]] in tools
              and (((r[I["ST"]] or 0) >= 1000 and r[I["C90"]] == 0) or r[I["ARC"]])]
    stales.sort(key=lambda r: -r[I["ST"]])
    ai_n = sum(1 for r in pool if r[I["AIK"]])
    ai_mcp = sum(1 for r in pool if r[I["AIK"]] and "mcp" in r[I["AIK"]].split(","))
    stale_n = len(stales)
    return dict(cut7=cut7, new_cut=new_cut, cn=cn, tools=tools, sec=sec_e, rel=rel_e,
                topg=topg, topg_cn=topg_cn, news=news, stales=stales,
                ai_n=ai_n, ai_mcp=ai_mcp, stale_n=stale_n)


# ---------- 记录组装 ----------
def sev_chip(sw):
    return f'<span class="sev">{SEV_CN.get(sw, sw)}</span>'


def build_record(no, pub_date, draft, meta, pool, st):
    cn = st["cn"]
    by_fn = {r[I["FN"]]: r for r in pool}
    short = lambda fn: fn.split("/")[-1]

    deep = []
    for a in draft["deep"]:
        r = by_fn.get(a["fn"])
        nums, panel = [], []
        if r:
            g7 = r[I["G7"]]
            nums = [["Star", fmtk(r[I["ST"]])],
                    ["本周", ("+" + str(g7)) if (g7 or 0) > 0 else "±0"],
                    ["c/7天", "—" if r[I["C7"]] is None else str(r[I["C7"]])],
                    ["贡献者", "—" if r[I["CT"]] is None else fmtk(r[I["CT"]])]]
            panel = [["Star", fmtk(r[I["ST"]])],
                     ["本周增星", ("+" + str(g7)) if (g7 or 0) > 0 else "—"],
                     ["7天提交", "—" if r[I["C7"]] is None else str(r[I["C7"]])],
                     ["90天提交", "—" if r[I["C90"]] is None else str(r[I["C90"]])],
                     ["贡献者", "—" if r[I["CT"]] is None else fmtk(r[I["CT"]])],
                     ["最新发版", r[I["RV"]] or "—"],
                     ["许可证", r[I["LIC"]] or "—"],
                     ["活跃度", f"{act(r)}/100"]]
        deep.append({**a, "nums": nums, "panel": panel})

    # 导读三行：草稿提供手写版则优先（编辑口径），否则模板自动生成
    total = meta.get("total") or len(pool)
    if draft.get("lede"):
        lede = draft["lede"]
    else:
        t1, t2 = st["topg"][0], (st["topg"][1] if len(st["topg"]) > 1 else None)
        lead_html = (f'本周增速冠军 <a href="#" class="jump" data-fn="{t1[I["FN"]]}">{short(t1[I["FN"]])}</a>'
                     f'（周 +{t1[I["G7"]]}★）'
                     + (f'，次席 <a href="#" class="jump" data-fn="{t2[I["FN"]]}">{short(t2[I["FN"]])}</a>（+{t2[I["G7"]]}★）' if t2 else "")
                     + "领跑全站")
        sec_top = st["sec"][0] if st["sec"] else None
        risk_html = (f'近 7 天<b>新披露</b>高危通告 {len(st["sec"])} 起'
                     + (f'，{short(sec_top[I["FN"]])} 影响最大' if sec_top else "")
                     + f'；{st["stale_n"]:,} 个千星级工具停维或归档')
        lede = [["亮点", lead_html], ["风险", risk_html],
                ["规模", f"全站收录 {total:,} 个项目，17 库生态，每周更新一次"]]

    # 数字条 6 项
    nums = [["收录项目", f"{total:,}", "projects.html"],
            ["新披露通告(7天)", str(len(st["sec"])), "projects.html#sec=hi"],
            ["发版项目(7天)", str(len(st["rel"])), "projects.html#sort=rel"],
            ["停维预警", str(st["stale_n"]), "projects.html#mst=gone"],
            ["AI 工具", str(st["ai_n"]), "projects.html#ai=ai"],
            ["新项目(45天)", str(len(st["news"])), "projects.html#sort=new"]]

    # 速览四卡（轮换：单期全站+官方优先；双期国产榜+内核优先）
    gain_list = st["topg"] if no % 2 == 1 else st["topg_cn"]
    gain_hint = ("本周 · 全站总榜" if no % 2 == 1 else "本周 · 国产榜") \
                + f" · 基线 {meta['growthBase'][4:]}→{meta['snap'][4:]}"
    rel_list = st["rel"]
    if no % 2 == 0:
        rel_list = sorted(rel_list, key=lambda r: (0 if r[I["CAT"]] == "内核/引擎" else 1,
                                                   -(r[I["O"]] or 0), -r[I["ST"]]))
    rel_hint = "近 7 天发版 · 官方优先" if no % 2 == 1 else "近 7 天发版 · 内核优先"

    def rel_meta(r):
        off = '<span class="tag off">官方</span> ' if r[I["O"]] else ""
        return f'{off}{str(r[I["RV"]])[:18]} <span class="muted">· {r[I["RP"]]}</span> · ★{fmtk(r[I["ST"]])}'

    risk_rows = ([{"fn": r[I["FN"]], "chip": sev_chip(r[I["SW"]]),
                   "meta": f'{r[I["SL"]]} 新披露 · ★{fmtk(r[I["ST"]])}'} for r in st["sec"][:3]]
                 + [{"fn": r[I["FN"]],
                     "chip": f'<span class="bdg arc">归档</span>' if r[I["ARC"]] else '<span class="bdg stale">停维</span>',
                     "meta": f'{"已标记归档" if r[I["ARC"]] else "90 天零提交"} · ★{fmtk(r[I["ST"]])}'} for r in st["stales"][:3]])
    glance = {
        "risk": {"hint": f"本周新披露 {len(st['sec'])} 起 · 停维/归档 {st['stale_n']}", "rows": risk_rows[:6]},
        "rel": {"hint": rel_hint,
                "rows": [{"fn": r[I["FN"]], "meta": rel_meta(r)} for r in rel_list[:5]]},
        "gain": {"hint": gain_hint,
                 "rows": [{"fn": r[I["FN"]], "meta": f'<span class="g7">+{r[I["G7"]]}</span> · ★{fmtk(r[I["ST"]])}'}
                          for r in gain_list[:3]]},
        "newb": {"hint": "创建 ≤45 天 · 已归属",
                 "rows": [{"fn": r[I["FN"]],
                           "meta": f'★{fmtk(r[I["ST"]])} · <span class="tag gray">{r[I["CAT"]]}</span> · {r[I["CR"]]}'
                           } for r in st["news"][:3]]},
    }

    # 一句话情报 6 条
    g1 = st["topg"][0] if st["topg"] else None
    kernel = next((r for r in st["rel"] if r[I["CAT"]] == "内核/引擎" and r[I["O"]]), None)
    arc = sorted([r for r in pool if r[I["ARC"]]], key=lambda r: -r[I["ST"]])
    arc1 = arc[0] if arc else None
    lines = []
    if g1:
        lines.append(f'<code>{g1[I["FN"]]}</code> 本周 <b class="g7">+{g1[I["G7"]]}</b> 星，'
                     f'全站第一（现 ★{fmtk(g1[I["ST"]])}）')
    if kernel:
        lines.append(f'内核发版：<code>{kernel[I["FN"]]}</code> 发布 <b>{kernel[I["RV"]]}</b>（{kernel[I["RP"]]}）')
    if arc1:
        lines.append(f'<code>{arc1[I["FN"]]}</code>（★{fmtk(arc1[I["ST"]])}）已标记归档，选型避开')
    lines.append(f'近 7 天新披露安全通告 <b>{len(st["sec"])}</b> 起、发版 <b>{len(st["rel"])}</b> 个项目')
    lines.append(f'AI 渗透：在册 AI 相关工具 {st["ai_n"]} 个，其中 MCP 类 {st["ai_mcp"]} 个')
    lines.append(f'45 天窗口内新入库且已归属的工具 <b>{len(st["news"])}</b> 个')

    theme = draft.get("theme") or {"cat": WHEEL[(no - 2) % len(WHEEL)], "side": "intl" if no % 2 == 1 else "cn"}
    return {
        "no": no, "date": pub_date,
        "snap": meta["snap"], "built": meta.get("built", "?"),
        "growthBase": meta.get("growthBase", "?"), "g7cov": meta.get("g7cov", 0),
        "total": total, "theme": theme, "lede": lede, "deep": deep,
        "nums": nums, "glance": glance, "onelines": lines,
    }


# ---------- 校验（防撞车 / 保底 / sanity） ----------
def check(no, rec, weekly):
    warns = []
    try:
        cur = date.fromisoformat(rec["date"])
    except ValueError:
        cur = ANCHOR + timedelta(days=7 * (no - 1))
    fns = [d["fn"] for d in rec["deep"]]
    if len(set(fns)) != len(fns):
        warns.append("本期深读出现重复项目")
    for n, r in weekly.items():
        if n == no:
            continue
        try:
            other = date.fromisoformat(r["date"])
        except ValueError:
            continue
        if abs((other - cur).days) < 90:
            for d in r.get("deep", []):
                if d["fn"] in fns:
                    warns.append(f"冷却违规：{d['fn']} 与第 {n} 期（{r['date']}）间隔不足 90 天")
    window = [n for n in range(max(1, no - 3), no + 1)]
    if not any(d.get("sec") == "ai"
               for n in window for d in (weekly.get(n, {}).get("deep", []) if n != no else rec["deep"])):
        warns.append(f"AI 保底：第 {window[0]}–{no} 期均无 AI×数据库 深读，本期应补 1 篇")
    prev = weekly.get(max([n for n in weekly if n < no], default=0), None) if weekly else None
    if prev and prev.get("total") and rec["total"]:
        drift = abs(rec["total"] - prev["total"]) / prev["total"]
        if drift > 0.05:
            warns.append(f"sanity：收录总数较上期变动 {drift:.1%}（{prev['total']} → {rec['total']}），确认快照无误")
    return warns


# ---------- 选题日历 ----------
def plan(no, meta, pool, st, weekly):
    pub = ANCHOR + timedelta(days=7 * (no - 1))
    cat = WHEEL[(no - 2) % len(WHEEL)]
    side = "intl" if no % 2 == 1 else "cn"
    side_dbs = set(meta["dbOrder"][:CN_AT]) if side == "intl" else set(meta["dbOrder"][CN_AT:])
    cand = sorted([r for r in pool if r[I["CAT"]] == cat and not isna(r)],
                  key=lambda r: (-(r[I["G7"]] or 0), -r[I["ST"]]))[:3]
    side_cand = sorted([r for r in pool if set(dbs_of(r)) & side_dbs],
                       key=lambda r: (-(r[I["G7"]] or 0), -r[I["ST"]]))[:3]
    ev = []
    if st["stales"]:
        r = st["stales"][0]
        ev.append(f"①千星停维/归档：{r[I['FN']]}（★{fmtk(r[I['ST']])}）")
    off_rel = [r for r in st["rel"] if r[I["O"]]]
    if off_rel:
        r = off_rel[0]
        ev.append(f"②官方发版：{r[I['FN']]} {r[I['RV']]}")
    crit = [r for r in st["sec"] if r[I["SW"]] == "critical"]
    if crit:
        ev.append(f"③critical 新披露：{crit[0][I['FN']]}")
    big = [r for r in st["topg"] if (r[I["G7"]] or 0) >= 500]
    if big:
        ev.append(f"④增星≥500：{big[0][I['FN']]}（+{big[0][I['G7']]}）")
    window = [n for n in range(max(1, no - 3), no + 1)]
    has_ai = any(d.get("sec") == "ai" for n in window if n != no
                 for d in weekly.get(n, {}).get("deep", []))
    cooldown = []
    for n, r in sorted(weekly.items()):
        try:
            d0 = date.fromisoformat(r["date"])
        except ValueError:
            continue
        if abs((d0 - pub).days) < 90:
            cooldown += [f"{d['fn']}（第 {n} 期）" for d in r.get("deep", [])]
    print(f"━━ 第 {no} 期 选题日历 · 预计 {pub.isoformat()}（周{'一二三四五六日'[pub.weekday()]}）")
    print(f"类别席（轮盘 {(no - 2) % len(WHEEL) + 1}/{len(WHEEL)}）：{cat}")
    print("  候选（按本周增星）：" + ("、".join(f"{r[I['FN']]} ★{fmtk(r[I['ST']])}" for r in cand) or "无候选！"))
    print(f"板块席（硬配额，主打 {'国产' if side == 'cn' else '国际'}）："
          + ("、".join(f"{r[I['FN']]} ★{fmtk(r[I['ST']])}" for r in side_cand) or "无候选！"))
    print("事件席（四级优先序，全落空回落类别席候选第一名）：")
    for e in ev or ["  本周无显著信号 → 回落类别席"]:
        print(f"  {e}")
    print(f"AI 保底：{'近 3 期已有 AI 深读，本期无需保底' if has_ai else '近 3 期无 AI 深读，本期事件/板块席应给 AI 1 篇'}")
    print(f"冷却名单（90 天内已写，勿重复）：{('、'.join(cooldown) or '无')}")
    rot = "增星榜=全站总榜 · 版本动态=官方优先全类别" if no % 2 == 1 else "增星榜=国产榜 · 版本动态=内核优先"
    print(f"速览轮换：{rot}")
    print(f"流程：写 weekly/issues/issue-{no:03d}.json（三席各 ≥1 篇，字段同 issue-001）"
          f" → python build/freeze_issue.py --freeze {no} --date {pub.isoformat()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=int, metavar="N", help="第 N 期选题日历")
    ap.add_argument("--freeze", type=int, metavar="N", help="冻结第 N 期")
    ap.add_argument("--date", help="覆盖发刊日期（默认锚点+7×(N-1)）")
    args = ap.parse_args()
    if not args.plan and not args.freeze:
        ap.print_help()
        sys.exit(1)
    meta, pool = load_pool()
    weekly = load_weekly()
    if args.plan:
        plan(args.plan, meta, pool, stats(meta, pool), weekly)
        return
    no = args.freeze
    pub = args.date or (ANCHOR + timedelta(days=7 * (no - 1))).isoformat()
    draft_path = DRAFTS / f"issue-{no:03d}.json"
    if not draft_path.exists():
        sys.exit(f"草稿不存在：{draft_path}（先按 --plan {no} 的日历写稿）")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    if draft.get("no", no) != no:
        sys.exit(f"草稿期号 {draft.get('no')} 与 --freeze {no} 不一致")
    rec = build_record(no, pub, draft, meta, pool, stats(meta, pool))
    if not rec["total"]:
        sys.exit("sanity 拦截：收录总数为 0，pool.js 疑似异常，已拒绝写入")
    save_weekly(no, rec)
    print(f"✓ 第 {no} 期已冻结 → data/weekly.js（快照 {rec['snap']}，幂等可重跑覆盖）")
    for w in check(no, rec, load_weekly()):
        print(f"⚠ {w}")


if __name__ == "__main__":
    main()
