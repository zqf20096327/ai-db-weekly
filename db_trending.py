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
import urllib.error
from datetime import datetime, timedelta, timezone

# ╔══════════════════════════════════════════════════════════╗
# ║  CONFIG 区 — 所有可调参数集中在这里，改这里就够了          ║
# ╚══════════════════════════════════════════════════════════╝

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache")
OUTPUT_DIR = os.path.join(HERE, "output")
DRAFT_DIR = os.path.join(OUTPUT_DIR, "draft")   # 非发布日的草稿目录

# --- 采集范围（改这里调整「抓什么」）---
# 搜索方式：两轨都搜索下面这些 topic（OR 组合），只是 star/时间不同
# 主轨: (topic 列表) stars:>50 pushed:>180天
# 副轨: (topic 列表) stars:>2  created:>14天
# 想加新 topic 只需往列表加一个字符串，比如再加 "nl2sql"
# topic 列表大小写不敏感（GitHub topic 搜索本身不分大小写）；
# 跨 topic 重复命中时由 _fetch_track 的 merged 字典在代码层去重。
SEARCH_TOPICS = [
    "database", "oracle-database",
    "mysql", "oracle", "sqlserver", "db2",
    "postgresql", "postgres", "opengauss",
    "tidb", "oceanbase", "goldendb", "polardb",
    "yashandb", "dm", "gbase", "tdsql",
]

# 数据库名称信号词：验证阶段用，项目描述/topics/名字里命中任一即视为数据库相关
# 想加新库（如 GaussDB）只需往列表加一个字符串
DB_KEYWORDS = [
    "mysql", "postgres", "postgresql", "sqlite", "mariadb", "oracle",
    "tidb", "cockroachdb", "oceanbase", "opengauss", "polardb",
    "sqlserver", "db2",
    "goldendb", "yashandb", "gbase", "tdsql", "dameng", "kingbase",
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
# README 精筛：DB 板块要求 README 里 DB 关键词出现 ≥ 此次（剔除乱贴 topic/描述蹭词的噪音）
# 比 AI 板块宽松：纯数据库引擎的 README 常是"SQL/事务/存储"等通用 DB 词，不会反复提库名
README_DB_MIN_HITS = 2

# --- 门槛（改这里调整「抓多严」）---
MAIN_STARS_MIN = 50          # 主轨最低 star
MAIN_ACTIVE_DAYS = 180       # 主轨活跃窗口（近 N 天有更新）
EMERGING_STARS_MIN = 2       # 副轨最低 star
EMERGING_CREATED_DAYS = 14   # 副轨新建窗口（近 N 天创建）
MAIN_MAX_PAGES = 10          # 主轨分页数（每页100，10页=最多1000，GitHub上限）
DELTA_DAYS = 7               # 周增量计算的天数

# --- topic 间隔（从源头规避 search API 限速）---
# GitHub Search API 配额 30 次/分钟。单 topic 最多消耗 ~11 次请求
# (1 次探测 + 最多 10 页翻页)，在 TOPIC_INTERVAL 秒内远低于上限；
# 处理完一个 topic 后固定等待 TOPIC_INTERVAL 秒，让配额充分恢复再处理下一个，
# 这样无论多少 topic / 多少 star 桶都不会累积触发限速。时效性要求不高时设大些更稳。
TOPIC_INTERVAL = 90          # 相邻 topic 之间的间隔秒数

# --- star 分桶（突破单 query 1000 条上限）---
# GitHub Search API 单个查询硬上限 1000 条。热门 topic(如 database/postgresql)
# 在 stars:>50 下会触顶，star 50~300 的长尾项目被截断漏掉。
# 解法：先探测 total_count，超过 BUCKET_THRESHOLD 的 topic 自动按 star 区间
# 拆成多个子查询（每桶 < 1000），代码层合并去重，从而覆盖到低 star 长尾。
# 设为 0 则关闭分桶（恢复旧行为）。
BUCKET_THRESHOLD = 900       # total_count 超过此值才触发分桶
# 从高到低的分桶边界（与 MAIN_STARS_MIN 衔接）：
#   stars:>BUCKET_BOUNDS[0] | BOUNDS[1]..BOUNDS[0] | ... | MAIN_STARS_MIN..末桶
BUCKET_BOUNDS = [1000, 500, 300, 100]
PUBLISH_WEEKDAY = 0          # 周几发布周报：0=周一 1=周二 ... 6=周日

# --- 榜单条数（改这里调整「展示多少」）---
# 每个板块（AI / DB）各有四小节：本周star热点 / 新锐发现 / star总榜 / 本周解读
HOT_TOP_N = 5          # 本周 star 热点 topN（按周增量；数据积累期按 star）
EMERGING_TOP_N = 5     # 新锐发现 topN（近14天新建）
TOTAL_TOP_N = 5        # star 总榜 topN（按绝对 star）

# --- 噪音黑名单（命中即剔除）---
# 描述里含这些词的项目直接排除（第一道防线，命中即丢，不抓 README）
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
    # 游戏/娱乐类（靠乱贴 database topic 混入的噪音）
    "party game", "board game", "card game", "flappy bird",
    "flappy", "wordle", "trivia", "quiz game", "typing game",
    "mini game", "minigame", "game engine", "game jam",
    "social deduction", "vocabulary", "spelling bee",
    "jump and run", "platformer",
    # 个人/玩具项目类
    "personal website", "portfolio", "resume", "cv template",
    "boilerplate", "starter template", "landing page",
    "discord bot", "telegram bot", "slack bot",
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


class RateLimited(Exception):
    """Search API 配额耗尽(403)。抛给上层 _fetch_track，触发分桶重试。"""


def github_search_get(url):
    """search 请求：成功返回 dict；403 配额耗尽抛 RateLimited；其他失败返回 None。

    不在此处自动等待重试——把限速信号抛给 _fetch_track，由它决定是
    「等 TOPIC_INTERVAL 后对该 topic 分桶重试」还是「跳过」。
    """
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
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RateLimited()   # 配额耗尽，交给上层处理
        print(f"[!] 认证问题: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[!] 请求失败: {e}", file=sys.stderr)
        return None


def search_repos(query, per_page=100, page=1):
    params = {"q": query, "sort": "stars", "order": "desc",
              "per_page": per_page, "page": page}
    url = f"{API_ROOT}?{urllib.parse.urlencode(params)}"
    data = github_search_get(url)
    return data["items"] if data and "items" in data else []


def query_total_count(query):
    """探测某个 query 命中的总仓库数（只取 1 条，读 total_count）。
    用于判断单 topic 查询是否触顶 1000 上限，决定是否 star 分桶。"""
    params = {"q": query, "per_page": 1, "page": 1}
    url = f"{API_ROOT}?{urllib.parse.urlencode(params)}"
    data = github_search_get(url)
    return data.get("total_count", 0) if data else 0


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
               "User-Agent": "ai-db-weekly-bot/1.0"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:3000]
    except Exception:
        return None


