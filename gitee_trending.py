#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI×DB 周报 - Gitee 项目采集脚本

与 db_trending.py（GitHub 源）平行，采集 Gitee 上的 AI×数据库 开源项目。

Gitee API v5 与 GitHub 的关键差异（决定了本脚本的采集策略）：
  - 仓库详情字段 stargazers_count / pushed_at / created_at / language 与 GitHub 同名
  - **/v5/search/repositories 接口长期返回空**（Gitee 平台已知 bug，无论认证与否）
  - 但 /v5/search/issues 可用，issue 结果内嵌 repository 字段，可间接发现仓库
  - issue 内 repository 不含 star/时间，需额外调 /v5/repos/{owner}/{repo} 补全
  - 不支持 topic: / stars:> / created:> / pushed:> 限定符，只能用纯关键词 q 搜索
  - 不返回 topics 字段；README 接口 GET /v5/repos/{owner}/{repo}/readme 返回 {content: base64}

因此采集策略改为「搜 issue 发现仓库 + 详情补全 + 代码层全部过滤」：
  DB词 × AI词 笛卡尔积构造搜索词对 → 搜 issue 提取仓库 → 调详情补全字段
  → 代码层做 star/时间/黑名单/双重验证/README 精筛

━━━ 后期维护指南 ━━━
要改采集范围/门槛，只需修改下方 CONFIG 区，不用动其他代码。
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
CACHE_DIR = os.path.join(HERE, "cache_gitee")        # Gitee 专属缓存，与 GitHub 的 cache/ 隔离
OUTPUT_DIR = os.path.join(HERE, "output_gitee")       # Gitee 专属输出，与 output/ 隔离
DRAFT_DIR = os.path.join(OUTPUT_DIR, "draft")         # 非发布日的草稿目录

# --- 采集范围（改这里调整「抓什么」）---
# 采集策略（重要）：Gitee 的 /v5/search/repositories 接口长期返回空（平台已知 bug），
# 改用「/v5/search/issues 间接发现仓库 + /v5/repos/{owner}/{repo} 补全字段」的变通链路：
#   用下方 SEARCH_QUERIES 里的高区分度复合词搜 issue → 提取被讨论的仓库
#   → 调仓库详情补全 star/pushed_at/created_at/language
#   → 代码层做 star 阈值 + 时间窗口 + 黑名单 + 双重验证 + README 精筛
#
# 为什么用预定义复合词而非「DB词×AI词笛卡尔积」：
#   issue 搜索 q="mysql agent" 会命中大量教程/笔记里的 mysql/agent 字样，噪音极大。
#   改用本身就表达「AI×数据库」语义的复合词（text2sql/AI SQL/数据库 大模型 等），
#   召回率更高、请求数更少、噪音更低。想扩大搜索面，往 SEARCH_QUERIES 加词即可。

# 搜索词列表：每个词都会被送进 /search/issues?q=<词>，提取命中的仓库。
# 想加新搜索面，只需往列表加一个字符串。
SEARCH_QUERIES = [
    # AI × SQL / NL2SQL（核心方向，区分度最高）
    "text2sql", "nl2sql", "text-to-sql", "NL2SQL",
    "自然语言 SQL", "自然语言查询", "AI SQL", "LLM SQL",
    # AI × 数据库（中文为主，Gitee 上中文项目多）
    "数据库 AI", "AI 数据库", "数据库 大模型", "大模型 数据库",
    "智能体 数据库", "数据库 智能",
    # 具体产品名（精准命中已知 AI×DB 项目）
    "Chat2DB", "chatdb", "db-gpt", "dbgpt", "ai4db",
    # AI Agent / RAG 偏向（可能涉及数据库）
    "数据库 agent", "RAG 数据库",
]

# 数据库名称信号词：验证阶段用，项目描述/名字里命中任一即视为数据库相关
# 含国产数据库 / 信创生态（Gitee 上更丰富）
DB_KEYWORDS = [
    # 关系型 / 主流开源
    "mysql", "postgres", "postgresql", "sqlite", "mariadb", "oracle",
    "tidb", "cockroachdb", "oceanbase", "opengauss", "polardb",
    "sqlserver", "db2",
    # 国产数据库 / 信创生态
    "gaussdb", "dameng", "达梦", "kingbase", "人大金仓",
    "shardingsphere", "doris", "clickhouse",
    # SQL 泛化（覆盖 text2sql 等场景）
    "sql",
]

