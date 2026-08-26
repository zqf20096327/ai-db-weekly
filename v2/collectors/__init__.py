"""采集器包 —— 每个采集步骤一个模块。

模块分工（对应 SOP 第四章 + 采集策略清单）：
  probe.py          第1步  探测 16 topic 规模
  topic.py          第2-3步 巨型/中型三层拆分 + 小型/微型全采
  whitelist.py      第4步  白名单内核（Core API）
  org_scan.py       第4.5步 org 全量扫描（Core API）
  new_projects.py   第5步  新生项目 30 天窗 + 内容相关性过滤
  commit_activity.py 数据源4 commit 活跃度（候选池合并后跑）

每个 collector 接收 GitHubClient，返回采集到的项目列表（已标准化）。
落盘由各自负责（调 storage.save_*），保证每次查询立即写盘防中断。
"""