def gen_zh_desc(full_name, en_desc, lang, cache, readme=None):
    """生成中文一句话介绍。优先用传入的 readme（精筛阶段已抓缓存），避免重复请求。"""
    if full_name in cache:
        return cache[full_name]
    if not AI_API_KEY:
        return en_desc or "（无描述）"
    if readme is None:
        readme = fetch_readme(full_name)
    context = f"项目README（节选）：\n{readme}" if readme else f"英文描述：{en_desc or '（无）'}"
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


def fill_zh_descs(items, cache, readme_map=None):
    """批量生成中文介绍。

    readme_map: {full_name: readme_text}，精筛阶段已抓的 README 缓存。
    优先用它，避免对每个上榜项目重复请求 README（省 API 配额、防限速）。
    """
    readme_map = readme_map or {}
    for v in items:
        readme = readme_map.get(v["full"])
        v["zh_desc"] = gen_zh_desc(v["full"], v["desc"], v["lang"], cache, readme)


# ============================================================
# 双池分类验证：DB 板块(数据库词) / AI 板块(数据库词 AND AI词)
# ============================================================
# 预编译正则（词边界，避免 rag 匹配 storage；mysql 等不需边界）
_DB_REGEX = [re.compile(rf"\b{kw}\b") if len(kw) <= 4 else re.compile(kw)
             for kw in DB_KEYWORDS]
_AI_REGEX = [re.compile(rf"\b{kw}\b", re.IGNORECASE) for kw in AI_KEYWORDS]


def _db_text(repo):
    """拼出用于关键词验证的文本（名字 + 描述 + topics，全小写）。"""
    name = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()
    topics = " ".join(repo.get("topics", []) or []).lower()
    return f"{name} {desc} {topics}"


def is_db(repo):
    """DB 板块准入：描述/topics/名字命中任一数据库信号词。
    比 AI 板块更宽——纯数据库引擎(如 TiDB/OceanBase 内核)也能进 DB 榜。"""
    text = _db_text(repo)
    return any(p.search(text) for p in _DB_REGEX)



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


def count_db_hits_in_readme(readme_text):
    """统计 README 里数据库关键词的命中次数。

    用于 DB 板块精筛：靠乱贴 topic / 描述蹭词混入的噪音（游戏、玩具项目等），
    README 里往往通篇不提数据库，命中次数很低，据此剔除。
    """
    if not readme_text:
        return 0
    text = readme_text.lower()
    total = 0
    for kw, p in zip(DB_KEYWORDS, _DB_REGEX):
        # 用与初筛相同的预编译正则统计出现次数
        total += len(p.findall(text))
    return total