# AI 信号词：验证阶段用，命中任一即视为 AI 相关
# 含中文词（Gitee 上中文项目多）
AI_KEYWORDS = [
    "agent", "mcp", "llm", "gpt", "copilot",
    "text2sql", "nl2sql", "nl-to-sql",
    "rag", "skill", "chatbot", "ai-native",
    "natural language", "embedding", "openai", "claude",
    "language model", "prompt", "genai", "ai-driven",
    "ai assistant",
    # 中文 AI 词
    "大模型", "自然语言", "智能体",
]

# README 精筛：AI 词命中次数 ≥ 此值才保留
README_AI_MIN_HITS = 3

# --- 门槛（改这里调整「抓多严」）---
# 注意：Gitee star 量级远小于 GitHub，门槛要相应调低
MAIN_STARS_MIN = 20            # 主轨最低 star（GitHub 版是 50，Gitee 调低到 20）
MAIN_ACTIVE_DAYS = 180         # 主轨活跃窗口（近 N 天有 pushed_at）
EMERGING_STARS_MIN = 2         # 副轨最低 star
EMERGING_CREATED_DAYS = 14     # 副轨新建窗口（近 N 天 created_at）
DELTA_DAYS = 7                 # 周增量计算的天数
PUBLISH_WEEKDAY = 0            # 周几发布周报：0=周一 1=周二 ... 6=周日

# --- 搜索强度（改这里调整「搜多少」）---
# 遍历 SEARCH_QUERIES 列表搜索 issue，每个词翻若干页（issue 搜索 per_page 上限 50）
MAIN_PAGES_PER_QUERY = 2       # 主轨每个搜索词最多翻几页（2 页 × 50 = 最多 100 条 issue/词）
EMERGING_PAGES_PER_QUERY = 1   # 副轨每个搜索词最多翻几页

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
GITEE_TOKEN = os.environ.get("GITEE_TOKEN", "").strip()
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
# Gitee API
# ============================================================
GITEE_API_ROOT = "https://gitee.com/api/v5"


def gitee_get(path, params=None):
    """Gitee API GET。认证用 access_token 查询参数（Gitee 习惯用法）。

    返回解析后的 JSON；失败返回 None（与 github_get 行为一致）。
    """
    params = dict(params or {})
    if GITEE_TOKEN:
        params["access_token"] = GITEE_TOKEN
    url = f"{GITEE_API_ROOT}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": "ai-db-weekly-gitee/1.0"}
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


def gitee_search_repos_via_issues(q, per_page=20, page=1):
    """【关键变通】通过搜索 issue 间接发现仓库。

    背景：Gitee 的 /v5/search/repositories 接口长期返回空（平台已知 bug，见
    https://gitee.com/oschina/git-osc/issues/ICCSIY），未认证或权限不足时恒为空。
    但 /v5/search/issues 可用，且每条 issue 结果内嵌 repository 字段，
    可据此提取出「被讨论过的仓库」。

    缺点：issue 内的 repository 字段只有基本标识（full_name/description/html_url），
    不含 star/pushed_at/created_at/language，需后续调 gitee_repo_detail 补全。

    返回去重后的仓库基本列表 [{full_name, description, html_url, ...}, ...]。
    """
    data = gitee_get("/search/issues",
                     {"q": q, "per_page": per_page, "page": page})
    if not isinstance(data, list):
        return []
    seen = set()
    repos = []
    for it in data:
        repo = it.get("repository") or {}
        full = repo.get("full_name")
        if full and full not in seen:
            seen.add(full)
            repos.append(repo)
    return repos


def gitee_repo_detail(full_name):
    """获取仓库详情，补全 issue 搜索缺失的字段。

    Gitee: GET /v5/repos/{owner}/{repo}，返回完整仓库对象，
    含 stargazers_count / pushed_at / created_at / language（与 GitHub 同名字段）。
    返回 None 表示获取失败。
    """
    data = gitee_get(f"/repos/{full_name}")
    return data if isinstance(data, dict) else None


