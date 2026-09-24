# -*- coding: utf-8 -*-
"""site_export 公共层：路径 / 快照读取 / 口径复用 / 历史库 IO。

设计约定（见 blog-site/demo/落地实施方案.md）：
  - 每个聚合模块是独立脚本，只读本仓库 data/ 下的采集数据（目录或 zip 归档）；
  - watched 边界（已定）：范围内(scoped) 且 star≥10 ∪ 历史上榜 ∪ 历史解读对象；
  - 国产判定必须走 sections.assign_section（token 防误命中），禁止关键词子串；
  - 展示门槛是渲染选项（国际≥300 / 国产≥50 默认档），数据层不做取舍；
  - history.json 原子写入 + 轮转备份。
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

# v2 采集仓库根目录（2026-09-22 site_export 从 v2/ 移到 db-oss-observer/ 下，
# 相对定位失效，改为环境变量可覆盖 + 默认绝对路径；与 verify_independent.py 口径一致）
V2_ROOT = Path(os.environ.get("V2_ROOT", r"D:\daily_github\v2"))
sys.path.insert(0, str(V2_ROOT))

import config  # noqa: E402
import filters  # noqa: E402
import sections  # noqa: E402
import storage  # noqa: E402  noqa: F401 （保留 import 以复用其读取函数）
import tool_registry as reg  # noqa: E402

log = logging.getLogger("site_export")

DATA_DIR = V2_ROOT / "data"
SITE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = SITE_DIR / "history.json"
HISTORY_BACKUPS = 7
BLOG_SITE_DIR = Path(os.environ.get(
    "BLOG_SITE_DIR", r"D:\db-oss-observer\blog-site\data\site"))

WATCH_STAR_MIN = 10          # watched 边界（已定）
TIER_INTL_DEFAULT = 300      # 展示默认档：国际/AI
TIER_CN_DEFAULT = 50         # 展示默认档：国产板块
# 适用库白名单（2026-09-23 定，17 个，禁止出现其他库）：
#   polardb-x 并入 PolarDB；dm/dm8/dameng/达梦 并入 Dameng；tikv 并入 TiDB；
#   Redis/MongoDB 等一律不产出。
KNOWN_DBS = ["PostgreSQL", "MySQL", "Oracle", "SQLite", "SQL Server",
             "ClickHouse", "MariaDB", "TiDB", "OceanBase", "PolarDB",
             "Dameng", "openGauss", "GaussDB", "GBase", "TDSQL",
             "YashanDB", "GoldenDB"]
_DB_PATTERNS = {
    "PostgreSQL": [r"postgres"],
    "MySQL": [r"mysql"],
    "Oracle": [r"oracle"],
    "SQLite": [r"sqlite"],
    "SQL Server": [r"sql\s*server", r"sqlserver", r"mssql"],
    "ClickHouse": [r"clickhouse"],
    "MariaDB": [r"mariadb"],
    "TiDB": [r"tidb", r"tikv"],
    "OceanBase": [r"oceanbase"],
    "PolarDB": [r"polardb"],
    "Dameng": [r"dm8", r"dameng", r"达梦", r"dm[- ]database"],
    "openGauss": [r"opengauss"],
    "GaussDB": [r"gaussdb"],
    "GBase": [r"gbase"],
    "TDSQL": [r"tdsql"],
    "YashanDB": [r"yashandb"],
    "GoldenDB": [r"goldendb"],
}
# 裸词 dm 有歧义：TiDB 生态的 DM=Data Migration（如 pingcap/tiflow，
# 描述和 topics 都会出现裸 dm）。强证据词扫全量；裸词 dm 只在
# 库名+描述+推断串上匹配，且后跟「data migration/数据迁移」解释时排除
_DB_PATTERNS_NOTOPICS = {
    "Dameng": [r"(?<![a-z0-9])dm(?![a-z0-9])"
               r"(?!\s*[（(]?\s*((a\s+)?data[- ]migration|数据迁移))"],
}
CAT_ORDER = ["备份", "监控", "高可用", "迁移", "连接/代理", "管理", "平台", "开发库"]

# ============================================================
# 任务分类三层（2026-09-22 分类试验定案转正，原 _ENH 兜底由本体系替代）：
#   ① GitHub topics 精确集合（作者自标，最可靠）
#   ② 关键词词形匹配（补 manage/ment、migrat/ion 等变体，原表只匹配原形）
#   ③ AI 分类缓存 categories.json（v2/run_categories.py 产出，护栏版提示词）
# 第 8 类「开发库」＝驱动/ORM/SDK/查询构建器/SQL 解析转译工具（试验证据：
# 唯一项目 201 项、精选层 95 项占 11%，原 7 类无家可归；SQL工具 44 项并入）。
# ============================================================
_TOPIC2CAT = {}
for _t in ["backup", "backups", "pgbackrest", "xtrabackup", "barman", "database-backup"]:
    _TOPIC2CAT[_t] = "备份"
for _t in ["monitoring", "monitoring-tool", "prometheus", "alerting", "observability",
           "metrics", "apm", "grafana", "prometheus-exporter"]:
    _TOPIC2CAT[_t] = "监控"
for _t in ["high-availability", "failover", "cluster", "clustering", "replication",
           "patroni", "repmgr", "keepalived", "mysql-ha"]:
    _TOPIC2CAT[_t] = "高可用"
for _t in ["migration", "data-migration", "database-migration", "cdc",
           "change-data-capture", "etl", "data-sync", "debezium"]:
    _TOPIC2CAT[_t] = "迁移"
for _t in ["connection-pool", "connection-pooling", "pool", "proxy", "load-balancer",
           "pgbouncer", "sidecar", "gateway", "database-proxy"]:
    _TOPIC2CAT[_t] = "连接/代理"
for _t in ["database-client", "database-gui", "database-management", "admin",
           "admin-panel", "gui", "database-tool", "sql-client", "dbgui"]:
    _TOPIC2CAT[_t] = "管理"
for _t in ["dbaas", "platform", "paas", "cloud-native", "control-plane"]:
    _TOPIC2CAT[_t] = "平台"
for _t in ["orm", "driver", "database-driver", "odbc", "jdbc", "connector",
           "query-builder", "sdk", "database-sdk", "sql-parser", "parser",
           "sql-transpiler", "transpiler", "sql-formatter", "sql-optimizer",
           "sql-generator"]:
    _TOPIC2CAT[_t] = "开发库"

_TASK_KW = {
    "备份": ["backup", "restore", "restoration", "pitr", "point-in-time", "wal-g",
             "pgbackrest", "xtrabackup", "barman", "mysqldump", "pg_dump", "dump"],
    "监控": ["monitor", "alert", "slow query", "slowquery", "slow-query", "metric",
             "grafana", "prometheus", "observability", "apm", "diagnos",
             "health check", "healthcheck", "health-check", "explain", "profil"],
    "高可用": ["ha", "high availability", "high-availability", "failover", "fail-over",
               "fail over", "cluster", "replication", "patroni", "repmgr",
               "orchestrator", "keepalived", "disaster recovery", "switchover"],
    "迁移": ["migrate", "migration", "sync", "synchronization", "cdc",
             "change data capture", "change-data-capture", "etl", "debezium",
             "replicate", "export", "import", "transfer", "convert", "loader",
             "schema change"],
    "连接/代理": ["pool", "proxy", "load balance", "loadbalancer", "load-balancer",
                  "pgbouncer", "connection pool", "sidecar", "gateway", "router",
                  "routing"],
    "管理": ["manage", "admin", "administration", "client", "gui", "studio", "ide",
             "console", "workbench", "navigator", "browser",
             "database management", "web ui", "webui"],
    "平台": ["platform", "dbaas", "managed", "hosting", "control plane", "saas",
             "self-host"],
    "开发库": ["orm", "odbc", "jdbc", "query builder", "type-safe", "type safe",
               "sql parser", "parses sql", "sql transpil", "sql optimiz",
               "sql format", "sql generation", "sql rewrite", "driver",
               "database abstraction", "database framework"],
}
_RE_CACHE: dict[str, re.Pattern] = {}


def _kw_hit(kw: str, hay: str) -> bool:
    """短语走子串；单词走词边界+常见后缀变体（manage→management 等）。"""
    if " " in kw or "-" in kw:
        return kw in hay
    pat = _RE_CACHE.get(kw)
    if pat is None:
        pat = _RE_CACHE[kw] = re.compile(
            r"\b" + re.escape(kw) + r"(s|es|ed|ing|ment|ion|ions|er|ers|al)?\b")
    return bool(pat.search(hay))


_CATEGORIES_REF: list[dict | None] = [None]


def load_categories() -> dict:
    """AI 任务分类缓存 {fn: {cat, why, ev}}（低置信 ev=低 不入库，此处不设防）。"""
    p = SITE_DIR / "categories.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.warning("categories.json 读取失败：%s", e)
    return {}


# ---------------- 快照读取 ----------------

def snapshot_dates() -> list[str]:
    """全部观察日（目录 ∪ zip 归档），升序。名字必须 snapshot_\\d{8}[.zip]，防垃圾目录。"""
    dates = set()
    for p in DATA_DIR.iterdir():
        m = re.fullmatch(r"snapshot_(\d{8})(?:\.zip)?", p.name)
        if m:
            dates.add(m.group(1))
    return sorted(dates)


def read_pool(date: str) -> list[dict] | None:
    """读某观察日的 merged 候选池（优先目录，回退 zip）。无则 None。"""
    rel = f"merged/all_projects.json"
    d = DATA_DIR / f"snapshot_{date}" / "merged" / "all_projects.json"
    try:
        if d.is_file():
            return json.loads(d.read_text(encoding="utf-8"))
        z = DATA_DIR / f"snapshot_{date}.zip"
        if z.is_file():
            with zipfile.ZipFile(z) as zf:
                name = f"snapshot_{date}/{rel}"
                if name in zf.namelist():
                    return json.loads(io.TextIOWrapper(zf.open(name), encoding="utf-8").read())
    except (OSError, json.JSONDecodeError, zipfile.BadZipFile) as e:
        log.warning("读快照 %s 失败：%s", date, e)
    return None


def read_orgs(date: str) -> dict[str, list[dict]] | None:
    """读某观察日 orgs/*.json → {org: [repo,...]}。无目录则读 zip。"""
    base = DATA_DIR / f"snapshot_{date}" / "orgs"
    out: dict[str, list[dict]] = {}
    if base.is_dir():
        for f in base.glob("*.json"):
            try:
                out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return out or None
    z = DATA_DIR / f"snapshot_{date}.zip"
    if z.is_file():
        try:
            with zipfile.ZipFile(z) as zf:
                prefix = f"snapshot_{date}/orgs/"
                for name in zf.namelist():
                    if name.startswith(prefix) and name.endswith(".json"):
                        out[Path(name).stem] = json.loads(
                            io.TextIOWrapper(zf.open(name), encoding="utf-8").read())
            return out or None
        except (OSError, zipfile.BadZipFile) as e:
            log.warning("读 orgs zip %s 失败：%s", date, e)
    return None


# ---------------- 口径（与管道一致） ----------------

def scoped_items(pool: list[dict]) -> list[dict]:
    """范围内项目：展示相关性过滤 → 排除闸门 → 板块归属（与 run_weekly 同口径）。"""
    out = []
    for it in filters.filter_display_pool(pool):
        fn = it.get("full_name") or ""
        if not fn:
            continue
        if (reg.is_kernel(fn) or sections.should_exclude_sop(it)
                or sections.is_out_of_scope(it) or sections.exclusion_reason(it)):
            continue
        if not sections.assign_section(it):
            continue
        out.append(it)
    return out


def canon_dbs(it: dict) -> list[str]:
    """规范化适用库（desc+topics+推断串 匹配；短词走词边界防子串误报）。

    合并口径：polardb-x→PolarDB；dm/dm8/dameng/达梦→Dameng；tikv→TiDB；
    只产白名单 17 库，Redis/MongoDB 等其他库一律不出现。
    """
    desc_hay = " ".join([
        it.get("full_name") or "",
        it.get("description") or "",
        sections.infer_databases(it) or "",
    ]).lower()
    hay = desc_hay + " " + " ".join(str(t) for t in (it.get("topics") or []))
    out = []
    for db in KNOWN_DBS:
        hit = any(re.search(pat, hay) for pat in _DB_PATTERNS[db])
        if not hit and any(re.search(pat, desc_hay)
                          for pat in _DB_PATTERNS_NOTOPICS.get(db, [])):
            hit = True
        if hit:
            out.append(db)
    return out


def task_cat(it: dict) -> str:
    """任务分类（三层）：topics 精确集合 → 关键词词形 → AI 缓存。"""
    topics = it.get("topics") or []
    for t in topics:
        c = _TOPIC2CAT.get(str(t).lower())
        if c:
            return c
    fn = it.get("full_name") or ""
    hay = ((it.get("description") or "") + " " + fn + " " +
           " ".join(str(t) for t in topics)).lower()
    for cat in CAT_ORDER:
        for kw in _TASK_KW[cat]:
            if _kw_hit(kw, hay):
                return cat
    # ③ AI 缓存兜底（run_categories.py 产出，仅采高/中置信）
    if _CATEGORIES_REF[0] is None:
        _CATEGORIES_REF[0] = load_categories()
    hit = _CATEGORIES_REF[0].get(fn)
    if hit and hit.get("cat") in CAT_ORDER:
        return hit["cat"]
    return "其他"


def record(it: dict, growth=None) -> dict:
    """池项目 → 站点记录（map/archive/weekly 共用字段）。"""
    lic = (it.get("license") or {}).get("spdx_id") or ""
    fn = it.get("full_name") or ""
    return {
        "fn": fn,
        "url": it.get("html_url") or ("https://github.com/" + fn),
        "desc": it.get("description") or "",   # 全文入库(GitHub 本身限 ~350 字),前端卡片样式自行控制展示
        "stars": it.get("stargazers_count") or 0,
        "growth": growth,
        "section": sections.assign_section(it) or "",
        "cat": task_cat(it),
        "dbs": canon_dbs(it),
        "license": lic if lic != "NOASSERTION" else "",
        "lang": it.get("language") or "",
        "commit7": it.get("commit_count_7d"),
        "pushed": (it.get("pushed_at") or "")[:10],
        "archived": bool(it.get("archived")),
    }


def prev_snapshot_date(date: str) -> str | None:
    """观察日列表中 date 的前一个。"""
    ds = snapshot_dates()
    i = ds.index(date) if date in ds else len(ds)
    return ds[i - 1] if i > 0 else None


# ---------------- M5 富集数据（release / security / personas） ----------------

def find_latest_meta(name: str, before: str) -> tuple[dict, str | None]:
    """在 ≤before 的观察日（目录或 zip）里找最近的 meta/{name}.json。

    富集按周节奏采集，聚合日不一定当天有 → 向前找最近一份。
    返回 (by_repo 映射, 数据观察日 YYYYMMDD)；找不到 → ({}, None)。
    """
    for d in reversed([x for x in snapshot_dates() if x <= before]):
        try:
            plain = DATA_DIR / f"snapshot_{d}" / "meta" / name
            if plain.is_file():
                obj = json.loads(plain.read_text(encoding="utf-8"))
                return (obj.get("by_repo") or {}), d
            z = DATA_DIR / f"snapshot_{d}.zip"
            if z.is_file():
                with zipfile.ZipFile(z) as zf:
                    nm = f"snapshot_{d}/meta/{name}"
                    if nm in zf.namelist():
                        obj = json.loads(
                            io.TextIOWrapper(zf.open(nm), encoding="utf-8").read())
                        return (obj.get("by_repo") or {}), d
        except (OSError, json.JSONDecodeError, zipfile.BadZipFile) as e:
            log.warning("读 meta %s@%s 失败：%s", name, d, e)
    return {}, None


PERSONAS_FILE = Path(os.environ.get(
    "PERSONAS_FILE", str(SITE_DIR / "personas.json")))


def load_personas() -> dict:
    """批量 AI 人群分类缓存 {fn: {p, ai, why, when}}（缺文件返回空）。"""
    if PERSONAS_FILE.is_file():
        try:
            return json.loads(PERSONAS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.warning("personas.json 读取失败：%s", e)
    return {}


def db_slug(db: str) -> str:
    """库名 → 文件名安全 slug（前端按同规则请求 archive-{slug}.json）。"""
    return re.sub(r"[^A-Za-z0-9-]+", "-", db).strip("-")


_OPS_CATS = {"监控", "备份", "高可用", "迁移", "连接/代理"}
_BUILD_KW = ("raft", "consensus", "storage engine", "rewrite", "reimplemented", "wire protocol")


def persona_of(section: str, cat: str, fn: str, desc: str) -> tuple[str, bool]:
    """人群映射（规则版）：主类 use/ops/build + AI 横切标。正式版由管道 AI 输出。"""
    ai = section == "AI工具"
    primary = "ops" if (cat in _OPS_CATS or cat == "平台") else "use"
    hay = (desc + " " + fn).lower()
    if any(k in hay for k in _BUILD_KW):
        primary = "build"
    return primary, ai


# ---------------- 历史库 ----------------

def load_history() -> dict:
    if HISTORY_FILE.is_file():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.error("history.json 损坏（%s），从轮转备份恢复或重跑 backfill。", e)
            for i in range(1, HISTORY_BACKUPS + 1):
                bak = HISTORY_FILE.with_suffix(f".json.{i}")
                if bak.is_file():
                    try:
                        return json.loads(bak.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue
            raise
    return {"meta": {"dates": [], "watch_rule": "scoped+star>=10|board|focus"},
            "watched": {}, "pool_seen": {}}


def save_history(h: dict) -> None:
    """原子写入 + 轮转备份。"""
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    if HISTORY_FILE.is_file():
        for i in range(HISTORY_BACKUPS - 1, 0, -1):
            src = HISTORY_FILE.with_suffix(f".json.{i}")
            dst = HISTORY_FILE.with_suffix(f".json.{i + 1}")
            if src.is_file():
                shutil.copyfile(src, dst)
        shutil.copyfile(HISTORY_FILE, HISTORY_FILE.with_suffix(".json.1"))
    tmp = HISTORY_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(h, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, HISTORY_FILE)


def anchor_dates(dates: list[str]) -> list[str]:
    """每周（ISO 周）最后一个观察日，升序。"""
    weeks: dict[tuple, str] = {}
    for d in dates:
        dt = datetime.strptime(d, "%Y%m%d")
        weeks.setdefault(dt.isocalendar()[:2], d)
        weeks[dt.isocalendar()[:2]] = max(weeks[dt.isocalendar()[:2]], d)
    return [weeks[k] for k in sorted(weeks)]


def streaks_of(w: dict | None) -> tuple[int, int]:
    """(连续在池周数, 连涨周数)：基于周锚点，跳过无数据锚点。"""
    if not w:
        return 0, 0
    daily: dict = w.get("daily") or {}
    anc = anchor_dates_from_history()
    present = [d for d in anc if d in daily]
    wp = 0
    for d in reversed(anc):
        if d not in daily:
            break
        wp += 1
    stars = [daily[d] for d in present]
    gs = 0
    for i in range(len(stars) - 1, 0, -1):
        if stars[i] > stars[i - 1]:
            gs += 1
        else:
            break
    return wp, gs


_ANCHOR_CACHE: list[str] | None = None


def anchor_dates_from_history() -> list[str]:
    global _ANCHOR_CACHE
    if _ANCHOR_CACHE is None:
        h = _HISTORY_REF[0] or {"meta": {"dates": []}}
        _ANCHOR_CACHE = anchor_dates(h.get("meta", {}).get("dates") or [])
    return _ANCHOR_CACHE


_HISTORY_REF: list[dict | None] = [None]


def bind_history(h: dict) -> None:
    """进程内绑定 history（streaks_of 用），避免反复读盘。"""
    _HISTORY_REF[0] = h
    global _ANCHOR_CACHE
    _ANCHOR_CACHE = None


# ---------------- 输出 ----------------

def write_site_json(name: str, obj) -> Path:
    BLOG_SITE_DIR.mkdir(parents=True, exist_ok=True)
    p = BLOG_SITE_DIR / name
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)
    log.info("写出 %s（%d KB）", p, p.stat().st_size // 1024)
    return p


def month_window(latest: str, dates: list[str], min_days: int = 26, max_days: int = 38) -> str | None:
    """月窗基准：latest 之前 26-38 天内最近的观察日。"""
    lt = datetime.strptime(latest, "%Y%m%d")
    cands = []
    for d in dates:
        if d >= latest:
            break
        dd = (lt - datetime.strptime(d, "%Y%m%d")).days
        if min_days <= dd <= max_days:
            cands.append(d)
    return cands[-1] if cands else None


def star_at(w: dict | None, dates: list[str], target: str) -> int | None:
    """watched 项目在 target 日的星数；当日缺数据则就近回退（≤target 的最近有值日）。"""
    if not w:
        return None
    daily: dict = w.get("daily") or {}
    if target in daily:
        return daily[target]
    for d in reversed(dates):
        if d < target and d in daily:
            return daily[d]
    return None


def org_base_date(base: str, dates: list[str], lookback_days: int = 14) -> str | None:
    """从 base 向前找最近一个带 orgs 数据的观察日（部分日期未扫 org）。"""
    bt = datetime.strptime(base, "%Y%m%d")
    for d in reversed(dates):
        if d > base:
            continue
        if (bt - datetime.strptime(d, "%Y%m%d")).days > lookback_days:
            break
        if read_orgs(d):
            return d
    return None


def issue_no(date: str) -> int:
    try:
        d0 = datetime.strptime(config.FIRST_ISSUE_DATE, "%Y%m%d").date()
        d1 = datetime.strptime(date, "%Y%m%d").date()
    except (ValueError, AttributeError):
        return 0
    return max(0, (d1 - d0).days // 7 + 1)
