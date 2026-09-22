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
echo "==== $(date '+%F %T') 日更开始 ===="

echo "-- 1/3 每日采集（run_daily）"
python run_daily.py || { echo "!! run_daily 失败，中止（今日不更新站点）"; exit 1; }

echo "-- 2/3 日聚合（aggregate_daily，site_export 已移至 db-oss-observer/）"
python D:/db-oss-observer/site_export/aggregate_daily.py || { echo "!! aggregate_daily 失败，中止"; exit 1; }

# 周四出刊日顺带跑维护/安全/人群富集（周节奏足够；watched 全量靠断点续采分次完成）
if [ "$(date +%u)" = "4" ]; then
    echo "-- 2.5/3 周度富集（releases + GHSA 安全 / personas 人群）"
    python run_enrich.py --cap 1500 || echo "!! run_enrich 失败（不影响本次部署，下次续采）"
    python run_personas.py || echo "!! run_personas 失败（不影响本次部署）"
    python D:/db-oss-observer/site_export/aggregate_daily.py || echo "!! 富集后重聚合失败"
fi

if [ "$NO_DEPLOY" = "--no-deploy" ]; then
    echo "-- 3/3 跳过部署（--no-deploy）"
else
    echo "-- 3/3 部署（deploy.sh，含两级校验）"
    bash "D:/db-oss-observer/blog-site/tools/deploy.sh" || { echo "!! deploy 失败（数据未上线）"; exit 1; }
fi

echo "==== $(date '+%F %T') 日更完成 ===="