def gitee_fetch_readme(full_name):
    """抓 README 前 3000 字符，让 AI 基于真实内容生成介绍。

    Gitee: GET /v5/repos/{owner}/{repo}/readme，返回 {content: base64}，
    与 GitHub readme 接口结构一致，解码方式相同。
    """
    data = gitee_get(f"/repos/{full_name}/readme")
    if data and isinstance(data, dict) and "content" in data:
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:3000]
        except Exception:
            return None
    return None


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


def gen_zh_desc(full_name, en_desc, lang, cache):
    if full_name in cache:
        return cache[full_name]
    if not AI_API_KEY:
        return en_desc or "（无描述）"
    readme = gitee_fetch_readme(full_name)
    context = f"项目README（节选）：\n{readme}" if readme else f"描述：{en_desc or '（无）'}"
    prompt = (
        f"你是数据库技术编辑。基于以下项目的真实信息，用一句话介绍它，要求：\n"
        f"1. 中文，严格控制在 60 字以内（一个短句）\n"
        f"2. 只说它是做什么的 + 一个最核心的功能或卖点\n"
        f"3. 只陈述 README 里的事实，不要臆测或夸大\n"
        f"4. 不要寒暄、不要分点、不要换行，直接输出一句话\n\n"
        f"项目名：{full_name}\n主要语言：{lang}\n{context}"
    )
    text = _call_ai_chat([{"role": "user", "content": prompt}])
    if not text:
        return en_desc or "（无描述）"
    text = text.strip().strip("\"'“”‘’")
    cache[full_name] = text
    return text


def gen_spotlight(full_name, en_desc, lang, stars, delta, readme, cache):
    cache_key = f"spotlight__{full_name}"
    if cache_key in cache:
        return cache[cache_key]
    if not AI_API_KEY:
        return None
    context = f"项目README（节选）：\n{readme}" if readme else f"描述：{en_desc or '（无）'}"
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
    text = text.strip().strip("\"'“”‘’")
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
    """初筛：描述/名字含 DB词 OR AI词（任一即可）。

    与 GitHub 版的 AND 逻辑不同，Gitee 版用 OR：
    - GitHub 上有 topic 精准分类，AND 能高效定位「既是DB又是AI」的项目
    - Gitee 无 topic，且 AI×DB 项目常呈单边形态：
      · AI 平台/知识库（MaxKB/langchat/solon-ai）—— 有 AI 词、无具体库名
      · 数据库内核/工具（opengauss/kwdb）—— 有 DB 词、无 AI 词
      若要求 AND 会把这两类真目标全过滤掉。
    - 因此初筛放宽为 OR，真正的质量把关交给 README 精筛（AI词命中≥3次），
      噪音（Spring脚手架等）在 README 里不会有 AI 词，会被精筛剔除。

    注意：Gitee 仓库对象不返回 topics 字段，这里只检查 name + description。
    """
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    # topics 字段 Gitee 不返回，get 默认空列表，兼容无影响
    topics = " ".join(repo.get("topics", []) or []).lower()
    text = f"{name} {desc} {topics}"
    has_db = any(p.search(text) for p in _DB_REGEX)
    has_ai = any(p.search(text) for p in _AI_REGEX)
    return has_db or has_ai


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

    用于精筛：靠关键词蹭 AI 标签但 README 里没真讲 AI 的项目会被剔除。
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
# 关键词搜索（Gitee 版核心：搜 issue 发现仓库 + 详情补全 + 代码层过滤）
# ============================================================
def _fetch_track(track_name, stars_min, time_filter_fn, pages_per_query, raw_pool=None):
    """通用采集：遍历 SEARCH_QUERIES 搜 issue → 提取仓库 → 详情补全 → 代码层过滤。

    采集链路（Gitee 变通方案，因 /search/repositories 接口失效）：
      1. gitee_search_repos_via_issues(q) —— 搜 issue，提取内嵌的 repository 基本信息列表
      2. gitee_repo_detail(full)         —— 调仓库详情补全 stargazers_count/pushed_at/created_at/language
      3. 代码层过滤：star 阈值 + 时间窗口(time_filter_fn) + 黑名单 + 双重关键词验证

    与 GitHub 版的关键区别：
    - GitHub 版靠 API 的 stars:>/pushed:>/created:> 限定符过滤，代码只做关键词验证
    - Gitee 版只能按关键词搜 issue，star/时间字段需额外调详情接口，过滤全部在代码层

    raw_pool: 传入一个 dict，所有补全过的项目都会存进去（用于全量快照）。
    """
    merged = {}
    for q in SEARCH_QUERIES:
        for page in range(1, pages_per_query + 1):
            # 步骤1：搜 issue 提取仓库基本列表（只含 full_name/description/html_url）
            basic_repos = gitee_search_repos_via_issues(q, per_page=50, page=page)
            if not basic_repos:
                break
            kept = 0
            for basic in basic_repos:
                full = basic.get("full_name", "")
                if not full:
                    continue
                # 跨词/跨页去重：已在合并结果里的不再处理
                if full in merged:
                    continue
                # 步骤2：调详情补全字段（issue 内 repository 不含 star/时间）
                if raw_pool is not None and full in raw_pool:
                    it = raw_pool[full]  # 复用已补全过的，避免重复调详情
                else:
                    it = gitee_repo_detail(full)
                    if not it:
                        continue
                # 代码层 star 过滤（替代 GitHub 的 stars:> 限定符）
                if it.get("stargazers_count", 0) < stars_min:
                    continue
                # 代码层时间过滤（替代 GitHub 的 pushed:>/created:> 限定符）
                if not time_filter_fn(it):
                    continue
                # 全量记录到 raw_pool（不管是否通过筛选，都存 star 供增量对比）
                if raw_pool is not None and full not in raw_pool:
                    raw_pool[full] = it
                # 初筛：黑名单 + 双重关键词
                if is_blacklisted(it) or not is_ai_db(it):
                    continue
                it["_track"] = track_name
                it["_tags"] = {track_name}
                merged[full] = it
                kept += 1
            print(f"  · {track_name}[{q}]第{page}页: 搜到{len(basic_repos)}仓 留{kept}")
            time.sleep(1)  # 节流
            if len(basic_repos) < 50:
                break
    return merged