# ============================================================
# 双轨搜索（两轨搜索方式+验证规则完全相同，只是 star/时间不同）
# ============================================================
def _build_query(topic, stars_min, time_filter):
    """构建单 topic 搜索查询：topic:X + star + 时间条件。
    GitHub Search API 对多 topic 的 OR 组合支持不稳定（常返回0或报错），
    所以策略是「每个 topic 单独查，代码层合并去重」，见 _fetch_track。"""
    return f"topic:{topic} stars:>{stars_min} {time_filter}"


def _star_bucket_queries(topic, time_filter, stars_min):
    """对触顶的 topic 生成 star 分桶查询列表（从高 star 到低 star）。

    GitHub Search API 单 query 硬上限 1000 条。热门 topic（如 database）
    在 stars:>50 下会触顶，star 50~300 的长尾项目被截断。分桶后每桶
    < 1000 条即可全收，代码层合并去重。

    返回 [(桶标签, query), ...]，例如：
      ('s>1000', 'topic:database stars:>1000 pushed:>...')
      ('500-1000', 'topic:database stars:500..1000 pushed:>...')
      ... ('50-100', 'topic:database stars:50..100 pushed:>...')
    末桶下界固定为 stars_min（主轨 MAIN_STARS_MIN / 副轨 EMERGING_STARS_MIN），与该轨门槛衔接。
    """
    bounds = sorted(BUCKET_BOUNDS, reverse=True)  # 降序
    # 完整边界链：[最高, ..., stars_min]
    chain = [b for b in bounds if b > stars_min] + [stars_min]
    queries = []
    prev = None  # 上一桶上界（不含）
    for i, lo in enumerate(chain):
        if i == 0:
            # 头桶：stars:>chain[0]
            queries.append((f"s>{lo}", f"topic:{topic} stars:>{lo} {time_filter}"))
        else:
            # 区间桶：stars:lo..prev
            queries.append((f"{lo}-{prev}", f"topic:{topic} stars:{lo}..{prev} {time_filter}"))
        prev = lo
    return queries


def _drain_query(merged, query, label, track_name, max_pages, per_page, raw_pool):
    """翻页抓完单个 query 的全部结果，合并进 merged，同时收 raw_pool。

    含黑名单 + DB词初筛 + 跨 query 去重。返回新留存的条目数。
    """
    kept = 0
    for page in range(1, max_pages + 1):
        items = search_repos(query, per_page=per_page, page=page)
        if not items:
            break
        for it in items:
            full = it.get("full_name", "")
            if not full:
                continue
            # 全量记录到 raw_pool（不管是否通过筛选，都存 star 供增量对比）
            if raw_pool is not None and full not in raw_pool:
                raw_pool[full] = it
            # 初筛：黑名单 + DB词；已在结果里的跳过（跨 topic/桶去重）
            if full in merged or is_blacklisted(it) or not is_db(it):
                continue
            it["_track"] = track_name
            it["_tags"] = {track_name}
            merged[full] = it
            kept += 1
        print(f"  · {track_name}[{label}]第{page}页: 抓{len(items)} 累计留{kept}")
        time.sleep(1)
        if len(items) < per_page:
            break
    return kept


