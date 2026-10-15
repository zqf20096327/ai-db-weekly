# -*- coding: utf-8 -*-
"""自测套件：单元行为 + 输出契约 + 数据一致性（零改动生产数据）。

三层：
  A. 单元——classify / interp / taxonomy / sources 纯函数分支全覆盖
  B. 契约——对已产出的 data/pool.js / detail.js 断言前端消费契约
     （32 列结构、排序、枚举值域、META 字段全集、detail 全量覆盖）
  C. 一致性——页面产物与 dbhub_collect 原始数据对账
     （总量=池去重数、override 生效/未命中、db_cnt 加总闭合）

用法:
  python build/selftest.py [--collect-dir D:/dbhub_collect] [--page-dir .]
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import classify
import interp
import sources
import taxonomy

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, True, ""))
        print(f"  ok    {name}")
    except AssertionError as e:
        RESULTS.append((name, False, str(e)))
        print(f"  FAIL  {name}: {e}")
    except Exception as e:                       # 非断言异常=测试自身出错，更严
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


# ================================================================ A. 单元
def test_classify():
    watch2db = {"postgres/postgres": "PostgreSQL"}
    org2db = {"mysql": "MySQL", "pingcap": "TiDB"}

    cat, conf, ev = classify.classify(
        {"full_name": "postgres/postgres", "description": "", "topics": []},
        watch2db, org2db)
    assert cat == "内核/引擎" and conf == 2 and ev == "官方内核/白名单", (cat, conf, ev)

    cat, conf, ev = classify.classify(
        {"full_name": "mysql/mysql-server", "owner": "mysql",
         "description": "", "topics": []}, watch2db, org2db)
    assert cat == "内核/引擎" and conf == 2, (cat, conf)          # 官方+引擎命名

    cat, conf, ev = classify.classify(
        {"full_name": "a/b", "owner": "x", "description": "",
         "topics": ["ORM"]}, watch2db, org2db)
    assert cat == "开发库" and conf == 2 and ev.startswith("topic:"), (cat, conf, ev)

    cat, conf, ev = classify.classify(
        {"full_name": "a/b", "owner": "x",
         "description": "a backup tool for mysql", "topics": []},
        watch2db, org2db)
    assert cat == "备份" and conf == 1 and ev.startswith("kw:"), (cat, conf, ev)

    cat, conf, _ = classify.classify(
        {"full_name": "a/awesome-db", "owner": "x",
         "description": "awesome list of tutorials", "topics": []},
        watch2db, org2db)
    assert cat == "应用" and conf == 1, (cat, conf)

    cat, conf, ev = classify.classify(
        {"full_name": "a/zzz", "owner": "x", "description": "nothing",
         "topics": []}, watch2db, org2db)
    assert cat == "其他" and conf == 0 and ev == "", (cat, conf, ev)

    # 非官方仓引擎式命名不得判内核（须走后续规则）
    cat, _, _ = classify.classify(
        {"full_name": "someone/mysql-server", "owner": "someone",
         "description": "", "topics": []}, watch2db, org2db)
    assert cat != "内核/引擎", cat


def test_ai_flag():
    base = {"full_name": "a/b", "description": ""}
    out = classify.ai_flag(dict(base, topics=["mcp"]), ["mcp", "rag"])
    assert out == "mcp", out
    out = classify.ai_flag(dict(base, description="natural language text-to-sql tool",
                                topics=[]), ["text2sql"])
    # text2sql 关键词不在列表时不命中——ai_flag 只认传入 keywords
    assert out == "", out
    out = classify.ai_flag(dict(base, full_name="a/rag-tool", description=""),
                           ["rag"])
    assert out == "rag", out                      # 短词词边界（rag 撞 storage 不算）
    out = classify.ai_flag(dict(base, description="uses llm"), ["llm"])
    assert out == "llm", out
    out = classify.ai_flag(dict(base, description="plain tool"), ["llm"])
    assert out == "", out


def _cls(dbs, verdicts=True, **kw):
    c = {"dbs": dbs, "ai": {"flag": False, "kind": []}, "official": {"flag": False}}
    if verdicts:
        c["db_verdicts"] = [{"db": d, "rel": "support", "quote": "q", "lines": [1]}
                             for d in dbs]
    c.update(kw)
    return c


def test_interp_guardrail():
    order = taxonomy.DB_ORDER
    all17 = _cls(list(order))
    mi = interp.merge_interp({"classification": all17}, order)
    assert mi["dbs"] == [] and mi["wide_n"] == 0, (mi["dbs"], mi["wide_n"])   # 17/17 硬丢

    twelve = _cls(order[:12])
    mi = interp.merge_interp({"classification": twelve}, order)
    assert mi["dbs"] == order[:12] and mi["wide_n"] == 12       # 有证据≥10 保留+审计

    # 无证据（无 db_verdicts 字段）>9 丢——v1 防御分支
    legacy = _cls(order[:12], verdicts=False)
    mi = interp.merge_interp({"classification": legacy}, order)
    assert mi["dbs"] == [] and mi["wide_n"] == 0, mi["dbs"]

    # 无证据恰好 9 库不丢（>9 才丢）
    legacy9 = _cls(order[:9], verdicts=False)
    mi = interp.merge_interp({"classification": legacy9}, order)
    assert mi["dbs"] == order[:9], mi["dbs"]

    # 范围外库名过滤
    mixed = _cls(["PostgreSQL", "RedisDB", "Mongo"])
    mi = interp.merge_interp({"classification": mixed}, order)
    assert mi["dbs"] == ["PostgreSQL"], mi["dbs"]


def test_interp_fields():
    order = taxonomy.DB_ORDER
    entry = {
        "classification": _cls(["PostgreSQL"], cat="监控", eco="tool",
                               persona="ops", eco_why="w" * 300),
        "identity": {"one_liner": "x" * 200, "review": "r",
                     "highlights": ["h" * 200] * 5,
                     "use_cases": ["u" * 200] * 5},
        "signals": {"status": "active", "install": ["npm", "bogus", "docker"]},
        "audit": {"confidence": "high", "evidence": "e" * 300},
        "source": "readme",
    }
    entry["classification"]["cat"] = "监控"
    mi = interp.merge_interp(entry, order)
    assert mi["cat"] == "监控" and mi["conf"] == 2, (mi["cat"], mi["conf"])
    assert mi["eco"] == "tool" and mi["persona"] == "ops" and mi["status"] == "active"
    assert mi["ol"] == "x" * 80, len(mi["ol"])                    # 80 截断
    assert len(mi["hl"][0]) == 90 and len(mi["hl"]) == 3          # 90 截断/前 3
    assert mi["ins"] == ["npm", "docker"]                          # 枚举过滤
    assert mi["cg"] == "high" and mi["src"] == "readme"

    # 低置信：cat 不采用
    entry["audit"]["confidence"] = "low"
    mi = interp.merge_interp(entry, order)
    assert mi["cat"] == "" and mi["conf"] == 0, (mi["cat"], mi["conf"])
    # 枚举外的值清洗
    entry["audit"]["confidence"] = "high"
    entry["classification"]["eco"] = "whatever"
    entry["classification"]["persona"] = "who"
    entry["signals"]["status"] = "sleeping"
    mi = interp.merge_interp(entry, order)
    assert mi["eco"] == "" and mi["persona"] == "" and mi["status"] == ""

    # AI kind 映射：dba-agent→agent、other 不映射；flag 无 kind → 伞形 ai
    entry["classification"]["ai"] = {"flag": True, "kind": ["dba-agent", "other"]}
    mi = interp.merge_interp(entry, order)
    assert mi["aik"] == "agent", mi["aik"]
    entry["classification"]["ai"] = {"flag": True, "kind": []}
    mi = interp.merge_interp(entry, order)
    assert mi["aik"] == "ai", mi["aik"]
    entry["classification"]["ai"] = {"flag": False, "kind": ["rag"]}
    mi = interp.merge_interp(entry, order)
    assert mi["aik"] == "", mi["aik"]                              # flag=False 整体关

    assert interp.merge_interp(None, order) is None               # 空入参


def test_taxonomy_maps():
    profiles = [
        {"name": "PostgreSQL", "enabled": True, "aliases": ["postgres"],
         "topics": ["postgresql"], "orgs": ["postgres"],
         "search": None, "watch": ["postgres/postgres"]},
        {"name": "TiDB", "enabled": True, "aliases": ["tidb"],
         "topics": ["tidb"], "orgs": [{"name": "pingcap", "class": "dedicated"}],
         "search": ['"tidb client"'], "watch": []},
        {"name": "DisabledDB", "enabled": False, "aliases": ["dead"],
         "topics": ["dead-topic"], "orgs": [], "search": None, "watch": []},
    ]
    glob = {"out_of_scope_dbs": ["Redis", "MongoDB"], "ai_keywords": ["mcp"]}
    tax = taxonomy.build_taxonomy(profiles, glob)
    assert tax.topic2db["postgresql"] == "PostgreSQL"
    assert tax.topic2db["tidb"] == "TiDB"
    assert tax.topic2db["pingcap"] == "TiDB"          # org 并入 topic 映射
    assert tax.topic2db["tidb client"] == "TiDB"      # search 显式词去引号
    assert tax.org2db["pingcap"] == "TiDB"            # dict 形态 org
    assert tax.watch2db["postgres/postgres"] == "PostgreSQL"
    assert tax.alias2db["postgres"] == "PostgreSQL"
    assert "dead-topic" not in tax.topic2db           # enabled=False 整库撤
    assert tax.oos_tokens == {"redis", "mongodb"}
    assert len(tax.db_order) == 17 and taxonomy.DB_ORDER[0] == "PostgreSQL"
    assert taxonomy.DB_ORDER[7] == "TiDB"             # 国产从第 8 位起
    # 正则型别名（含特殊字符）跳过
    profiles2 = [dict(profiles[0], aliases=["postgres(-sql)?"])]
    tax2 = taxonomy.build_taxonomy(profiles2, glob)
    assert "postgres(-sql)?" not in tax2.alias2db


def test_sources_edge(collect_dir):
    # growth_base 对无 git 目录降级为空（软失败、不抛异常）
    stars, day = sources.growth_base(os.path.join(collect_dir, "..", "not_exist"),
                                     "20261009")
    assert stars == {} and day == ""

    # readme_head：真实仓非空、长度上限 400、缺失文件空串
    head = sources.readme_head(collect_dir, "Snailclimb/JavaGuide")
    assert head and len(head) <= 400, len(head)
    assert sources.readme_head(collect_dir, "no/such-repo-xyz") == ""

    # _sorted_pool：(-stars, fn) 双键
    items = [{"full_name": "b/x", "stars": 5}, {"full_name": "a/z", "stars": 5},
             {"full_name": "c/y", "stars": 9}]
    out = sources._sorted_pool(items)
    assert [i["full_name"] for i in out] == ["c/y", "a/z", "b/x"]

    # snap_date 真库返回 YYYYMMDD
    snap = sources.snap_date(collect_dir)
    assert len(snap) == 8 and snap.isdigit(), snap


# ================================================================ B/C. 契约与一致性
def _load_outputs(page_dir):
    txt = open(os.path.join(page_dir, "data", "pool.js"), encoding="utf-8").read()
    left, right = txt.split(";\nwindow.POOL=")
    assert left.startswith("window.META=") and right.endswith(";\n")
    meta = json.loads(left[len("window.META="):])
    pool = json.loads(right[:right.rindex(";")])
    dtxt = open(os.path.join(page_dir, "data", "detail.js"), encoding="utf-8").read()
    assert dtxt.startswith("window.DETAIL=") and dtxt.endswith(";\n")
    detail = json.loads(dtxt[len("window.DETAIL="):dtxt.rindex(";")])
    audit = json.load(open(os.path.join(page_dir, "build", "audit_wide_dbs.json"),
                           encoding="utf-8"))
    return meta, pool, detail, audit


def test_contract(page_dir):
    meta, pool, detail, audit = _load_outputs(page_dir)
    order = taxonomy.DB_ORDER
    cats = set(classify.CAT_ORDER)

    # META 字段全集与关键数字闭合
    assert set(meta) == {"built", "snap", "growthBase", "total", "attributed",
                         "unattr", "enriched", "ai", "sec", "stale", "g7cov",
                         "interp", "aiCat", "app", "dbOrder", "catOrder"}, set(meta)
    assert meta["dbOrder"] == order and len(order) == 17
    assert meta["catOrder"] == classify.CAT_ORDER and len(meta["catOrder"]) == 14
    assert meta["attributed"] + meta["unattr"] == meta["total"] == len(pool)

    # 32 列 + 枚举值域 + 唯一性 + 排序
    fns = set()
    prev = None
    n_unattr = n_g7 = 0
    for r in pool:
        assert len(r) == 32, r[0]
        fn = r[0]
        assert fn not in fns, f"重复 fn: {fn}"
        fns.add(fn)
        assert r[7] in cats, (fn, r[7])
        assert r[8] in (0, 1, 2), (fn, r[8])
        assert r[11] in ("cn", "i"), (fn, r[11])
        assert all(d in order for d in r[6]), (fn, r[6])
        # db=首通道主归属（source_topic 优先），dbs=全量并集按 DB_ORDER 排序，
        # 两者可以不同位（netdata: db=MySQL 而 dbs[0]=PostgreSQL 属旧逻辑既定行为）
        assert (r[5] == "") == (len(r[6]) == 0), (fn, r[5], r[6])
        assert r[5] == "" or r[5] in r[6], (fn, r[5], r[6])
        if r[21] is not None:
            assert isinstance(r[21], int), (fn, r[21])
            n_g7 += 1
        if not r[5]:
            n_unattr += 1
        key = (-(r[3]), fn)
        assert prev is None or prev <= key, f"排序破坏 @{fn}"
        prev = key
    assert n_unattr == meta["unattr"], (n_unattr, meta["unattr"])
    assert n_g7 == meta["g7cov"], (n_g7, meta["g7cov"])

    # detail：键 ⊆ pool、全量覆盖（无 star 门槛）、ev 与主表一致
    byfn = {r[0]: r for r in pool}
    for fn, d in detail.items():
        assert fn in byfn, f"detail 孤儿: {fn}"
        assert d["ev"] == byfn[fn][22], fn
        assert len(d["rm"]) <= 400, fn
        assert set(d) <= {"rm", "si", "lg", "rp", "ev", "ol", "rw", "hl", "uc",
                          "ins", "ew", "oe", "cg", "src"}, set(d)
    assert len(detail) == len(pool), (len(detail), len(pool))

    # audit：条目结构 + n 与 dbs 长度一致 + 全部 ≥10
    for it in audit["items"]:
        assert it["n"] == len(it["dbs"]) >= 10, it
        assert all(d in order for d in it["dbs"]), it
    assert audit["count"] == len(audit["items"])


def test_consistency(page_dir, collect_dir):
    meta, pool, detail, audit = _load_outputs(page_dir)
    live = os.path.join(collect_dir, "data", "live")
    pool_fns = {p["full_name"] for p in
                sources._iter_ndjson(os.path.join(live, "pool.ndjson"))}
    assert len(pool) == len(pool_fns), (len(pool), len(pool_fns))   # 池去重全量
    assert {r[0] for r in pool} == pool_fns                          # 集合一致

    # override 生效/未命中与配置对账
    ovr = sources.load_overrides(collect_dir)
    seen = {r[0] for r in pool}
    hits = {fn for fn in ovr if fn in seen}
    assert sum(1 for r in pool if "override" in str(r[22])) == len(hits), \
        "ev override 标记数应等于命中数"
    # section 与 cn 池对齐
    cn_set = {p["full_name"] for p in
              sources._iter_ndjson(os.path.join(live, "pool_cn.ndjson"))}
    assert {r[0] for r in pool if r[11] == "cn"} == cn_set

    # 宽归属审计条目是单通道视角（AI 裁决或 override 签发），主表 dbs 是
    # 规则∪override∪AI 全量并集——audit.dbs 须为主表子集
    byfn = {r[0]: r for r in pool}
    for it in audit["items"]:
        r = byfn.get(it["fn"])
        assert r is not None and set(it["dbs"]) <= set(r[6]), (it["fn"],)

    # g7 与基准快照对账（抽 3 条复核差值口径）
    if meta["growthBase"]:
        stars, _ = sources.growth_base(collect_dir, meta["snap"])
        for fn in ("Snailclimb/JavaGuide", "redis/redis", "eosphoros-ai/DB-GPT"):
            r = byfn.get(fn)
            if r and fn in stars:
                assert r[21] == r[3] - stars[fn], (fn, r[21])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect-dir", default="D:/dbhub_collect")
    ap.add_argument("--page-dir", default=".")
    args = ap.parse_args()

    print("== A. 单元行为 ==")
    check("classify 六分支 + 非官方引擎否决", test_classify)
    check("ai_flag 关键词/词边界/类型", test_ai_flag)
    check("interp 护栏四分支（17丢/≥10审计/无证据>9丢/恰9不丢/范围外过滤）",
          test_interp_guardrail)
    check("interp 字段抽取（截断/枚举清洗/kind 映射/低置信）", test_interp_fields)
    check("taxonomy 映射构造（org并入/search去引号/enabled撤/正则别名跳过）",
          test_taxonomy_maps)
    check("sources 边界（git 降级空/readme 截断/排序双键/snap_date）",
          lambda: test_sources_edge(args.collect_dir))

    print("== B. 输出契约 ==")
    check("pool.js/detail.js/audit 契约（32列/值域/排序/闭合/detail门槛）",
          lambda: test_contract(args.page_dir))

    print("== C. 数据一致性 ==")
    check("与 dbhub_collect 对账（池集合/override/section/审计回查/g7 抽核）",
          lambda: test_consistency(args.page_dir, args.collect_dir))

    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n==== selftest {'通过 ✓' if n_fail == 0 else '未通过 ✗'}"
          f"（{len(RESULTS) - n_fail}/{len(RESULTS)}）====")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