def fetch_main_track(raw_pool):
    """主轨：star>=MAIN_STARS_MIN 且 近 MAIN_ACTIVE_DAYS 活跃（代码层过滤 pushed_at）。"""
    cutoff = daterange_iso(MAIN_ACTIVE_DAYS)

    def active_filter(it):
        return (it.get("pushed_at", "") or "")[:10] >= cutoff

    return _fetch_track("主轨", MAIN_STARS_MIN, active_filter,
                        MAIN_PAGES_PER_QUERY, raw_pool=raw_pool)


def fetch_emerging_track(raw_pool):
    """副轨：star>=EMERGING_STARS_MIN 且 近 EMERGING_CREATED_DAYS 创建（代码层过滤 created_at）。"""
    cutoff = daterange_iso(EMERGING_CREATED_DAYS)

    def created_filter(it):
        return (it.get("created_at", "") or "")[:10] >= cutoff

    return _fetch_track("新锐", EMERGING_STARS_MIN, created_filter,
                        EMERGING_PAGES_PER_QUERY, raw_pool=raw_pool)


def fetch_all():
    """双轨采集 → 合并去重 → README 精筛。

    返回 (精筛结果, 全量快照数据)。
    """
    raw_pool = {}

    print("  === 主轨: 复合关键词搜issue stars>=%d 近%d天 ===" % (MAIN_STARS_MIN, MAIN_ACTIVE_DAYS))
    main = fetch_main_track(raw_pool)
    print(f"  主轨初筛: {len(main)} 个（全量池: {len(raw_pool)} 个）\n")

    print("  === 副轨: 复合关键词搜issue stars>=%d 近%d天创建 ===" % (EMERGING_STARS_MIN, EMERGING_CREATED_DAYS))
    emerging = fetch_emerging_track(raw_pool)
    print(f"  副轨初筛: {len(emerging)} 个（全量池: {len(raw_pool)} 个）")

    # 合并：副轨中已在主轨的（star已超门槛），归主轨
    for full, repo in emerging.items():
        if full not in main:
            main[full] = repo
    print(f"\n  合并去重: {len(main)} 个（全量池: {len(raw_pool)} 个）")

    # README 精筛：抓 README，AI 词命中 ≥3 次才保留
    print(f"\n  === README 精筛（AI词命中≥{README_AI_MIN_HITS}次）===")
    filtered = {}
    removed = []
    for full, repo in main.items():
        readme = gitee_fetch_readme(full)
        hits = count_ai_hits_in_readme(readme)
        if hits >= README_AI_MIN_HITS:
            repo["_readme"] = readme  # 缓存，后面生成介绍时复用
            filtered[full] = repo
        else:
            removed.append((full, hits))
    print(f"  README 精筛后: {len(filtered)} 个（剔除 {len(removed)} 个）")
    for full, hits in removed:
        print(f"    ✗ {full} (AI命中{hits}次)")

    return filtered, raw_pool


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
    """本周重点解读：从热门榜 Top10 里选增量最高的。"""
    if not hot_items:
        return None
    with_delta = [v for v in hot_items if has_delta(v) and v["delta"] > 0]
    if with_delta:
        return max(with_delta, key=lambda x: x["delta"])
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
    """卡片型排版：标题行(含元信息) + 一句话介绍 + 链接，用分割线分隔项目。"""
    tag_str = fmt_tags(v["tags"])
    meta = [f"⭐{fmt_stars(v['stars'])}", v["lang"]]
    if has_delta(v):
        meta.append(f"📈{fmt_delta(v['delta'])}/周")
    meta.append(f"更新 {days_ago_label(v['pushed'])}")
    meta_str = " · ".join(meta)
    title = f"**{idx}. {v['full']}**" + (f" {tag_str}" if tag_str else "") + f"  {meta_str}"
    desc = v.get("zh_desc") or v["desc"]
    return "\n".join(["", "---", "", title, f"> {desc}", "", f"🔗 {v['url']}", ""])


