"""快照保留策略 —— 近 N 天明文 + 窗口外 zip 永久归档（2026-09-20 定稿）。

背景：data/snapshot_* 曾按"滚动 8 天窗口"清理（CI 每日把窗口外快照移出 git 索引）。
GitHub API 只返回当前状态、历史 star/forks 无法回填，删掉的快照即永久损失的
数据资产（本地实测已缺 0819-0825 / 0901-0906 两段）。新策略：

  1. 近 config.SNAPSHOT_PLAIN_KEEP_DAYS 天保持明文目录（周报 7 天 diff 与
     storage.find_prev_snapshot_date 依赖目录结构，行为不变）；
  2. 出窗快照压缩为 data/snapshot_YYYYMMDD.zip 永久入库，不再删除（幂等：
     zip 已存在则跳过压缩，只负责把明文目录移出 git 索引）；
  3. 重写仓库根 .gitignore 的快照白名单块（BEGIN/END 标记之间）：
     近 N 天目录 + `!v2/data/snapshot_*.zip` 全量例外；
  4. git 暂存：出窗已跟踪目录 git rm -r --cached（磁盘文件保留）、
     新入库目录与全部 zip git add（提交/推送仍由调用方编排，本脚本不 commit）。

与 CI 的分工：v2-daily.yml 步骤 6 每日调用本脚本后自行 commit + push；
本地手工补档（把磁盘残留的窗口外历史快照回填进仓库）直接运行本脚本即可。

用法（仓库根或 v2/ 下均可，git 操作自动定位仓库根）：
  python v2/snapshot_retention.py                # 以今天（UTC）为基准执行
  python v2/snapshot_retention.py --date 20260920
  python v2/snapshot_retention.py --dry-run      # 只打印将执行的动作
  python v2/snapshot_retention.py --no-git       # 只转 zip，不改 .gitignore、不动 git
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any

import config

log = logging.getLogger("snapshot_retention")

GITIGNORE_BEGIN = "# BEGIN snapshot whitelist (auto-generated)"
GITIGNORE_END = "# END snapshot whitelist"

# .gitignore 中 data 目录的总排斥规则（v2/data/*），白名单块紧随其后做再包含
_REPO_ROOT = os.path.dirname(config.HERE)
_GITIGNORE_PATH = os.path.join(_REPO_ROOT, ".gitignore")


# ============================================================
# 日期窗口与快照清点
# ============================================================
def window_dates(base_date: str, keep_days: int) -> list[str]:
    """明文窗口：base_date 往前共 keep_days 天（含基准日），YYYYMMDD 列表。"""
    base = datetime.strptime(base_date, "%Y%m%d").date()
    return [(base - timedelta(days=i)).strftime("%Y%m%d") for i in range(keep_days)]


def _scan_dates(prefix_dir: str, want_dir: bool) -> list[str]:
    """列出 data/ 下的 snapshot_YYYYMMDD 目录（或 zip）日期，升序。"""
    out: list[str] = []
    for fn in os.listdir(prefix_dir):
        if want_dir:
            d, ok = fn, fn.startswith("snapshot_") and len(fn) == len("snapshot_YYYYMMDD")
        else:
            ok = fn.startswith("snapshot_") and fn.endswith(".zip") and len(fn) == len("snapshot_YYYYMMDD.zip")
            d = fn[: -len(".zip")]
        if ok and d.removeprefix("snapshot_").isdigit():
            out.append(d.removeprefix("snapshot_"))
    return sorted(set(out))


def plain_snapshots() -> list[str]:
    return _scan_dates(config.DATA_DIR, want_dir=True)


def zip_snapshots() -> list[str]:
    return _scan_dates(config.DATA_DIR, want_dir=False)


# ============================================================
# zip 转档（确定性归档：文件按路径排序，arcname 带顶层目录，与既有手工 zip 一致）
# ============================================================
def create_zip(date: str, *, force: bool = False) -> str | None:
    """把 data/snapshot_{date}/ 压缩为同名 zip（已存在且未要求 force 则跳过）。

    返回 zip 路径；目录不存在或完全为空（采集失败日的空壳，无归档价值）返回 None。
    原子写：先落 .tmp 再 rename。
    """
    src_dir = os.path.join(config.DATA_DIR, f"snapshot_{date}")
    dst = os.path.join(config.DATA_DIR, f"snapshot_{date}.zip")
    if not os.path.isdir(src_dir):
        return None
    has_file = any(
        files for _root, _dirs, files in os.walk(src_dir)
    )
    if not has_file:
        log.info("  空目录跳过（采集失败残留）：snapshot_%s", date)
        return None
    if os.path.exists(dst) and not force:
        log.info("  zip 已存在，跳过压缩：snapshot_%s.zip", date)
        return dst

    tmp = dst + ".tmp"
    count = 0
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(src_dir):
                dirs.sort()
                for fn in sorted(files):
                    full = os.path.join(root, fn)
                    arc = os.path.relpath(full, config.DATA_DIR)  # snapshot_YYYYMMDD/...
                    zf.write(full, arc)
                    count += 1
        os.replace(tmp, dst)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    size_mb = os.path.getsize(dst) / 1e6
    log.info("  zip ✓ snapshot_%s.zip（%d 个文件，%.1f MB）", date, count, size_mb)
    return dst


# ============================================================
# .gitignore 白名单块重写
# ============================================================
def rewrite_gitignore(window: list[str]) -> None:
    """重写 BEGIN/END 标记间的白名单：近 N 天目录 + snapshot_*.zip 全量例外。

    标记块由 CI 每日重写，勿手工编辑（与 v2-daily.yml 原内联逻辑格式兼容）。
    """
    with open(_GITIGNORE_PATH, encoding="utf-8") as f:
        text = f.read()
    if GITIGNORE_BEGIN not in text or GITIGNORE_END not in text:
        raise SystemExit(f".gitignore 缺少白名单标记块（{GITIGNORE_BEGIN}），请先手工补齐")
    pre, rest = text.split(GITIGNORE_BEGIN, 1)
    _, post = rest.split(GITIGNORE_END, 1)
    lines = [f"!v2/data/snapshot_{d}/" for d in window]
    lines.append("!v2/data/snapshot_*.zip")
    block = GITIGNORE_BEGIN + "\n" + "".join(f"{l}\n" for l in lines) + GITIGNORE_END
    with open(_GITIGNORE_PATH, "w", encoding="utf-8") as f:
        f.write(pre + block + post)
    log.info(".gitignore 白名单已重写：明文窗口 %s + snapshot_*.zip 全量例外", "/".join(window))


# ============================================================
# git 暂存（不 commit；提交与推送由调用方编排）
# ============================================================
def _git(*args: str) -> str:
    r = subprocess.run(
        ["git", "-C", _REPO_ROOT, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败：{r.stderr.strip()}")
    return r.stdout


def tracked_snapshot_dirs() -> set[str]:
    """git 索引中已跟踪的明文快照日期集合。"""
    out = _git("ls-files", "--", "v2/data/snapshot_*").splitlines()
    dates = set()
    for line in out:
        parts = line.split("/")  # v2/data/snapshot_YYYYMMDD/...
        if len(parts) >= 4 and parts[2].startswith("snapshot_") and parts[2][9:].isdigit():
            dates.add(parts[2][len("snapshot_"):])
    return dates


def stage_changes(window: list[str], out_of_window: list[str]) -> None:
    """窗口外目录移出索引（--cached，磁盘保留）；窗口内新目录与全部 zip 入索引。

    仅对 git 实际跟踪的目录执行 rm：本地磁盘可能有从未入库的历史快照
    （如手工补档前的残留），对未跟踪路径 rm 会报 pathspec 错误。
    """
    tracked_before = tracked_snapshot_dirs()
    for d in out_of_window:
        if d not in tracked_before:
            continue
        _git("rm", "-r", "-q", "--cached", f"v2/data/snapshot_{d}")
        log.info("  git rm --cached：snapshot_%s（磁盘文件保留）", d)

    adds: list[str] = [".gitignore"]
    # 人群分类增量缓存（v2/data/personas.json）：CI 每日富集产物，随快照一起入库
    personas_abs = os.path.join(config.DATA_DIR, "personas.json")
    if os.path.isfile(personas_abs):
        adds.append(os.path.relpath(personas_abs, _REPO_ROOT).replace("\\", "/"))
    tracked = tracked_snapshot_dirs()  # rm 之后的最新索引状态
    for d in plain_snapshots():
        if d in window and d not in tracked:
            adds.append(f"v2/data/snapshot_{d}")
    for d in zip_snapshots():
        adds.append(f"v2/data/snapshot_{d}.zip")
    _git("add", "--", *adds)
    log.info("git add：%d 个路径（.gitignore + personas + 窗口内新目录 + 全部 zip）", len(adds))


# ============================================================
# 主流程
# ============================================================
def run(base_date: str, *, dry_run: bool = False, no_git: bool = False) -> dict[str, Any]:
    window = window_dates(base_date, config.SNAPSHOT_PLAIN_KEEP_DAYS)
    plains = plain_snapshots()
    out_of_window = [d for d in plains if d not in window]
    log.info("基准日 %s：明文窗口 %s（近 %d 天）", base_date, f"{window[-1]}..{window[0]}", len(window))
    log.info("磁盘明文快照 %d 个，其中出窗待转档 %d 个：%s",
             len(plains), len(out_of_window), ", ".join(out_of_window) or "无")

    new_zips: list[str] = []
    for d in out_of_window:
        if dry_run:
            existing = os.path.exists(os.path.join(config.DATA_DIR, f"snapshot_{d}.zip"))
            log.info("  [dry-run] %s snapshot_%s.zip", "已有" if existing else "将创建", d)
            continue
        if create_zip(d):
            new_zips.append(d)

    if no_git:
        log.info("--no-git：不重写 .gitignore、不执行 git 暂存，结束。")
        return {"window": window, "converted": new_zips, "staged": False}

    if dry_run:
        log.info("[dry-run] 将重写 .gitignore 白名单块并执行 git 暂存（rm --cached 出窗目录 / add 窗口内新目录与 zip），结束。")
        return {"window": window, "converted": [], "staged": False}

    rewrite_gitignore(window)
    stage_changes(window, out_of_window)
    log.info("完成：出窗转档 %d 个，git 已暂存（未提交，提交/推送由调用方执行）。", len(new_zips))
    return {"window": window, "converted": new_zips, "staged": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="快照保留：近 N 天明文 + 窗口外 zip 永久归档")
    parser.add_argument("--date", default=config.TODAY, help="基准日期 YYYYMMDD（默认今天 UTC）")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的动作")
    parser.add_argument("--no-git", action="store_true", help="只转 zip，不改 .gitignore、不动 git")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    run(args.date, dry_run=args.dry_run, no_git=args.no_git)


if __name__ == "__main__":
    main()
