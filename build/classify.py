# -*- coding: utf-8 -*-
"""规则分类 + AI 旗标（纯函数，零 IO）。

分类优先级：内核/引擎白名单特判 > topic 主题命中 > 名称/描述关键词 >
应用兜底 > 其他。规则集逐字沿自重构前的旧单体脚本（2026-10-09 拆分），
改动分类口径只碰本文件。
"""
import re

# 顺序即优先级：主题命中 > 名称/描述关键词命中。
# 每条: (类别, topic 词集, 关键词正则)
CAT_RULES = [
    ("内核/引擎", {"database-engine", "dbms", "sql-engine"},
     r"(^|[\s/_-])(server|engine|kernel|dbms)([\s/_-]|$)|mysql-server|opengauss-server|"
     r"polardbx-engine|^sqlite$|^tidb$|^tikv$|^oceanbase$|^postgres$"),
    ("安全/审计", {"audit", "security", "sql-audit", "data-masking", "masking",
                "encryption", "vault"},
     r"audit|firewall|脱敏|mask(ing)?|加密|encrypt|sql[- ]injection|waf|vault|"
     r"yearning|archery|敏感数据|secrets?[- ]scan|权限管理|rbac"),
    ("测试/质量", {"fuzzing", "benchmark", "sysbench", "tpcc", "tpch", "jepsen"},
     r"fuzz|benchmark|sysbench|sqlsmith|jepsen|stress[- ]test|tpc-[ch]|tpcc|tpch|"
     r"性能测试|正确性"),
    ("备份", {"backup", "mysqldump", "xtrabackup", "pgdump", "pgbackrest", "barman",
           "data-recovery"},
     r"backup|back[- ]?up|mysqldump|xtrabackup|pg_?dump|pgbackrest|barman|"
     r"dump(ing)?|restore|pitr|备份|恢复|归档"),
    ("监控", {"exporter", "prometheus", "grafana", "monitoring", "zabbix",
            "observability", "datadog"},
     r"exporter|prometheus|grafana|monitor|observab|metric|alert(ing)?|zabbix|pmm|"
     r"telemetry|健康检查|health[- ]?check|监控"),
    ("高可用", {"haproxy", "keepalived", "patroni", "high-availability", "failover"},
     r"patroni|keepalived|failover|high[- ]?availability|高可用|主备切换|switchover|"
     r"replication[- ]manager|raft共识|容灾"),
    ("迁移", {"migration", "data-migration", "cdc", "canal", "otter", "etl",
            "flyway", "liquibase"},
     r"migrat|cdc\b|canal\b|otter\b|dtle|data[- ]?sync|data[- ]?transfer|etl\b|dts\b|"
     r"flyway|liquibase|sqitch|异构|同步|迁移|数据搬运"),
    ("建模/设计", {"erd", "er-diagram", "database-design", "schema-design", "dbml"},
     r"\berd?\b|er[- ]diagram|schema[- ]design|data[- ]model|dbml|建模|"
     r"table[- ]design|数据库设计"),
    ("连接/代理", {"proxy", "pooler", "pgbouncer", "sharding", "load-balancer",
                "gateway"},
     r"proxy|pooler|pgbouncer|connection[- ]pool|负载均衡|load[- ]balanc|"
     r"shard(ing)?sphere|mycat|vitess|路由|router|gateway"),
    ("开发库", {"orm", "driver", "connector", "jdbc", "odbc", "sdk", "client",
             "sqlalchemy", "gorm", "mybatis", "hibernate", "prisma", "typeorm"},
     r"\borm\b|driver|jdbc|odbc|connector|sdk\b|client library|sqlalchemy|gorm\b|"
     r"mybatis|hibernate|prisma|typeorm|sequelize|activerecord|jooq|dapper\b|"
     r"psycopg|pymysql|mysqlclient|go-sql-driver|libpq|query[- ]builder|"
     r"database/sql|数据库连接|连接池"),
    ("管理", {"admin", "gui", "dashboard", "phpmyadmin", "adminer", "cli",
            "database-management"},
     r"\bgui\b|admin(er|panel)?|dashboard|studio|console|phpmyadmin|chat2db|dbeaver|"
     r"metabase|superset|bi\b|报表|可视化|web[- ]client|管理工具|运维平台|"
     r"import|export|导入导出|慢查询|slow[- ]query"),
    ("平台", {"platform", "paas", "dbops"},
     r"一体化平台|one[- ]stop|dbpaas|db-?ops|云管平台|管控平台|database platform"),
]
# 应用/其他 兜底
APP_PAT = (r"awesome|curated|list of|tutorial|demo\b|example|sample|template|"
           r"starter|boilerplate|course|learning|interview|面试|笔记|notes\b|"
           r"roadmap|cheat[- ]sheet|best[- ]practice|guide\b| cookbook")