def count_issues():
    """本期期数 = output_gitee/ 根目录下「除今天这份外」的已发布周报 .md 数 + 1。"""
    if not os.path.isdir(OUTPUT_DIR):
        return 1
    today_file = f"{TODAY}.md"
    files = [f for f in os.listdir(OUTPUT_DIR)
             if f.endswith(".md")
             and f != today_file
             and os.path.isfile(os.path.join(OUTPUT_DIR, f))]
    return len(files) + 1


def is_publish_day():
    """今天是否为发布日（默认周一）。"""
    return TODAY_DT.weekday() == PUBLISH_WEEKDAY


def _readme_path():
    """Gitee 源专属 README。"""
    return os.path.join(HERE, "README_gitee.md")


def _extract_latest_block(md_text):
    """从周报 .md 提取要展示在 README「本期周报」区块的内容（去掉首行 H1 标题）。"""
    lines = md_text.splitlines()
    out = []
    skipped_title = False
    for ln in lines:
        if not skipped_title and ln.startswith("# "):
            skipped_title = True
            continue
        out.append(ln)
    return "\n".join(out).strip()


def _latest_summary(md_text, md_relpath, issue_no, date_str):
    """组装 README 顶部的「本期周报」区块。"""
    body = _extract_latest_block(md_text)
    header = (
        f"<!-- LATEST:START --> 本期周报区块由脚本自动维护，请勿手动编辑此段 -->\n"
        f"> 📖 **本期周报**：[第 {issue_no} 期 · {date_str}]({md_relpath})\n"
        f"> 📚 **历史周报**：见文末[「往期周报」](#往期周报)\n"
        f"\n---\n\n"
    )
    footer = f"\n<!-- LATEST:END -->"
    return header + body + footer


def _insert_archive_row(content, md_relpath, issue_no, date_str):
    """往「往期周报」表格插入一行（最新期置顶），按期数去重。"""
    start_tag, end_tag = "<!-- ARCHIVE:START -->", "<!-- ARCHIVE:END -->"
    i, j = content.find(start_tag), content.find(end_tag)
    if i == -1 or j == -1:
        return content
    block = content[i + len(start_tag):j]
    existing = [ln for ln in block.splitlines()
                if re.match(r"^\|\s*第\s*\d+\s*期", ln)]
    new_row = f"| 第 {issue_no} 期 | {date_str} | [{md_relpath}]({md_relpath}) |"
    existing = [ln for ln in existing
                if not re.match(rf"^\|\s*第\s*{issue_no}\s*期", ln)]
    rows = [new_row] + existing
    table = ["", "| 期数 | 日期 | 链接 |", "|------|------|------|"] + rows + [""]
    new_block = "\n".join(table)
    return content[:i + len(start_tag)] + new_block + content[j:]


