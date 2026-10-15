# -*- coding: utf-8 -*-
"""AI 解读合并 + 归属护栏（纯函数，零 IO）。

输入是 interp 缓存的原始条目（sources.load_interp 已按 fn 去重取最新），
输出是流水线合并所需的紧凑字段。归属护栏为证据条件式（2026-10-03 定稿）：
v2/v3 裁决带逐库引句证据，幻觉通道已被 db_scan 候选提名 + 逐字校验堵死，
故有证据条目只拦 17/17 无差别全选（README 对比表型），10-16 库照单保留
并进宽归属审计（wide_n）供人工周检；无证据条目（db_verdicts 字段缺失，
防御分支）沿用旧 >9 丢。护栏规则改动只碰本文件。
"""

# interpret 的 kind 枚举 {text2sql,mcp,dba-agent,rag,other} → 本站 {mcp,text2sql,rag,agent}
# "other" 不映射具体类型：只保留 AI 总标记（前端 "ai" 伞形过滤）
AI_KIND_MAP = {"mcp": "mcp", "text2sql": "text2sql", "rag": "rag",
               "dba-agent": "agent"}
AI_CAT_ENUM = {"备份", "监控", "高可用", "迁移", "连接/代理", "管理", "平台", "开发库",
               "安全/审计", "测试/质量", "建模/设计", "内核/引擎", "应用", "其他"}
INSTALL_ENUM = {"npm", "pypi", "docker", "binary", "source", "helm"}


def merge_interp(interp, db_order):
    """抽取合并所需字段，返回 dict 或 None（无解读）。"""
    if not interp:
        return None
    cls = interp.get("classification") or {}
    ident = interp.get("identity") or {}
    sig = interp.get("signals") or {}
    aud = interp.get("audit") or {}
    conf = aud.get("confidence")
    cat = cls.get("cat")
    use_cat = cat in AI_CAT_ENUM and conf in ("high", "mid")
    ai = cls.get("ai") or {}
    kinds = []
    for k in ai.get("kind") or []:
        m = AI_KIND_MAP.get(k)
        if m and m not in kinds:
            kinds.append(m)
    if ai.get("flag") and not kinds:
        kinds = ["ai"]
    aidbs = [d for d in (cls.get("dbs") or []) if d in db_order]
    wide_n = 0
    if "db_verdicts" in cls:
        if len(aidbs) == 17:
            aidbs = []
        elif len(aidbs) >= 10:
            wide_n = len(aidbs)
    elif len(aidbs) > 9:
        aidbs = []
    return {
        "cat": cat if use_cat else "",
        "conf": (2 if conf == "high" else 1) if use_cat else 0,
        "dbs": aidbs,
        "wide_n": wide_n,
        "aik": ",".join(kinds) if ai.get("flag") else "",
        "official": 1 if (cls.get("official") or {}).get("flag") else 0,
        "eco": cls.get("eco") if cls.get("eco") in ("tool", "app") else "",
        "persona": cls.get("persona") if cls.get("persona") in ("use", "ops", "build") else "",
        "status": sig.get("status") if sig.get("status") in
                  ("active", "maintenance", "experimental", "deprecated", "discontinued") else "",
        "ol": (ident.get("one_liner") or "")[:80],
        "rw": ident.get("review") or "",
        "hl": [h[:90] for h in (ident.get("highlights") or [])[:3]],
        "uc": [u[:60] for u in (ident.get("use_cases") or [])[:3]],
        "ins": [i for i in (sig.get("install") or []) if i in INSTALL_ENUM],
        "ew": (cls.get("eco_why") or "")[:140],
        "oe": (aud.get("evidence") or "")[:200],
        "cg": conf or "low",
        "src": "desc" if interp.get("source") == "desc" else "readme",
    }
