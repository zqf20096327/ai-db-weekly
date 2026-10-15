# -*- coding: utf-8 -*-
"""AI 项目对比生成器（构建期离线运行，产物固化进站点数据）。

对指定的项目组合：提取双方 README 证据 + 站内信号 → 调用 LLM 生成
「怎么选」对比解读 → 合并写入 data/comparisons.js（页面按 fns 排序键匹配）。

用法:
  python build/ai_compare.py --collect-dir D:/dbhub_collect --out . --dry-run
  DBHUB_AI_KEY=xxx python build/ai_compare.py            # 实际调用（默认智谱 GLM）

组合来源:
  data/compare_pairs.json —— [{"fns": ["a/b", "c/d"]}, ...]（不存在时自动
  推荐热门组合：同库同类别 Star Top2-3）

已有产物按 key 保留（增量生成，不重复花钱）；--force 全部重生成。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODEL = "glm-4.6"
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

PROMPT = """你是数据库工具选型顾问。基于下面的两个项目的事实材料（README 摘录 + 数据信号），
写一份中立的中文对比解读，帮助用户选型。禁止编造材料中没有的事实，禁止营销腔。

项目材料：
{materials}

输出严格 JSON（不要 markdown 代码块）：
{{
 "title": "对比标题（观点式，<=20字）",
 "verdict": "一句话总结怎么选（<=60字）",
 "sections": [
   {{"h": "小节标题（如：定位差异/核心能力/生态与维护）", "text": "100-180字分析，必须引用材料中的具体事实"}},
   ...共3-4节
 ],
 "picks": [
   {{"scene": "场景A（如：超大库的备份）", "pick": "项目名", "why": "理由（<=40字）"}},
   ...3条
 ]
}}"""


def load_pool(out_dir):
    src = open(os.path.join(out_dir, "data", "pool.js"), encoding="utf-8").read()
    return json.loads(re.search(r"window\.POOL=(\[.*?\]);\n", src, re.S).group(1))


def readme_head(collect_dir, fn, n=3500):
    path = os.path.join(collect_dir, "data", "readmes",
                        fn.replace("/", "__") + ".md")
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            txt = f.read(n * 2)
    except OSError:
        return ""
    txt = re.sub(r"(!\[[^\]]*\]\([^)]*\)|<[^>]+>|\[|\]|#{1,6} |\*{1,3})", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()[:n]


def material(fn, r, collect_dir):
    I = dict(FN=0, DESC=1, LANG=2, ST=3, CAT=7, AIK=9, O=10, C7=14, RV=16,
             RD=17, SN=18, SW=19, CT=20, G7=21, LIC=23, DBS=6, CR=12, ARC=25)
    return (f"### {fn}\n描述: {r[I['DESC']]}\n类别: {r[I['CAT']]} | 语言: {r[I['LANG']]} | "
            f"Star: {r[I['ST']]} | 本周增星: {r[I['G7']]} | 7天提交: {r[I['C7']]} | "
            f"贡献者: {r[I['CT']]} | 最新发版: {r[I['RV']]}({r[I['RD']]}天前) | "
            f"许可证: {r[I['LIC']]} | 支持库: {','.join(r[I['DBS']])} | "
            f"官方: {'是' if r[I['O']] else '否'} | 归档: {'是' if r[I['ARC']] else '否'} | "
            f"安全通告: {r[I['SN']]}条(最高{r[I['SW']]}) | 创建: {r[I['CR']]}\n"
            f"README 摘录: {readme_head(collect_dir, fn)}")


def call_llm(prompt, key):
    body = json.dumps({"model": MODEL, "messages": [
        {"role": "user", "content": prompt}], "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        txt = json.loads(resp.read().decode())["choices"][0]["message"]["content"]
    txt = re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip()
    return json.loads(txt)


def suggest_pairs(pool):
    """自动推荐组合：同库同工具类别（排除应用/其他）、Star Top2-3、总 Star≥2000。"""
    TOOL_CATS = {"内核/引擎", "安全/审计", "测试/质量", "备份", "监控", "高可用", "迁移",
                 "建模/设计", "连接/代理", "开发库", "管理", "平台"}
    groups = {}
    for r in pool:
        if not r[5] or r[7] not in TOOL_CATS:
            continue
        for db in (r[6] or [r[5]]):
            groups.setdefault((db, r[7]), []).append(r)
    pairs = []
    for (db, cat), rs in groups.items():
        rs.sort(key=lambda x: -x[3])
        top = [r for r in rs[:3] if r[3] >= 300]
        if len(top) >= 2 and sum(r[3] for r in top) >= 2000:
            pairs.append({"fns": [r[0] for r in top], "hint": f"{db}·{cat}",
                          "_w": sum(r[3] for r in top)})
    pairs.sort(key=lambda p: -p["_w"])
    return [{"fns": p["fns"], "hint": p["hint"]} for p in pairs[:30]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect-dir", default="D:/dbhub_collect")
    ap.add_argument("--out", default=".")
    ap.add_argument("--pairs", default="data/compare_pairs.json")
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pool = load_pool(args.out)
    byfn = {r[0]: r for r in pool}
    if os.path.isfile(args.pairs):
        pairs = json.load(open(args.pairs, encoding="utf-8"))
        print(f"pairs: {len(pairs)} (from {args.pairs})")
    else:
        pairs = suggest_pairs(pool)
        print(f"pairs: {len(pairs)} (auto-suggested)")

    out_path = os.path.join(args.out, "data", "comparisons.js")
    results = {}
    if os.path.isfile(out_path) and not args.force:
        old = open(out_path, encoding="utf-8").read()
        m = re.search(r"window\.COMPARE=(\{.*\});?\s*$", old, re.S)
        if m:
            results = json.loads(m.group(1))
            print(f"existing: {len(results)} (kept, incremental)")

    key = os.environ.get("DBHUB_AI_KEY", "")
    n_ok = n_skip = 0
    for p in pairs[:args.max]:
        fns = sorted(p["fns"])
        k = "|".join(fns)
        if k in results and not args.force:
            n_skip += 1
            continue
        recs = [byfn.get(f) for f in fns]
        if any(r is None for r in recs):
            print("  skip (missing in pool):", k)
            continue
        mats = "\n\n".join(material(f, r, args.collect_dir)
                           for f, r in zip(fns, recs))
        prompt = PROMPT.format(materials=mats)
        if args.dry_run:
            print(f"\n== DRY {k} ({p.get('hint','')}), prompt {len(prompt)} chars ==")
            print(prompt[:400] + " …")
            continue
        if not key:
            print("  no DBHUB_AI_KEY; stop. 已有产物保留。")
            break
        try:
            res = call_llm(prompt, key)
            results[k] = res
            n_ok += 1
            print("  ok:", k, "->", res.get("title", ""))
        except Exception as e:
            print("  FAIL:", k, e)
        time.sleep(1)

    if not args.dry_run and n_ok:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("/* AI 构建期生成的对比解读（build/ai_compare.py 产物） */\n")
            f.write("window.COMPARE=")
            json.dump(results, f, ensure_ascii=False, separators=(",", ":"))
            f.write(";\n")
        print(f"wrote {out_path}: {len(results)} entries ({n_ok} new, {n_skip} kept)")
    elif args.dry_run:
        print("\n(dry-run 完成，未写文件)")


if __name__ == "__main__":
    main()