def _fetch_track(track_name, stars_min, time_filter, max_pages, per_page=100, raw_pool=None):
    """通用采集函数：逐 topic 采集，限速时自动分桶重试，跨 topic/桶合并去重。

    节流策略（从源头规避 search API 30次/分钟 限速）：
      1. 每个 topic 处理完后固定等待 TOPIC_INTERVAL 秒，让配额充分恢复；
      2. 若某 topic 撞限速(RateLimited)，则再等 TOPIC_INTERVAL 秒后
         对该 topic 做 star 分桶重试——把大查询拆成多个小子查询，
         每个子查询请求量更小，桶之间也间隔 TOPIC_INTERVAL 秒。

    初筛门槛为 is_db（DB 板块准入，较宽）：纯数据库引擎也能进 DB 池。
    跨 topic / 跨 star 桶的重复项目由 merged 字典天然去重。

    raw_pool: 传入一个 dict，所有搜索到的原始项目都会存进去（用于全量快照）。
    """
    merged = {}
    n_topics = len(SEARCH_TOPICS)
    for idx, topic in enumerate(SEARCH_TOPICS, 1):
        prefix = f"[{idx}/{n_topics}]"
        print(f"\n  === {prefix} {track_name} topic:{topic} ===")
        try:
            # 先探测 total_count（撞限速会抛 RateLimited）
            total = query_total_count(_build_query(topic, stars_min, time_filter)) \
                if BUCKET_THRESHOLD > 0 else 0
            if BUCKET_THRESHOLD > 0 and total >= BUCKET_THRESHOLD:
                # 命中量大：主动分桶（正常路径，非限速）
                buckets = _star_bucket_queries(topic, time_filter, stars_min)
                print(f"  · {track_name}[topic:{topic}] total={total} ≥{BUCKET_THRESHOLD} → 分{len(buckets)}桶")
                for label, q in buckets:
                    _drain_query(merged, q, f"topic:{topic}/{label}", track_name,
                                 max_pages, per_page, raw_pool)
                    time.sleep(TOPIC_INTERVAL)
            else:
                # 命中量小：单 query 翻页（撞限速会抛 RateLimited 冒到这里）
                kept = _drain_query(merged, _build_query(topic, stars_min, time_filter),
                                    f"topic:{topic}", track_name,
                                    max_pages, per_page, raw_pool)
                print(f"  · {track_name}[topic:{topic}] total={total} 留{kept}")
        except RateLimited:
            # 撞限速：等 TOPIC_INTERVAL 秒后对该 topic 分桶重试
            print(f"  · {track_name}[topic:{topic}] ⚠️ 限速，{TOPIC_INTERVAL}s 后分桶重试...")
            time.sleep(TOPIC_INTERVAL)
            buckets = _star_bucket_queries(topic, time_filter, stars_min)
            print(f"    分{len(buckets)}桶重试:")
            for label, q in buckets:
                try:
                    _drain_query(merged, q, f"topic:{topic}/{label}", track_name,
                                 max_pages, per_page, raw_pool)
                except RateLimited:
                    # 分桶后仍限速（极少见）：跳过该桶，继续下一个
                    print(f"    · {label} 仍限速，跳过")
                time.sleep(TOPIC_INTERVAL)
            continue  # 分桶重试已含桶间间隔，跳过下方的 topic 间隔

        # topic 之间固定间隔（最后一个不必等）
        if idx < n_topics:
            print(f"  · topic 间隔 {TOPIC_INTERVAL}s...")
            time.sleep(TOPIC_INTERVAL)
    return merged


def fetch_main_track(raw_pool):
    """主轨：topic:* stars:>50 近180天活跃。"""
    return _fetch_track("主轨", MAIN_STARS_MIN,
                        f"pushed:>{daterange_iso(MAIN_ACTIVE_DAYS)}",
                        MAIN_MAX_PAGES, raw_pool=raw_pool)


def fetch_emerging_track(raw_pool):
    """副轨：topic:* stars:>2 近14天创建。

    翻页深度与主轨一致(MAIN_MAX_PAGES)，最大化召回新建项目；
    实测14天窗口下每 topic 仅几十个，翻满也不会多耗多少 API 配额。
    """
    return _fetch_track("新锐", EMERGING_STARS_MIN,
                        f"created:>{daterange_iso(EMERGING_CREATED_DAYS)}",
                        max_pages=MAIN_MAX_PAGES, per_page=100, raw_pool=raw_pool)


