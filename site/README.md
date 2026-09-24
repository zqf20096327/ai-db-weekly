# site/ —— 聚合接力层(中间结果专区)

本目录是「采集在 GitHub、站点在服务器」架构的中间层:**聚合导出的代码、
状态正本和产物数据都集中在这里**,由 `site-build.yml` workflow 每日在
`v2 每日采集` 完成后自动接力生成。`v2/` 采集层零改动。

## 目录结构

```
site/
├── site_export/            # 聚合导出层代码(自 db-oss-observer/site_export 迁入)
│   ├── aggregate_daily.py  #   日聚合 → now/map/archive-*.json
│   ├── export_weekly.py    #   周报导出 → weekly-{N}.json + issues-index.json
│   ├── aggregate_monthly.py / backfill_history.py / validate_site.py
│   ├── site_common.py      #   公共口径层(V2_ROOT/BLOG_SITE_DIR/PERSONAS_FILE 环境变量可覆盖)
│   ├── run_ci_categories.py#   categories CI 驱动(绕开 v2 硬编码路径,见文件头注释)
│   ├── history.json        #   ★状态正本:watched 序列/在池周数,随每日提交累积
│   ├── categories.json     #   ★状态正本:AI 任务分类缓存,增量累积
│   └── docs/               #   落地实施方案 / 数据提取清单
├── blog-site/              # 前端静态文件(index.html + assets/,改版时更新入库)
├── data/site/              # ★中间结果产物(now/map/archive-*/weekly-*/issues-index)
└── README.md               # 本文件
```

> personas 缓存不落在本目录:正本是 `v2/data/personas.json`(v2-daily 每日
> 提交),聚合时用环境变量 `PERSONAS_FILE` 直连,单一正本不复制。

## 自动化链路

```
v2-daily(09:00 采集+富集,已存在,不动)
   ↓ workflow_run 完成事件
site-build.yml(本目录的接力)
   categories 增量 → [周六] run_weekly + export_weekly
   → aggregate_daily → validate_site 闸门 → 提交 site/ 产物
   ↓
服务器 cron:git pull + rsync → /var/www/blog(见下)
```

## 服务器部署(一次性 + 两条 cron)

```bash
# 1) 首次:克隆仓库(公开仓库,匿名即可)
ssh root@<服务器IP>
mkdir -p /opt && cd /opt
git clone https://github.com/zqf20096327/ai-db-weekly.git

# 2) 历史周报回填(一次性):把服务器上现有的站点数据收进仓库成为正本
cd /opt/ai-db-weekly
mkdir -p site/data/site
cp /var/www/blog/data/site/*.json site/data/site/     # weekly-1..7 / issues-index 等
git add site/data/site && git commit -m "data: 回填服务器现有站点数据" && git push

# 3) 定时同步(crontab -e)——不用 --delete,保留服务器上尚未入库的历史文件
#    每天 13:00 与 21:00 各同步一次(13 点接住当日聚合,21 点兜住周六周报)
0 13,21 * * * cd /opt/ai-db-weekly && git pull -q origin main \
  && rsync -a site/blog-site/ /var/www/blog/ \
  && rsync -a site/data/site/ /var/www/blog/data/site/
```

nginx 不需要任何改动(root 仍是 `/var/www/blog`,静态文件 + data 同目录布局)。

## 注意事项

- **首次上线顺序**:先做上面的「历史周报回填」,再启用 cron。否则
  `site/data/site` 里只有新产物,前端「往期」页会缺旧期数据(服务器现有
  文件不会被删,但仓库侧正本不完整)。
- **验证闸门**:validate_site 失败时 workflow 整体失败、不提交产物,
  服务器 rsync 自然停留在上一版,坏数据不会上线。
- **本机角色**:本地不再跑聚合写状态(history/categories 正本在仓库),
  本机只读浏览与开发。`db-oss-observer/code-consolidated` 仍是阅读/交接
  用的总集快照。
- `verify_independent.py` 为旧本机布局下的一次性核对脚本,未迁入
  (含失效绝对路径)。
