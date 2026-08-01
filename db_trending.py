#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI×DB 周报 - GitHub 项目采集脚本

双轨搜索：
  主轨: topic:database → 成熟项目(热门榜/重点解读)
  副轨: AI词×DB词交叉查询 + 近N天新建 → 早期项目(新锐发现)

━━━ 后期维护指南 ━━━
要改采集范围/门槛，只需修改下方 CONFIG 区，不用动其他代码。
常见调整见各配置项的注释。
"""

import os
import sys
import re
import json
import time
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

# ╔══════════════════════════════════════════════════════════╗
# ║  CONFIG 区 — 所有可调参数集中在这里，改这里就够了          ║
# ╚══════════════════════════════════════════════════════════╝

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")
OUTPUT_DIR = os.path.join(HERE, "output")
DRAFT_DIR = os.path.join(OUTPUT_DIR, "draft")   # 非发布日的草稿目录

# --- 采集范围（改这里调整「抓什么」）---
# 搜索方式：两轨都用 topic:database，只是 star/时间不同
# 主轨: topic:database stars:>50 pushed:>180天
# 副轨: topic:database stars:>2  created:>14天
SEARCH_KEYWORD = "database"
SEARCH_MODE = "topic"          # topic:database

# 数据库名称信号词：验证阶段用，项目描述/topics 里命中任一即视为关系型数据库相关
# 想加新库（如 GaussDB）只需往列表加一个字符串
DB_KEYWORDS = [
    "mysql", "postgres", "postgresql", "sqlite", "mariadb", "oracle",
    "tidb", "cockroachdb", "oceanbase", "opengauss", "polardb",
    "sqlserver", "db2",
]

# AI 信号词：验证阶段用，命中任一即视为 AI 相关
# 初筛(描述/topics)用词边界匹配；README 精筛统计命中次数
AI_KEYWORDS = [
    "agent", "mcp", "llm", "gpt", "copilot",
    "text2sql", "nl2sql", "nl-to-sql",
    "rag", "skill", "chatbot", "ai-native",
    "natural language", "embedding", "openai", "claude",
    "language model", "prompt", "genai", "ai-driven",
    "ai assistant",
]

# README 精筛：AI 词命中次数 ≥ 此值才保留（剔除 TiDB 这种靠 topic 蹭的）
README_AI_MIN_HITS = 3

# --- 门槛（改这里调整「抓多严」）---
MAIN_STARS_MIN = 50          # 主轨最低 star
MAIN_ACTIVE_DAYS = 180       # 主轨活跃窗口（近 N 天有更新）
EMERGING_STARS_MIN = 2       # 副轨最低 star
EMERGING_CREATED_DAYS = 14   # 副轨新建窗口（近 N 天创建）
MAIN_MAX_PAGES = 10          # 主轨分页数（每页100，10页=最多1000，GitHub上限）
DELTA_DAYS = 7               # 周增量计算的天数
PUBLISH_WEEKDAY = 5          # 周几发布周报：0=周一 1=周二 ... 6=周日 [临时=5周六,测完改回0]

# --- 榜单条数（改这里调整「展示多少」）---
HOT_TOP_N = 10
EMERGING_TOP_N = 5

# --- 噪音黑名单（命中即剔除）---
# 描述里含这些词的项目直接排除
DESC_BLACKLIST = [
    "30 days of", "tutorial", "course", "learn-", "awesome-",
    "cheatsheet", "interview", "ssl pinning", "bypass",
    "proxy panel", "vless", "wechat", "decrypt",
    "monitoring system", "infrastructure monitoring",
    "agentic memory", "memory map", "3d model", "daz 3d",
    "x64dbg", "x32dbg", "dead by daylight", "dbd auto",
    "hackerrank", "certification test", "brain training",
    "code intelligence", "codebase memory",
    "unreal engine", "虚幻引擎", "game development",
    "figma", "browser automation", "filesystem",
    "spreadsheet", "电子表格", "hosting", "faq",
]
# 精确剔除的项目（owner/name 全小写）
KNOWN_OFFTOPIC = {
    "netdata/netdata", "asabeneh/30-days-of-python",
    "teableio/teable", "dolthub/dolt",
    "quivrhq/quivr", "sinaptik-ai/pandas-ai",
    "thorsten/phpmyfaq", "dalisoft/awesome-hosting",
    "ystemsrx/mini-nanogpt", "ai4protein/venusfactory2",
    "redis/mcp-redis", "neo4j-contrib/mcp-neo4j",
    "falkordb/falkordb", "rush-db/rushdb",
    "matrixorigin/memoria", "lealone/lealone",
    "matrixages/polywise", "henrydaum/second-brain",
    "bvisible/mcp-ssh-manager", "tugraph-family/chat2graph",
}


# ╔══════════════════════════════════════════════════════════╗
# ║  以下为实现代码，一般不需要修改                            ║
# ╚══════════════════════════════════════════════════════════╝

# --- 环境变量 ---
def load_env_file():
    """从 .env 读取配置（不覆盖已设的环境变量）。"""
    env_path = os.path.join(HERE, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v


load_env_file()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
AI_BASE_URL = os.environ.get(
    "AI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
).strip().rstrip("/")
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "glm-4-flash").strip()
# 飞书机器人 webhook（可选，配置后自动推送）
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "").strip()

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TODAY_DT = datetime.now(timezone.utc)
AI_DESC_CACHE = os.path.join(CACHE_DIR, f"ai_desc_{TODAY}.json")


def daterange_iso(days_ago):
    """N 天前的 UTC 日期（YYYY-MM-DD）。"""
    return (TODAY_DT - timedelta(days=days_ago)).strftime("%Y-%m-%d")


# ============================================================
# GitHub API
# ============================================================
API_ROOT = "https://api.github.com/search/repositories"


def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-db-weekly-bot/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        if "403" in str(e):
            print(f"[!] 限速/认证问题: {e}", file=sys.stderr)
        else:
            print(f"[!] 请求失败: {e}", file=sys.stderr)
        return None


def search_repos(query, per_page=100, page=1):
    params = {"q": query, "sort": "stars", "order": "desc",
              "per_page": per_page, "page": page}
    url = f"{API_ROOT}?{urllib.parse.urlencode(params)}"
    data = github_get(url)
    return data["items"] if data and "items" in data else []


# ============================================================
# AI 介绍生成（基于 README）
# ============================================================
def _load_ai_cache():
    if not os.path.exists(AI_DESC_CACHE):
        return {}
    try:
        with open(AI_DESC_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_ai_cache(cache):
    with open(AI_DESC_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _call_ai_chat(messages):
    if not AI_API_KEY:
        return None
    url = f"{AI_BASE_URL}/chat/completions"
    payload = {"model": AI_MODEL, "messages": messages,
               "temperature": 0.3, "max_tokens": 4096}
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {AI_API_KEY}"}
    # 最多重试 3 次，遇到 429 限流时等待后重试
    for attempt in range(3):
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                # 思考模型可能返回空 content（思考被截断），重试
                if content and content.strip():
                    return content.strip()
                if attempt < 2:
                    time.sleep(3)
                    continue
                return None
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = (attempt + 1) * 10
                print(f"    [AI] 限流，{wait}s 后重试...", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"    [AI] 调用失败: {e}", file=sys.stderr)
            return None
    return None


def fetch_readme(full_name):
    """抓 README 前 3000 字符，让 AI 基于真实内容生成介绍。"""
    url = f"https://api.github.com/repos/{full_name}/readme"
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": f"Bearer {GITHUB_TOKEN}",
               "User-Agent": "ai-db-weekly-bot/1.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:3000]
    except Exception:
        return None


def gen_zh_desc(full_name, en_desc, lang, cache):
    if full_name in cache:
        return cache[full_name]
    if not AI_API_KEY:
        return en_desc or "（无描述）"
    readme = fetch_readme(full_name)
    context = f"项目README（节选）：\n{readme}" if readme else f"英文描述：{en_desc or '（无）'}"
    prompt = (
        f"你是数据库技术编辑。基于以下项目的真实信息，用一句话介绍它，要求：\n"
        f"1. 中文，100字左右\n"
        f"2. 说清它是做什么的、核心功能、解决什么问题\n"
        f"3. 只陈述 README 里的事实，不要臆测或夸大\n"
        f"4. 不要寒暄，直接输出介绍内容\n\n"
        f"项目名：{full_name}\n主要语言：{lang}\n{context}"
    )
    text = _call_ai_chat([{"role": "user", "content": prompt}])
    if not text:
        return en_desc or "（无描述）"
    text = text.strip().strip("\"'""''")
    cache[full_name] = text
    return text


def gen_spotlight(full_name, en_desc, lang, stars, delta, readme, cache):
    cache_key = f"spotlight__{full_name}"
    if cache_key in cache:
        return cache[cache_key]
    if not AI_API_KEY:
        return None
    context = f"项目README（节选）：\n{readme}" if readme else f"英文描述：{en_desc or '（无）'}"
    prompt = (
        f"你是数据库技术编辑。基于以下项目的真实信息做「本周重点解读」，要求：\n"
        f"1. 中文，150字以内\n"
        f"2. 分三部分：① 解决什么问题 ② 核心亮点 ③ 适用场景/注意事项\n"
        f"3. 只陈述 README 里能验证的事实，不要臆测\n"
        f"4. 客观平实，不要营销腔\n\n"
        f"项目名：{full_name}\nStar：{stars}（本周增长 {delta}）\n"
        f"主要语言：{lang}\n{context}"
    )
    text = _call_ai_chat([{"role": "user", "content": prompt}])
    if not text:
        return None
    text = text.strip().strip("\"'""''")
    cache[cache_key] = text
    return text


def fill_zh_descs(items, cache):
    for v in items:
        v["zh_desc"] = gen_zh_desc(v["full"], v["desc"], v["lang"], cache)


# ============================================================
# 双重验证：具体库名 AND AI词
# ============================================================
# 预编译正则（词边界，避免 rag 匹配 storage；mysql 等不需边界）
_DB_REGEX = [re.compile(rf"\b{kw}\b") if len(kw) <= 4 else re.compile(kw)
             for kw in DB_KEYWORDS]
_AI_REGEX = [re.compile(rf"\b{kw}\b", re.IGNORECASE) for kw in AI_KEYWORDS]


def is_ai_db(repo):
    """双重验证：描述/topics/名字同时含具体库名 AND AI词。"""
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    topics = " ".join(repo.get("topics", []) or []).lower()
    text = f"{name} {desc} {topics}"
    has_db = any(p.search(text) for p in _DB_REGEX)
    has_ai = any(p.search(text) for p in _AI_REGEX)
    return has_db and has_ai


def is_blacklisted(repo):
    """黑名单 + 已知误标项目剔除。"""
    full = (repo.get("full_name") or "").lower()
    if full in KNOWN_OFFTOPIC:
        return True
    desc = (repo.get("description") or "").lower()
    for bad in DESC_BLACKLIST:
        if bad in desc or bad in full:
            return True
    return False


def count_ai_hits_in_readme(readme_text):
    """统计 README 里 AI 关键词的命中次数。

    用于精筛：靠 topic 蹭 AI 标签但 README 里没真讲 AI 的项目会被剔除。
    """
    if not readme_text:
        return 0
    text = readme_text.lower()
    total = 0
    for kw in AI_KEYWORDS:
        # 含特殊字符的词用直接匹配，其余用词边界
        if any(c in kw for c in "2- "):
            total += len(re.findall(re.escape(kw), text))
        else:
            total += len(re.findall(rf"\b{re.escape(kw)}\b", text))
    return total


def is_ai_by_readme(readme_text):
    """README 精筛：AI 词命中 ≥ README_AI_MIN_HITS 次才算真 AI 项目。"""
    return count_ai_hits_in_readme(readme_text) >= README_AI_MIN_HITS


# ============================================================
# 双轨搜索（两轨搜索方式+验证规则完全相同，只是 star/时间不同）
# ============================================================
def _build_query(stars_min, time_filter):
    """构建统一的搜索查询：topic:database + star + 时间条件。"""
    return f"topic:{SEARCH_KEYWORD} stars:>{stars_min} {time_filter}"


def _fetch_track(track_name, stars_min, time_filter, max_pages, per_page=100, raw_pool=None):
    """通用采集函数：执行搜索 + 黑名单 + 双重验证。

    主轨和副轨共用此函数，只是参数不同。
    raw_pool: 传入一个 dict，所有搜索到的原始项目都会存进去（用于全量快照）。
    """
    query = _build_query(stars_min, time_filter)
    merged = {}
    for page in range(1, max_pages + 1):
        items = search_repos(query, per_page=per_page, page=page)
        if not items:
            break
        kept = 0
        for it in items:
            full = it.get("full_name", "")
            if not full:
                continue
            # 全量记录到 raw_pool（不管是否通过筛选，都存 star 供增量对比）
            if raw_pool is not None and full not in raw_pool:
                raw_pool[full] = it
            # 初筛：黑名单 + 双重关键词
            if full in merged or is_blacklisted(it) or not is_ai_db(it):
                continue
            it["_track"] = track_name
            it["_tags"] = {track_name}
            merged[full] = it
            kept += 1
        print(f"  · {track_name}第{page}页: 抓{len(items)} 留{kept}")
        time.sleep(1)
        if len(items) < per_page:
            break
    return merged


def fetch_main_track(raw_pool):
    """主轨：topic:database stars:>50 近180天活跃。"""
    return _fetch_track("主轨", MAIN_STARS_MIN,
                        f"pushed:>{daterange_iso(MAIN_ACTIVE_DAYS)}",
                        MAIN_MAX_PAGES, raw_pool=raw_pool)


def fetch_emerging_track(raw_pool):
    """副轨：topic:database stars:>2 近14天创建。"""
    return _fetch_track("新锐", EMERGING_STARS_MIN,
                        f"created:>{daterange_iso(EMERGING_CREATED_DAYS)}",
                        max_pages=1, per_page=100, raw_pool=raw_pool)


def fetch_all():
    """双轨采集 → 合并去重 → README 精筛。

    返回 (精筛结果, 全量快照数据)。
    全量快照 = 所有搜索到的项目（不管是否通过筛选），保证进榜项目都有历史可对比。
    """
    # raw_pool 收集所有搜索到的原始项目，用于全量快照
    raw_pool = {}

    print("  === 主轨: topic:database stars:>50 近180天 ===")
    main = fetch_main_track(raw_pool)
    print(f"  主轨初筛: {len(main)} 个（全量池: {len(raw_pool)} 个）\n")

    print("  === 副轨: topic:database stars:>2 近14天创建 ===")
    emerging = fetch_emerging_track(raw_pool)
    print(f"  副轨初筛: {len(emerging)} 个（全量池: {len(raw_pool)} 个）")

    # 合并：副轨中已在主轨的（star已超50），归主轨
    for full, repo in emerging.items():
        if full not in main:
            main[full] = repo
    print(f"\n  合并去重: {len(main)} 个（全量池: {len(raw_pool)} 个）")

    # README 精筛：抓 README，AI 词命中 ≥3 次才保留
    print(f"\n  === README 精筛（AI词命中≥{README_AI_MIN_HITS}次）===")
    filtered = {}
    removed = []
    for full, repo in main.items():
        readme = fetch_readme(full)
        hits = count_ai_hits_in_readme(readme)
        if hits >= README_AI_MIN_HITS:
            repo["_readme"] = readme  # 缓存，后面生成介绍时复用
            filtered[full] = repo
        else:
            removed.append((full, hits))
    print(f"  README 精筛后: {len(filtered)} 个（剔除 {len(removed)} 个）")
    for full, hits in removed:
        print(f"    ✗ {full} (AI命中{hits}次)")

    return filtered, raw_pool  # 精筛结果 + 全量快照数据


# ============================================================
# 快照（算周增量）
# ============================================================
def snapshot_path(date_str):
    return os.path.join(CACHE_DIR, f"snapshot_{date_str}.json")


def save_snapshot(repos):
    snap = {"date": TODAY, "repos": {
        full: {"stars": r.get("stargazers_count", 0),
               "pushed_at": r.get("pushed_at", "")}
        for full, r in repos.items()}}
    with open(snapshot_path(TODAY), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)


def find_history_snapshot(days_ago):
    for offset in range(0, 4):
        d = (TODAY_DT - timedelta(days=days_ago - offset)).strftime("%Y-%m-%d")
        p = snapshot_path(d)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f).get("repos", {})
    return None


# ============================================================
# 视图 + 栏目算法
# ============================================================
def repo_view(repo, hist_repos=None):
    full = repo.get("full_name", "")
    stars = repo.get("stargazers_count", 0)
    delta = None
    if hist_repos and full in hist_repos:
        delta = stars - hist_repos[full].get("stars", stars)
    return {
        "full": full,
        "name": full.split("/", 1)[-1] if "/" in full else full,
        "stars": stars,
        "lang": repo.get("language") or "—",
        "desc": (repo.get("description") or "").strip() or "（无描述）",
        "url": repo.get("html_url", ""),
        "pushed": repo.get("pushed_at", ""),
        "delta": delta,
        "tags": repo.get("_tags", set()),
        "track": repo.get("_track", ""),
    }


def has_delta(v):
    return v["delta"] is not None


def section_hot(views, top_n=HOT_TOP_N):
    """本周热门：主轨项目，按周增量降序（无增量则按star）。"""
    main = [v for v in views if v["track"] == "主轨"]
    with_delta = [v for v in main if has_delta(v)]
    if len(with_delta) >= top_n:
        return sorted(with_delta, key=lambda x: x["delta"], reverse=True)[:top_n], True
    return sorted(main, key=lambda x: x["stars"], reverse=True)[:top_n], False


def section_emerging(views, top_n=EMERGING_TOP_N):
    """新锐发现：副轨项目，按 star 降序。"""
    new = sorted([v for v in views if v["track"] == "新锐"],
                 key=lambda x: x["stars"], reverse=True)
    return new[:top_n]


def section_spotlight(hot_items):
    """本周重点解读：从热门榜 Top10 里选增量最高的。

    只从热门榜选，保证选中的一定是核心 AI×DB 项目，
    不会选到「顺便涉及数据库」的边缘项目。
    """
    if not hot_items:
        return None
    # 优先选有正增量的
    with_delta = [v for v in hot_items if has_delta(v) and v["delta"] > 0]
    if with_delta:
        return max(with_delta, key=lambda x: x["delta"])
    # 兜底：选热门榜第一个（star 最高）
    return hot_items[0]


# ============================================================
# 格式化
# ============================================================
def fmt_stars(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def fmt_delta(delta):
    if delta is None:
        return "—"
    return f"+{fmt_stars(delta)}" if delta > 0 else (fmt_stars(delta) if delta < 0 else "—")


def fmt_tags(tags):
    if not tags:
        return ""
    shown = []
    for t in sorted(tags):
        if t.startswith("新锐/"):
            shown.append(t.split("/", 1)[1])
        elif t != "主轨":
            shown.append(t)
    return "".join(f"[{s}]" for s in shown) if shown else ""


def days_ago_label(iso_str):
    try:
        dt = datetime.strptime(iso_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return f"{max((TODAY_DT - dt).days, 0)}天前"
    except Exception:
        return iso_str or "—"


def render_entry(idx, v):
    tag_str = fmt_tags(v["tags"])
    title = f"**{idx}. {v['full']}**" + (f" {tag_str}" if tag_str else "")
    desc = v.get("zh_desc") or v["desc"]
    meta = [f"⭐ {fmt_stars(v['stars'])}", v["lang"]]
    if has_delta(v):
        meta.append(f"📈 {fmt_delta(v['delta'])}/周")
    meta.append(f"更新 {days_ago_label(v['pushed'])}")
    return "\n".join([title, desc, f"🔗 {v['url']}", " ｜ ".join(meta), ""])


def count_issues():
    """期数 = output/ 根目录下已发布的周报 .md 数 + 1。
    只数根目录（正式周报），不数 draft/ 子目录（每日草稿）。"""
    if not os.path.isdir(OUTPUT_DIR):
        return 1
    # 只数直接位于 OUTPUT_DIR 下的 .md（跳过子目录如 draft/）
    files = [f for f in os.listdir(OUTPUT_DIR)
             if f.endswith(".md") and os.path.isfile(os.path.join(OUTPUT_DIR, f))]
    return len(files) + 1


def is_publish_day():
    """今天是否为发布日（默认周一）。发布日才更新 README、把周报放 output/ 根目录。"""
    return TODAY_DT.weekday() == PUBLISH_WEEKDAY


def _readme_path():
    return os.path.join(HERE, "README.md")


def _extract_latest_block(md_text):
    """从周报 .md 提取要展示在 README「本期周报」区块的内容。
    策略：去掉第一行的 H1 标题（README 有自己的标题），其余作为本期正文。"""
    lines = md_text.splitlines()
    # 跳过开头的 # 标题行和紧跟的空行
    out = []
    skipped_title = False
    for ln in lines:
        if not skipped_title and ln.startswith("# "):
            skipped_title = True
            continue
        out.append(ln)
    # 去掉首尾空行
    return "\n".join(out).strip()


def _latest_summary(md_text, md_relpath, issue_no, date_str):
    """组装 README 顶部的「本期周报」区块 HTML。"""
    body = _extract_latest_block(md_text)
    header = (
        f"<!-- LATEST:START --> 本期周报区块由脚本 update_readme() 自动维护，请勿手动编辑此段 -->\n"
        f"> 📖 **本期周报**：[第 {issue_no} 期 · {date_str}]({md_relpath})\n"
        f"> 📚 **历史周报**：见文末[「往期周报」](#往期周报)\n"
        f"\n---\n\n"
    )
    footer = f"\n<!-- LATEST:END -->"
    return header + body + footer


def _insert_archive_row(content, md_relpath, issue_no, date_str):
    """往「往期周报」表格插入一行（最新期在最上，即表头分隔线之后）。
    做法：把 ARCHIVE 区块里的表格行抽出来，重建为 干净的表格。"""
    start_tag, end_tag = "<!-- ARCHIVE:START -->", "<!-- ARCHIVE:END -->"
    i, j = content.find(start_tag), content.find(end_tag)
    if i == -1 or j == -1:
        return content
    block = content[i + len(start_tag):j]

    # 收集现有表格数据行（形如 | 第 N 期 | ... |，跳过表头和分隔线）
    existing = [ln for ln in block.splitlines()
                if re.match(r"^\|\s*第\s*\d+\s*期", ln)]
    new_row = f"| 第 {issue_no} 期 | {date_str} | [{md_relpath}]({md_relpath}) |"
    rows = [new_row] + existing  # 新期数置顶

    # 重建表格：表头 + 分隔线 + 数据行
    table = ["", "| 期数 | 日期 | 链接 |", "|------|------|------|"] + rows + [""]
    new_block = "\n".join(table)
    return content[:i + len(start_tag)] + new_block + content[j:]


def update_readme(md_text, md_path):
    """发布日调用：用最新周报更新 README 的「本期周报」+「往期周报」。
    md_path 为周报文件绝对路径，用于换算 README 里的相对链接。"""
    readme_p = _readme_path()
    if not os.path.exists(readme_p):
        print("    [update_readme] 未找到 README.md，跳过")
        return
    with open(readme_p, "r", encoding="utf-8") as f:
        content = f.read()

    # 期数 & 相对路径 & 日期（日期从文件名提取，比 TODAY 更稳健）
    issue_no = count_issues()
    md_relpath = os.path.relpath(md_path, HERE).replace("\\", "/")
    date_str = os.path.splitext(os.path.basename(md_path))[0]  # output/2026-08-08.md → 2026-08-08

    # 1. 替换「本期周报」区块
    start_tag, end_tag = "<!-- LATEST:START -->", "<!-- LATEST:END -->"
    i, j = content.find(start_tag), content.find(end_tag)
    if i != -1 and j != -1:
        new_latest = _latest_summary(md_text, md_relpath, issue_no, date_str)
        content = content[:i] + new_latest + content[j + len(end_tag):]
    else:
        print("    [update_readme] 未找到 LATEST 标记，跳过本期区块")

    # 2. 往「往期周报」插入一行
    content = _insert_archive_row(content, md_relpath, issue_no, date_str)

    with open(readme_p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"    [update_readme] 已更新 README：第 {issue_no} 期 · {date_str}")


def render_markdown(views, hot_items, hot_is_delta, emerging, spotlight, spotlight_text):
    issue = count_issues()
    parts = [f"# 📋 AI×DB 周报 · 第 {issue} 期 | {TODAY}", ""]

    # 今日聚焦
    focus = []
    if hot_items:
        top = hot_items[0]
        if has_delta(top):
            focus.append(f"🔥 本周增长王：**{top['name']}**（📈 {fmt_delta(top['delta'])}/周）")
        else:
            focus.append(f"🔥 最受关注：**{top['name']}**（⭐{fmt_stars(top['stars'])}）")
    if emerging:
        focus.append(f"🆕 新项目：**{emerging[0]['name']}**（⭐{fmt_stars(emerging[0]['stars'])}）")
    if spotlight:
        focus.append(f"🎯 重点解读：**{spotlight['name']}**")
    if focus:
        parts += ["**📌 今日聚焦**", ""] + focus + ["", "---", ""]

    # 本周热门
    parts.append("## 🔥 本周热门 Top10")
    if not hot_is_delta:
        parts += [f"> 💡 数据积累中：需连续运行 {DELTA_DAYS} 天后展示真实「周 star 增量」。"
                  f"本期暂按 star 绝对值排序。", ""]
    for i, v in enumerate(hot_items, 1):
        parts.append(render_entry(i, v))

    # 新锐发现
    if emerging:
        parts += ["**🆕 新锐发现**（近14天新建，早期项目）", ""]
        for i, v in enumerate(emerging, 1):
            parts.append(render_entry(i, v))

    # 本周重点解读
    if spotlight:
        tag_str = fmt_tags(spotlight["tags"])
        title = f"**{spotlight['full']}**" + (f" {tag_str}" if tag_str else "")
        parts += ["**🎯 本周重点解读**", "", title, "",
                  spotlight_text or spotlight.get("zh_desc") or spotlight["desc"], ""]
        delta_str = f" 📈 {fmt_delta(spotlight['delta'])}/周" if has_delta(spotlight) else ""
        parts.append(f"⭐ {fmt_stars(spotlight['stars'])}{delta_str} ｜ {spotlight['lang']} ｜ 更新 {days_ago_label(spotlight['pushed'])}")
        parts.append("")

    parts += ["---", "💬 互动：本周你最关注哪个项目？欢迎留言。", "",
              f"<sub>由 ai_db_weekly 自动采集于 {TODAY}，候选池 {len(views)} 个项目。介绍基于各项目 README 由 AI 生成。</sub>"]
    return "\n".join(parts)


# ============================================================
# 主流程
# ============================================================
def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"=== AI×DB 周报采集 {TODAY} ===")
    print(f"[+] GITHUB_TOKEN: {'已加载' if GITHUB_TOKEN else '未设置'}")
    print(f"[+] AI_API_KEY: {'已加载(' + AI_MODEL + ')' if AI_API_KEY else '未设置'}")

    # 1. 双轨采集 → 返回 (精筛结果, 全部初筛项目)
    print("\n[1/4] 双轨采集...")
    repos, all_candidates = fetch_all()
    print(f"\n    精筛结果: {len(repos)} 个")
    if not repos:
        print("[x] 未采集到数据", file=sys.stderr)
        sys.exit(1)

    # 2. 快照 — 存全部初筛项目(不只是精筛后的)，保证进榜项目都有历史
    print(f"\n[2/4] 保存快照（{len(all_candidates)} 个项目）...")
    save_snapshot(all_candidates)

    # 3. 增量
    print(f"\n[3/4] 查找 {DELTA_DAYS} 天前历史快照...")
    hist = find_history_snapshot(DELTA_DAYS)
    print(f"    → {'命中(' + str(len(hist)) + '个)，展示真实周增量' if hist else '未找到，兜底排序'}")

    # 4. 榜单
    print("\n[4/4] 生成榜单...")
    views = [repo_view(r, hist) for r in repos.values()]
    hot_items, hot_is_delta = section_hot(views)
    hot_names = {v["full"] for v in hot_items}
    spotlight = section_spotlight(hot_items)
    spotlight_names = {spotlight["full"]} if spotlight else set()
    emerging = section_emerging(views)

    # AI 介绍
    listed = hot_items + emerging + ([spotlight] if spotlight else [])
    if AI_API_KEY:
        print(f"\n[AI] 为 {len(listed)} 个项目抓 README + 生成中文介绍...")
    ai_cache = _load_ai_cache()
    fill_zh_descs(listed, ai_cache)

    spotlight_text = None
    if spotlight and AI_API_KEY:
        print(f"[AI] 生成「本周重点解读」: {spotlight['full']}")
        readme = fetch_readme(spotlight["full"])
        spotlight_text = gen_spotlight(
            spotlight["full"], spotlight["desc"], spotlight["lang"],
            spotlight["stars"], spotlight.get("delta") or 0, readme, ai_cache)
    _save_ai_cache(ai_cache)

    # 渲染输出
    # 发布日（周一）→ 正式周报放 output/ 根目录；其余日子 → 草稿放 output/draft/
    publish = is_publish_day()
    out_dir = OUTPUT_DIR if publish else DRAFT_DIR
    os.makedirs(out_dir, exist_ok=True)
    role = "发布(正式周报)" if publish else f"非发布日(草稿, PUBLISH_WEEKDAY={PUBLISH_WEEKDAY})"
    print(f"\n[输出] 今天 {TODAY} → {role}")

    md = render_markdown(views, hot_items, hot_is_delta, emerging, spotlight, spotlight_text)
    md_path = os.path.join(out_dir, f"{TODAY}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] 已生成: {md_path}")

    json_path = os.path.join(out_dir, f"{TODAY}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"hot": hot_items, "emerging": emerging,
                   "spotlight": spotlight, "spotlight_text": spotlight_text,
                   "hot_is_delta": hot_is_delta},
                  f, ensure_ascii=False, indent=2,
                  default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    print(f"[OK] 原始数据: {json_path}")

    # 发布日：更新 README（本期周报 + 往期目录）
    if publish:
        print("\n[README] 发布日，更新首页...")
        update_readme(md, md_path)

    print("\n" + "=" * 50 + "\n预览:\n" + "=" * 50)
    print(md)

    # 5. 推送到飞书（可选）
    if FEISHU_WEBHOOK:
        print("\n[推送] 发送到飞书...")
        ok = push_to_feishu(md)
        print(f"    → {'推送成功' if ok else '推送失败'}")


# ============================================================
# 飞书机器人推送
# ============================================================
def push_to_feishu(md_text):
    """把周报 Markdown 推送到飞书群机器人。

    需要在 .env 配置 FEISHU_WEBHOOK（飞书群自定义机器人的 webhook 地址）。
    """
    if not FEISHU_WEBHOOK:
        return False
    payload = {
        "msg_type": "text",
        "content": {"text": md_text[:30000]},  # 飞书单条消息上限 30k 字符
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(FEISHU_WEBHOOK, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("code", -1) == 0 or result.get("StatusCode", -1) == 0
    except Exception as e:
        print(f"    [飞书] 推送失败: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    main()