def fetch_all():
    """双轨采集 → 合并去重 → README 精筛 → 分流出 AI 子集。

    返回 (db_pool, ai_pool, raw_pool)：
      - db_pool = 通过 DB 词初筛 + 非黑名单的项目（DB 板块用，范围较宽）
      - ai_pool = db_pool 中 README AI 词命中 ≥3 次的子集（AI 板块用）
      - raw_pool = 所有搜索到的原始项目（全量快照，保证进榜项目都有历史可对比）

    允许重叠：强 AI 的数据库项目在两个池里都存在。
    """
    # raw_pool 收集所有搜索到的原始项目，用于全量快照
    raw_pool = {}

    print("  === 主轨: topic:* stars:>50 近180天 ===")
    main = fetch_main_track(raw_pool)
    print(f"  主轨初筛: {len(main)} 个（全量池: {len(raw_pool)} 个）\n")

    print("  === 副轨: topic:* stars:>2 近14天创建 ===")
    emerging = fetch_emerging_track(raw_pool)
    print(f"  副轨初筛: {len(emerging)} 个（全量池: {len(raw_pool)} 个）")

    # 合并：副轨中主轨没有的项目（star<50 且近14天新建）并入候选池。
    # 注意：这些项目 _track 仍为「新锐」，只进「新锐发现」榜，不进「热点/总榜」
    # （它们本就是新建的低 star 项目，归新锐榜更合理）。
    for full, repo in emerging.items():
        if full not in main:
            main[full] = repo
    print(f"\n  合并去重: {len(main)} 个（全量池: {len(raw_pool)} 个）")

    # db_pool = 合并去重后的全部项目（已过 is_db + 黑名单，待 README 精筛）
    db_candidates = dict(main)

    # README 双重精筛：抓一次 README，同时判定 DB 板块准入 + AI 子集分流
    print(f"\n  === README 精筛 ===")
    print(f"     DB板块：DB词命中≥{README_DB_MIN_HITS}；AI板块：AI词命中≥{README_AI_MIN_HITS}")
    db_pool = {}
    ai_pool = {}
    dropped = []
    for full, repo in db_candidates.items():
        readme = fetch_readme(full)
        db_hits = count_db_hits_in_readme(readme)
        ai_hits = count_ai_hits_in_readme(readme)
        # DB 板块准入：README 里 DB 词命中达标（剔除乱贴 topic/描述蹭词的噪音）
        if db_hits < README_DB_MIN_HITS:
            dropped.append((full, db_hits, ai_hits))
            continue
        repo["_readme"] = readme  # 缓存，后面生成介绍时复用
        db_pool[full] = repo
        # AI 子集分流：DB 板块内 README 再达 AI 词阈值的进 AI 板块
        if ai_hits >= README_AI_MIN_HITS:
            ai_pool[full] = repo
    print(f"  DB 板块入选: {len(db_pool)} 个；AI 板块入选: {len(ai_pool)} 个")
    print(f"  README 精筛剔除: {len(dropped)} 个（噪音/蹭词项目）")
    for full, dh, ah in dropped:
        print(f"    ✗ {full} (DB词{dh}次 AI词{ah}次)")

    return db_pool, ai_pool, raw_pool


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
    """本周 star 热点：板块池内的主轨项目，按周增量降序（无增量则按star）。

    views 传入「该板块的池」（AI 池或 DB 池），实现板块内选榜。
    返回 (榜单列表, 是否为真实增量排序)。
    """
    main = [v for v in views if v["track"] == "主轨"]
    with_delta = [v for v in main if has_delta(v)]
    if len(with_delta) >= top_n:
        return sorted(with_delta, key=lambda x: x["delta"], reverse=True)[:top_n], True
    return sorted(main, key=lambda x: x["stars"], reverse=True)[:top_n], False


def section_total(views, top_n=TOTAL_TOP_N):
    """star 总榜：板块池内的主轨项目，按绝对 star 降序（与增量榜区分）。"""
    main = [v for v in views if v["track"] == "主轨"]
    return sorted(main, key=lambda x: x["stars"], reverse=True)[:top_n]


def section_emerging(views, top_n=EMERGING_TOP_N):
    """新锐发现：板块池内的副轨项目，按 star 降序。"""
    new = sorted([v for v in views if v["track"] == "新锐"],
                 key=lambda x: x["stars"], reverse=True)
    return new[:top_n]


def section_spotlight(hot_items, exclude=None):
    """本周重点解读：从本板块热门榜里选增量最高的。

    只从热门榜选，保证选中的一定是核心项目，
    不会选到「顺便涉及数据库」的边缘项目。
    exclude: set of full_name，排除已被另一板块解读的项目（双板块去重）。
    """
    exclude = exclude or set()
    candidates = [v for v in hot_items if v["full"] not in exclude]
    if not candidates:
        return None
    # 优先选有正增量的
    with_delta = [v for v in candidates if has_delta(v) and v["delta"] > 0]
    if with_delta:
        return max(with_delta, key=lambda x: x["delta"])
    # 兜底：选候选榜第一个（star 最高）
    return candidates[0]


def _dedup_views(views):
    """视图列表按 full_name 去重，保留首次出现的（用于合并两板块上榜项目做 AI 介绍）。"""
    seen = set()
    out = []
    for v in views:
        if not v or v["full"] in seen:
            continue
        seen.add(v["full"])
        out.append(v)
    return out


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
    # 元信息：⭐ 语言 [📈 增量] [更新X天前]，拼到标题行右侧
    meta = [f"⭐{fmt_stars(v['stars'])}", v["lang"]]
    if has_delta(v):
        meta.append(f"📈{fmt_delta(v['delta'])}/周")
    meta.append(f"更新 {days_ago_label(v['pushed'])}")
    meta_str = " · ".join(meta)
    title = f"**{idx}. {v['full']}**" + (f" {tag_str}" if tag_str else "") + f"  {meta_str}"
    desc = v.get("zh_desc") or v["desc"]
    # 卡片：分割线 + 标题行 + 引用式介绍 + 链接
    return "\n".join(["", "---", "", title, f"> {desc}", "", f"🔗 {v['url']}", ""])


