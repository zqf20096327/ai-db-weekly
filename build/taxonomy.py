# -*- coding: utf-8 -*-
"""库口径：17 库顺序、档案映射表、范围外词表。

数据来源是 dbhub_collect/config/db_profiles.py（ast 解析取常量，
不 import 采集仓库代码）。四张归属映射表的构造规则与旧 build_demo.py
逐行对齐：topic2db 在最后并入 org2db（org 通道的 source_topic 就是 org 名）。
"""
import ast
import os
import re
from dataclasses import dataclass, field

INTL_ORDER = ["PostgreSQL", "MySQL", "Oracle", "SQLite", "SQL Server",
              "ClickHouse", "MariaDB"]
CN_ORDER = ["TiDB", "OceanBase", "PolarDB", "Dameng", "openGauss",
            "GaussDB", "GBase", "TDSQL", "YashanDB", "GoldenDB"]
DB_ORDER = INTL_ORDER + CN_ORDER


def load_profiles(collect_dir):
    """ast 解析 db_profiles.py，得到 (PROFILES 列表, GLOBAL 字典)。"""
    src = open(os.path.join(collect_dir, "config", "db_profiles.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    profiles, glob = [], {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = node.targets[0].id
            if name == "PROFILES":
                profiles = ast.literal_eval(node.value)
            elif name == "GLOBAL":
                glob = ast.literal_eval(node.value)
    return profiles, glob


def norm_topic(t):
    if isinstance(t, dict):
        t = t.get("name", "")
    return t.strip().lower()


@dataclass
class Taxonomy:
    """归属/分类全流程共享的口径对象。"""
    db_order: list = field(default_factory=lambda: DB_ORDER)
    topic2db: dict = field(default_factory=dict)
    org2db: dict = field(default_factory=dict)
    watch2db: dict = field(default_factory=dict)
    alias2db: dict = field(default_factory=dict)
    oos_tokens: set = field(default_factory=set)     # 范围外库词表（未归类提示用）
    ai_keywords: list = field(default_factory=list)


def build_maps(profiles):
    """source_topic -> DB；org -> DB；watch repo -> DB；topics 别名 token -> DB。"""
    topic2db, org2db, watch2db, alias2db = {}, {}, {}, {}
    for p in profiles:
        if not p.get("enabled", True):
            continue
        name = p["name"]
        for t in p.get("topics", []):
            topic2db[norm_topic(t)] = name
        for o in p.get("orgs", []):
            oname = o["name"] if isinstance(o, dict) else o
            org2db[oname.lower()] = name          # brand_infer 简化：org 主归属
        for w in p.get("watch", []):
            watch2db[w.lower()] = name
        for kw in p.get("search") or []:
            if isinstance(kw, str) and kw != "auto":
                topic2db[kw.strip('"').lower()] = name
        for a in p.get("aliases", []):
            try:                                   # 跳过正则型别名
                re.compile(a)
                # 注意：不能遍历 r"\s[]()|*+?{}" 的单字符（\s 会拆成字母 s，
                # 吞掉 postgres/sqlite 等一切含 s 的别名——旧脚本因此漏判
                # 274 项 mssql 归属，2026-10-09 修复）
                if re.search(r"[\s\[\]()|*+?{}]", a):
                    continue
            except re.error:
                pass
            alias2db[a.lower()] = name
    # 组织别名补充（org 通道 source_topic 就是 org 名）
    topic2db.update(org2db)
    return topic2db, org2db, watch2db, alias2db


def build_taxonomy(profiles, glob):
    """从档案常量构造 Taxonomy。"""
    topic2db, org2db, watch2db, alias2db = build_maps(profiles)
    return Taxonomy(
        topic2db=topic2db, org2db=org2db, watch2db=watch2db,
        alias2db=alias2db,
        oos_tokens={w.lower() for w in glob.get("out_of_scope_dbs", [])},
        ai_keywords=glob.get("ai_keywords", []),
    )
