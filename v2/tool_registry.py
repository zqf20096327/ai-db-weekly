"""标杆运维工具清单 + 内核黑名单 + 动态发现（周报新架构核心数据）。

设计依据：
  - DBA 工作场景分 6 类（连接池/代理、高可用/容灾、迁移/变更、备份/恢复、
    监控/诊断、管理客户端）
  - 标杆清单是"手工确认的 DBA 运维工具"，按类目归类（与 category=tool 的
    自动标签不同——后者混入大量内核/ORM/驱动/模板，不可靠）
  - 内核黑名单见 config.KERNEL_REPOS（版本/活跃度以厂商为准，周报不报）
  - 新晋工具：不在标杆但本周冒头的工具，动态纳入"新晋"栏

本模块只做数据定义与查询，不调网络。类目归类当前为手工清单（后续可接
AI 读 README 自动归类，替换 BENCHMARK_TOOLS 的生成方式即可）。
"""

from __future__ import annotations

from typing import Any

import config

# ============================================================
# 6 类标杆运维工具（手工确认，季度评审增减）
# 依据：DBA 工作场景。每类放该场景下的代表性工具。
# ⚠️ 仅收录"本身是 DBA 运维工具"的项目，剔除内核/ORM/驱动/应用模板。
# ============================================================
BENCHMARK_TOOLS: dict[str, list[str]] = {
    "连接池 / 代理": [
        "vitessio/vitess",        # MySQL 水平分片集群（YouTube）
        "flike/kingshard",        # 高性能 MySQL 代理
        "pgdogdev/pgdog",         # PG 连接池/负载均衡/分片
        "pgbouncer/pgbouncer",    # PG 轻量连接池
        "postgresml/pgcat",       # PG 连接池/分片/故障切换
        "yandex/odyssey",         # 可扩展 PG 连接池
        "XiaoMi/Gaea",            # 小米 MySQL 代理
    ],
    "高可用 / 容灾": [
        "patroni/patroni",                  # PG HA 模板
        "zalando/postgres-operator",        # K8s PG 集群管理
        "sorintlab/stolon",                 # PG 云原生 HA
        "reactive-tech/kubegres",           # K8s 多副本 PG
    ],
    "迁移 / 变更": [
        "golang-migrate/migrate",   # 迁移 CLI + Go 库
        "github/gh-ost",            # MySQL 在线 schema 变更
        "flyway/flyway",            # 迁移工具（Redgate）
        "xataio/pgroll",            # PG 零停机迁移
        "sqldef/sqldef",            # 幂等 schema 管理
    ],
    "备份 / 恢复": [
        "databasus/databasus",          # PG PITR 备份+恢复校验
        "EnterpriseDB/barman",          # PG 备份恢复管理器
        "David-Crty/databasement",      # 自托管备份管理（Web UI）
        "Aiven-Open/pghoard",           # PG 备份恢复服务
    ],
    "监控 / 诊断": [
        "grafana/grafana",                          # 可观测性平台
        "VictoriaMetrics/VictoriaMetrics",          # 监控+时序库
        "erikdarlingdata/PerformanceMonitor",       # SQL Server 性能监控
    ],
    "管理客户端": [
        "dbeaver/dbeaver",                          # 通用 DB 工具+SQL 客户端
        "sqlitebrowser/sqlitebrowser",              # SQLite 浏览器
        "beekeeper-studio/beekeeper-studio",        # 现代 SQL 客户端
        "chartdb/chartdb",                          # ER 图编辑器
        "sosedoff/pgweb",                           # PG Web 客户端
        "dbgate/dbgate",                            # 跨库管理工具
    ],
}

# 所有标杆工具 full_name 集合（扁平，便于查询）
ALL_BENCHMARK: set[str] = {fn for fns in BENCHMARK_TOOLS.values() for fn in fns}


def benchmark_category(full_name: str) -> str | None:
    """返回标杆工具所属类目；不在标杆返回 None。"""
    for cat, fns in BENCHMARK_TOOLS.items():
        if full_name in fns:
            return cat
    return None


def is_kernel(full_name: str) -> bool:
    """是否数据库内核（版本/活跃度以厂商为准，周报不报）。"""
    return full_name in config.KERNEL_REPOS


def is_tool(full_name: str) -> bool:
    """是否工具类（标杆 或 非内核的 category=tool 项目）。"""
    if full_name in ALL_BENCHMARK:
        return True
    return not is_kernel(full_name)