def update_readme(md_text, md_path):
    """发布日调用：用最新周报更新 README_gitee 的「本期周报」+「往期周报」。"""
    readme_p = _readme_path()
    if not os.path.exists(readme_p):
        print("    [update_readme] 未找到 README_gitee.md，跳过")
        return
    with open(readme_p, "r", encoding="utf-8") as f:
        content = f.read()

    issue_no = count_issues()
    md_relpath = os.path.relpath(md_path, HERE).replace("\\", "/")
    date_str = os.path.splitext(os.path.basename(md_path))[0]

    start_tag, end_tag = "<!-- LATEST:START -->", "<!-- LATEST:END -->"
    i, j = content.find(start_tag), content.find(end_tag)
    if i != -1 and j != -1:
        new_latest = _latest_summary(md_text, md_relpath, issue_no, date_str)
        content = content[:i] + new_latest + content[j + len(end_tag):]
    else:
        print("    [update_readme] 未找到 LATEST 标记，跳过本期区块")

    content = _insert_archive_row(content, md_relpath, issue_no, date_str)

    with open(readme_p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"    [update_readme] 已更新 README_gitee：第 {issue_no} 期 · {date_str}")


def render_markdown(views, hot_items, hot_is_delta, emerging, spotlight, spotlight_text):
    issue = count_issues()
    parts = [f"# 📋 AI×DB 周报（Gitee 源）· 第 {issue} 期 | {TODAY}", ""]

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

    parts.append("## 🔥 本周热门 Top10")
    if not hot_is_delta:
        parts += [f"> 💡 数据积累中：需连续运行 {DELTA_DAYS} 天后展示真实「周 star 增量」。"
                  f"本期暂按 star 绝对值排序。", ""]
    for i, v in enumerate(hot_items, 1):
        parts.append(render_entry(i, v))

    if emerging:
        parts += ["**🆕 新锐发现**（近14天新建，早期项目）", ""]
        for i, v in enumerate(emerging, 1):
            parts.append(render_entry(i, v))

    if spotlight:
        tag_str = fmt_tags(spotlight["tags"])
        title = f"**{spotlight['full']}**" + (f" {tag_str}" if tag_str else "")
        parts += ["**🎯 本周重点解读**", "", title, "",
                  spotlight_text or spotlight.get("zh_desc") or spotlight["desc"], ""]
        delta_str = f" 📈 {fmt_delta(spotlight['delta'])}/周" if has_delta(spotlight) else ""
        parts.append(f"⭐ {fmt_stars(spotlight['stars'])}{delta_str} ｜ {spotlight['lang']} ｜ 更新 {days_ago_label(spotlight['pushed'])}")
        parts.append("")

    parts += ["---", "💬 互动：本周你最关注哪个项目？欢迎留言。", "",
              f"<sub>由 gitee_trending 自动采集于 {TODAY}（数据源：Gitee），候选池 {len(views)} 个项目。介绍基于各项目 README 由 AI 生成。</sub>"]
    return "\n".join(parts)


# ============================================================
# 主流程
# ============================================================
def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"=== AI×DB 周报采集（Gitee 源）{TODAY} ===")
    print(f"[+] GITEE_TOKEN: {'已加载' if GITEE_TOKEN else '未设置（未认证，限速更严）'}")
    print(f"[+] AI_API_KEY: {'已加载(' + AI_MODEL + ')' if AI_API_KEY else '未设置'}")

    # 1. 双轨采集
    print("\n[1/4] 双轨采集（DB×AI词对交叉搜索）...")
    repos, all_candidates = fetch_all()
    print(f"\n    精筛结果: {len(repos)} 个")
    if not repos:
        print("[x] 未采集到数据", file=sys.stderr)
        sys.exit(1)

    # 2. 快照
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
    spotlight = section_spotlight(hot_items)
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
        readme = gitee_fetch_readme(spotlight["full"])
        spotlight_text = gen_spotlight(
            spotlight["full"], spotlight["desc"], spotlight["lang"],
            spotlight["stars"], spotlight.get("delta") or 0, readme, ai_cache)
    _save_ai_cache(ai_cache)

    # 渲染输出
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
    """把周报 Markdown 推送到飞书群机器人。"""
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