_DATE_MD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def count_issues():
    """本期期数 = output/ 根目录下「除今天这份外」的已发布周报 .md 数 + 1。
    只数根目录（正式周报），不数 draft/ 子目录（每日草稿）。
    严格匹配 YYYY-MM-DD.md 文件名，避免手动放入的非周报 .md 污染期号。
    关键：排除「今天这份」，否则今天这份被 render_markdown 写入后再调用本函数
    会让期数虚高 1（把正在生成的本期也数进去了）。"""
    if not os.path.isdir(OUTPUT_DIR):
        return 1
    today_file = f"{TODAY}.md"
    files = [f for f in os.listdir(OUTPUT_DIR)
             if _DATE_MD_RE.match(f)
             and f != today_file
             and os.path.isfile(os.path.join(OUTPUT_DIR, f))]
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


def _spotlight_name_from_json(json_path):
    """从某期的 output/*.json 读取两个板块的「本周解读」项目名。

    新格式 json 含 ai_spotlight / db_spotlight 字段；
    旧格式 json 只有单个 spotlight 字段 → 视作 AI 解读，DB 解读留空。
    返回 (ai_name, db_name)，无则对应位为 None。
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None, None
    ai = d.get("ai_spotlight") or {}
    db = d.get("db_spotlight") or {}
    ai_name = ai.get("name") if isinstance(ai, dict) else None
    db_name = db.get("name") if isinstance(db, dict) else None
    # 旧格式兼容：无 ai_spotlight 字段时回退到 spotlight
    if ai_name is None and "ai_spotlight" not in d:
        old = d.get("spotlight") or {}
        ai_name = old.get("name") if isinstance(old, dict) else None
    return ai_name, db_name


def _rebuild_archive_table(content):
    """从 output/*.json 重建「往期周报」表格（含 AI解读 / DB解读 两列）。

    扫描 OUTPUT_DIR 根目录下所有 YYYY-MM-DD.json，按日期倒序生成行。
    新格式 json 读取 ai_spotlight/db_spotlight；旧格式只有 spotlight（计入 AI 列）。
    每行额外带期数（由 .md 文件数推算，最新期对应最新日期）。
    """
    start_tag, end_tag = "<!-- ARCHIVE:START -->", "<!-- ARCHIVE:END -->"
    i, j = content.find(start_tag), content.find(end_tag)
    if i == -1 or j == -1:
        return content

    if not os.path.isdir(OUTPUT_DIR):
        return content

    # 收集所有正式周报（根目录 YYYY-MM-DD.md），日期升序 → 期数从 1 递增
    md_files = sorted(f for f in os.listdir(OUTPUT_DIR)
                      if _DATE_MD_RE.match(f) and os.path.isfile(os.path.join(OUTPUT_DIR, f)))
    rows = []
    for issue_no, md_file in enumerate(md_files, 1):
        date_str = os.path.splitext(md_file)[0]
        json_path = os.path.join(OUTPUT_DIR, f"{date_str}.json")
        if os.path.exists(json_path):
            ai_name, db_name = _spotlight_name_from_json(json_path)
        else:
            ai_name, db_name = None, None
        ai_cell = ai_name or "—"
        db_cell = db_name or "—"
        md_relpath = f"output/{md_file}"
        rows.append(f"| 第 {issue_no} 期 | {date_str} | {ai_cell} | {db_cell} | [{md_relpath}]({md_relpath}) |")

    # 最新期置顶
    rows.reverse()
    table = ["", "| 期数 | 日期 | AI 解读 | DB 解读 | 链接 |",
             "|------|------|----------|----------|------|"] + rows + [""]
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

    # 2. 重建「往期周报」表格（含 AI解读 / DB解读 两列，回读各期 json）
    content = _rebuild_archive_table(content)

    with open(readme_p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"    [update_readme] 已更新 README：第 {issue_no} 期 · {date_str}")


def _render_section(heading, hot, hot_is_delta, emerging, total, spotlight, spotlight_text):
    """渲染单个板块（AI 或 DB）的四小节，返回该板块的 Markdown 文本行列表。

    四小节：本周 star 热点 Top5 / 新锐发现 / Star 总榜 / 本周解读。
    """
    parts = [heading, ""]

    # ① 本周 star 热点（按周增量；数据积累期按 star）
    parts.append(f"### 本周 star 热点 Top{HOT_TOP_N}")
    if not hot_is_delta:
        parts += [f"> 💡 数据积累中：需连续运行 {DELTA_DAYS} 天后展示真实「周 star 增量」。"
                  f"本期暂按 star 绝对值排序。", ""]
    if hot:
        for i, v in enumerate(hot, 1):
            parts.append(render_entry(i, v))
    else:
        parts += ["> 暂无项目。", ""]

    # ② 新锐发现（近14天新建）
    parts.append(f"### 新锐发现 Top{EMERGING_TOP_N}")
    if emerging:
        for i, v in enumerate(emerging, 1):
            parts.append(render_entry(i, v))
    else:
        parts += ["> 本周暂无新锐项目。", ""]

    # ③ Star 总榜（按绝对 star）
    parts.append(f"### Star 总榜 Top{TOTAL_TOP_N}")
    if total:
        for i, v in enumerate(total, 1):
            parts.append(render_entry(i, v))
    else:
        parts += ["> 暂无项目。", ""]

    # ④ 本周解读
    parts.append("### 本周解读")
    if spotlight:
        tag_str = fmt_tags(spotlight["tags"])
        title = f"**{spotlight['full']}**" + (f" {tag_str}" if tag_str else "")
        parts += ["", title, "",
                  spotlight_text or spotlight.get("zh_desc") or spotlight["desc"], ""]
        delta_str = f" 📈 {fmt_delta(spotlight['delta'])}/周" if has_delta(spotlight) else ""
        parts.append(f"⭐ {fmt_stars(spotlight['stars'])}{delta_str} ｜ {spotlight['lang']} ｜ 更新 {days_ago_label(spotlight['pushed'])}")
        parts += [""]
    else:
        parts += ["> 本周暂无可解读项目。", ""]

    return parts


def render_markdown(db_count, ai_count, ai_hot_is_delta, db_hot_is_delta,
                    ai_hot, ai_emerging, ai_total, ai_spotlight, ai_spotlight_text,
                    db_hot, db_emerging, db_total, db_spotlight, db_spotlight_text):
    issue = count_issues()
    parts = [f"# 📋 数据库开源技术周报 · 第 {issue} 期，{TODAY}", ""]

    # 今日聚焦
    focus = []
    if ai_hot:
        top = ai_hot[0]
        if has_delta(top):
            focus.append(f"🔥 AI 增长王：**{top['name']}**（📈 {fmt_delta(top['delta'])}/周）")
        else:
            focus.append(f"🔥 AI 最受关注：**{top['name']}**（⭐{fmt_stars(top['stars'])}）")
    if db_hot:
        top = db_hot[0]
        if has_delta(top):
            focus.append(f"🔥 DB 增长王：**{top['name']}**（📈 {fmt_delta(top['delta'])}/周）")
        else:
            focus.append(f"🔥 DB 最受关注：**{top['name']}**（⭐{fmt_stars(top['stars'])}）")
    if ai_spotlight:
        focus.append(f"🤖 AI 解读：**{ai_spotlight['name']}**")
    if db_spotlight:
        focus.append(f"🗄️ DB 解读：**{db_spotlight['name']}**")
    if focus:
        parts += ["**📌 今日聚焦**", ""] + focus + ["", "---", ""]

    # AI 板块（用各自的 is_delta，避免 AI 池样本不足时误导 DB 板块提示）
    parts += _render_section("## 🤖 AI 板块",
                             ai_hot, ai_hot_is_delta, ai_emerging, ai_total,
                             ai_spotlight, ai_spotlight_text)

    # DB 板块
    parts += _render_section("## 🗄️ DB 板块",
                             db_hot, db_hot_is_delta, db_emerging, db_total,
                             db_spotlight, db_spotlight_text)

    parts += ["---", "💬 互动：本周你最关注哪个项目？欢迎留言。", "",
              f"<sub>由 ai_db_weekly 自动采集于 {TODAY}，候选池 AI 板块 {ai_count} 个 / DB 板块 {db_count} 个项目。介绍基于各项目 README 由 AI 生成。</sub>"]
    return "\n".join(parts)


# ============================================================
# 主流程
# ============================================================
def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"=== 数据库开源技术周报采集 {TODAY} ===")
    print(f"[+] GITHUB_TOKEN: {'已加载' if GITHUB_TOKEN else '未设置'}")
    print(f"[+] AI_API_KEY: {'已加载(' + AI_MODEL + ')' if AI_API_KEY else '未设置'}")

    # 1. 双轨采集 → 返回 (db_pool, ai_pool, raw_pool)
    print("\n[1/4] 双轨采集（DB池 + AI池分流）...")
    db_pool, ai_pool, raw_pool = fetch_all()
    print(f"\n    DB 板块候选: {len(db_pool)} 个；AI 板块候选: {len(ai_pool)} 个")
    if not db_pool:
        print("[x] 未采集到数据", file=sys.stderr)
        sys.exit(1)

    # 2. 快照 — 存全部初筛项目(不只是精筛后的)，保证进榜项目都有历史
    print(f"\n[2/4] 保存快照（{len(raw_pool)} 个项目）...")
    save_snapshot(raw_pool)

    # 3. 增量
    print(f"\n[3/4] 查找 {DELTA_DAYS} 天前历史快照...")
    hist = find_history_snapshot(DELTA_DAYS)
    print(f"    → {'命中(' + str(len(hist)) + '个)，展示真实周增量' if hist else '未找到，兜底排序'}")

    # 4. 双板块榜单
    print("\n[4/4] 生成双板块榜单...")
    db_views = [repo_view(r, hist) for r in db_pool.values()]
    ai_views = [repo_view(r, hist) for r in ai_pool.values()]

    # AI 板块四小节
    ai_hot, ai_is_delta = section_hot(ai_views)
    ai_total = section_total(ai_views)
    ai_emerging = section_emerging(ai_views)
    ai_spotlight = section_spotlight(ai_hot)

    # DB 板块四小节（解读排除 AI 已选项目，避免两板块解读撞车）
    db_hot, db_is_delta = section_hot(db_views)
    db_total = section_total(db_views)
    db_emerging = section_emerging(db_views)
    ai_spotlight_exclude = {ai_spotlight["full"]} if ai_spotlight else set()
    db_spotlight = section_spotlight(db_hot, exclude=ai_spotlight_exclude)

    # AI 介绍：合并两板块上榜并集去重，统一生成
    listed = _dedup_views(
        ai_hot + ai_total + ai_emerging + ([ai_spotlight] if ai_spotlight else [])
        + db_hot + db_total + db_emerging + ([db_spotlight] if db_spotlight else [])
    )
    if AI_API_KEY:
        print(f"\n[AI] 为 {len(listed)} 个项目生成中文介绍...")
    # readme_map：精筛阶段已抓的 README 缓存，复用避免重复请求
    readme_map = {full: r.get("_readme") for full, r in db_pool.items() if r.get("_readme")}
    ai_cache = _load_ai_cache()
    fill_zh_descs(listed, ai_cache, readme_map)

    # 两个板块各自的本周解读文本
    ai_spotlight_text = None
    if ai_spotlight and AI_API_KEY:
        print(f"[AI] 生成「AI 板块本周解读」: {ai_spotlight['full']}")
        readme = fetch_readme(ai_spotlight["full"]) or ai_pool.get(ai_spotlight["full"], {}).get("_readme")
        ai_spotlight_text = gen_spotlight(
            ai_spotlight["full"], ai_spotlight["desc"], ai_spotlight["lang"],
            ai_spotlight["stars"], ai_spotlight.get("delta") or 0, readme, ai_cache)

    db_spotlight_text = None
    if db_spotlight and AI_API_KEY:
        print(f"[AI] 生成「DB 板块本周解读」: {db_spotlight['full']}")
        readme = fetch_readme(db_spotlight["full"]) or db_pool.get(db_spotlight["full"], {}).get("_readme")
        db_spotlight_text = gen_spotlight(
            db_spotlight["full"], db_spotlight["desc"], db_spotlight["lang"],
            db_spotlight["stars"], db_spotlight.get("delta") or 0, readme, ai_cache)
    _save_ai_cache(ai_cache)

    # 渲染输出
    # 发布日（周一）→ 正式周报放 output/ 根目录；其余日子 → 草稿放 output/draft/
    publish = is_publish_day()
    out_dir = OUTPUT_DIR if publish else DRAFT_DIR
    os.makedirs(out_dir, exist_ok=True)
    role = "发布(正式周报)" if publish else f"非发布日(草稿, PUBLISH_WEEKDAY={PUBLISH_WEEKDAY})"
    print(f"\n[输出] 今天 {TODAY} → {role}")

    md = render_markdown(len(db_pool), len(ai_pool), ai_is_delta, db_is_delta,
                         ai_hot, ai_emerging, ai_total, ai_spotlight, ai_spotlight_text,
                         db_hot, db_emerging, db_total, db_spotlight, db_spotlight_text)
    md_path = os.path.join(out_dir, f"{TODAY}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[OK] 已生成: {md_path}")

    json_path = os.path.join(out_dir, f"{TODAY}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"ai_hot": ai_hot, "ai_emerging": ai_emerging, "ai_total": ai_total,
                   "ai_spotlight": ai_spotlight, "ai_spotlight_text": ai_spotlight_text,
                   "db_hot": db_hot, "db_emerging": db_emerging, "db_total": db_total,
                   "db_spotlight": db_spotlight, "db_spotlight_text": db_spotlight_text,
                   "ai_hot_is_delta": ai_is_delta, "db_hot_is_delta": db_is_delta},
                  f, ensure_ascii=False, indent=2,
                  default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    print(f"[OK] 原始数据: {json_path}")

    # 发布日：更新 README（本期周报 + 往期目录，往期表格含两解读列）
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
