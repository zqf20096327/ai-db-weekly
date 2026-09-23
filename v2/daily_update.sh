#!/usr/bin/env bash
# 每日全自动更新：采集 → 聚合 → 部署（日更模式）。
# 放在采集仓库根目录，由 Windows 任务计划每天调用（Git Bash 执行）。
#
# 注册计划任务（管理员 PowerShell/CMD，每天 08:00）：
#   schtasks /Create /TN "db-observe-daily" /SC DAILY /ST 08:00 ^
#     /TR "C:\Program Files\Git\bin\bash.exe -lc 'cd /d/daily_github/v2 && bash daily_update.sh >> logs/daily_update.log 2>&1'"
#   （Git Bash 路径按实际安装位置调整；日志目录需先 mkdir logs）
#
# 手动补跑：bash daily_update.sh [--no-deploy]
set -uo pipefail
cd "$(dirname "$0")"
NO_DEPLOY="${1:-}"

mkdir -p logs
# AI 缓存正本入仓库（v2/data/*.json，CI 每日增量提交）；site_export 读取
# 路径固定，聚合前同步过去（本地仓库越新，站点标注越全）
sync_caches() {
    [ -f data/personas.json ] && cp -f data/personas.json /d/db-oss-observer/site_export/personas.json || true
    [ -f data/categories.json ] && cp -f data/categories.json /d/db-oss-observer/site_export/categories.json || true
}
sync_personas() { sync_caches; }   # 兼容旧名
echo "==== $(date '+%F %T') 日更开始 ===="

echo "-- 1/3 每日采集（run_daily）"
python run_daily.py || { echo "!! run_daily 失败，中止（今日不更新站点）"; exit 1; }

echo "-- 2/3 日聚合（aggregate_daily，site_export 已移至 db-oss-observer/）"
sync_personas
python D:/db-oss-observer/site_export/aggregate_daily.py || { echo "!! aggregate_daily 失败，中止"; exit 1; }

# 富集增量滚动（2026-09-23 定案：每日跑，替代原"周四批量"）——
# 未采过的优先 + 超过 30 天未刷新的重采（cap 500/天稳态 ~200 个 repo），
# personas/categories 天然增量（缓存命中跳过，日常只有新项目）。
echo "-- 2.5/4 富集增量滚动（releases + GHSA / personas / categories）"
python run_enrich.py --cap 500 || echo "!! run_enrich 失败（不影响本次部署，明天继续）"
python run_personas.py || echo "!! run_personas 失败（不影响本次部署）"
python run_categories.py || echo "!! run_categories 失败（不影响本次部署）"
sync_caches
python D:/db-oss-observer/site_export/aggregate_daily.py || echo "!! 富集后重聚合失败"

if [ "$NO_DEPLOY" = "--no-deploy" ]; then
    echo "-- 3/3 跳过部署（--no-deploy）"
else
    echo "-- 3/3 部署（deploy.sh，含两级校验）"
    bash "D:/db-oss-observer/blog-site/tools/deploy.sh" || { echo "!! deploy 失败（数据未上线）"; exit 1; }
fi

echo "==== $(date '+%F %T') 日更完成 ===="