COMPILED = [(cat, set(ts), re.compile(pat, re.I))
            for cat, ts, pat in CAT_RULES if cat != "内核/引擎"]
APP_RE = re.compile(APP_PAT, re.I)
KERNEL_NAME_RE = re.compile(
    r"^(tidb|tikv|oceanbase|postgres|sqlite|mariadb)$|"
    r"(server|engine|kernel)$|^(server|engine)$", re.I)
KERNEL_TOPICS = {"database-engine", "dbms", "sql-engine"}

# META.catOrder：规则序 + 兜底两类（前端类别筛选的固定顺序）
CAT_ORDER = [c for c, _, _ in CAT_RULES] + ["应用", "其他"]

AI_KINDS = [
    ("mcp", re.compile(r"\bmcp\b|model context protocol", re.I)),
    ("text2sql", re.compile(r"text[- ]?2[- ]?sql|text[- ]to[- ]sql|nl2sql|chat2sql|"
                            r"自然语言.*sql|sql.*自然语言", re.I)),
    ("rag", re.compile(r"\brag\b|retrieval[- ]augmented", re.I)),
    ("agent", re.compile(r"\bagent|copilot|assistant", re.I)),
    ("llm", re.compile(r"\bllm|gpt|openai|claude|deepseek|qwen|大模型|大语言", re.I)),
]


def classify(item, watch2db, org2db):
    """返回 (类别, 置信度2/1/0, 依据串)。内核/引擎仅限官方或白名单。"""
    topics = set(t.lower() for t in (item.get("topics") or []))
    fn = item["full_name"]
    name = fn.split("/")[-1].lower()
    text = "%s %s" % (name, item.get("description") or "")
    official = ((item.get("owner") or "").lower() in org2db
                or fn.lower() in watch2db)
    # 内核/引擎：白名单，或官方仓 + 引擎式命名/主题
    if fn.lower() in watch2db:
        return "内核/引擎", 2, "官方内核/白名单"
    if official and (KERNEL_NAME_RE.search(name)
                     or topics & KERNEL_TOPICS):
        return "内核/引擎", 2, "官方+引擎命名"
    for cat, tset, pat in COMPILED:
        hit = topics & tset
        if hit:
            return cat, 2, "topic:" + ",".join(sorted(hit)[:3])
    for cat, tset, pat in COMPILED:
        m = pat.search(text)
        if m:
            frag = m.group(0).strip().lower()[:18]
            return cat, 1, "kw:" + frag
    if APP_RE.search(text):
        m = APP_RE.search(text).group(0).lower()
        return "应用", 1, "kw:" + m
    return "其他", 0, ""


def ai_flag(item, ai_keywords):
    """GLOBAL.ai_keywords 命中 → AI 类型短词，未命中空串。"""
    topics = set(t.lower() for t in (item.get("topics") or []))
    text = "%s %s" % (item["full_name"], item.get("description") or "")
    for kw in ai_keywords:
        k = kw.lower()
        if k in topics:
            kind = next((n for n, r in AI_KINDS if r.search(k)), "ai")
            return kind
        if len(k) <= 4:
            if re.search(r"\b%s\b" % re.escape(k), text, re.I):
                return next((n for n, r in AI_KINDS if r.search(k)), "ai")
        elif k in text.lower():
            return next((n for n, r in AI_KINDS if r.search(k)), "ai")
    return ""
