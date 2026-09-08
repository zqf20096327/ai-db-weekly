#<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DBA 周报 · 卡片版</title>
    <style>
        /* ----- 全局重置 & 字体 ----- */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: #f5f7fb;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                "PingFang SC", "Microsoft YaHei", sans-serif;
            padding: 24px 16px;
            color: #1e293b;
            max-width: 820px;
            margin: 0 auto;
        }

        /* ----- 主容器（模拟公众号卡片区） ----- */
        .weekly-wrapper {
            background: #ffffff;
            border-radius: 24px;
            padding: 32px 28px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
        }

        /* ----- 标题区 ----- */
        .weekly-header {
            border-bottom: 2px solid #eef2f6;
            padding-bottom: 20px;
            margin-bottom: 28px;
        }
        .weekly-header h1 {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #0f172a;
        }
        .weekly-header .meta {
            margin-top: 6px;
            font-size: 14px;
            color: #64748b;
            display: flex;
            flex-wrap: wrap;
            gap: 12px 20px;
        }
        .weekly-header .meta .tag {
            background: #eef2f6;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 12px;
            color: #334155;
        }

        /* ----- 板块标题 ----- */
        .section-title {
            font-size: 20px;
            font-weight: 650;
            margin-top: 36px;
            margin-bottom: 6px;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .section-sub {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 18px;
            padding-left: 2px;
            border-left: 3px solid #d0d9e8;
            padding-left: 12px;
        }

        /* ----- 卡片（核心） ----- */
        .card {
            background: #fafcff;
            border: 1px solid #e9edf4;
            border-radius: 18px;
            padding: 20px 22px;
            margin-bottom: 16px;
            transition: box-shadow 0.15s;
        }
        .card:hover {
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
        }

        .card-header {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 6px 12px;
            margin-bottom: 6px;
        }
        .card-header .name {
            font-size: 18px;
            font-weight: 650;
            color: #0f172a;
        }
        .card-header .badge {
            font-size: 12px;
            background: #e6edf8;
            padding: 2px 10px;
            border-radius: 30px;
            color: #1e4b7a;
            font-weight: 500;
        }
        .card-header .stars {
            font-size: 14px;
            color: #475569;
            margin-left: auto;
            white-space: nowrap;
        }
        .card-header .stars strong {
            color: #0f172a;
        }

        .card-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 6px 12px;
            font-size: 13px;
            color: #475569;
            margin-bottom: 10px;
        }
        .card-tags .label {
            background: #eef2f6;
            padding: 0 10px;
            border-radius: 30px;
            font-size: 12px;
            color: #334155;
        }
        .card-tags a {
            color: #2563eb;
            text-decoration: none;
            font-weight: 450;
            word-break: break-all;
        }
        .card-tags a:hover {
            text-decoration: underline;
        }

        .card-desc {
            font-size: 14.5px;
            line-height: 1.6;
            color: #1e293b;
            margin-top: 4px;
        }
        .card-desc strong {
            color: #0f172a;
        }
        .card-desc .highlight {
            background: #f1f5f9;
            padding: 0 6px;
            border-radius: 6px;
            font-weight: 450;
        }

        /* 新锐发现更紧凑 */
        .card-compact .card-desc {
            font-size: 14px;
        }

        /* ----- 总榜表格 ----- */
        .top-table-wrap {
            margin-top: 10px;
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid #e9edf4;
        }
        .top-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            min-width: 500px;
        }
        .top-table th {
            background: #f1f5f9;
            text-align: left;
            padding: 12px 14px;
            font-weight: 600;
            color: #1e293b;
            border-bottom: 1px solid #dce2ec;
        }
        .top-table td {
            padding: 12px 14px;
            border-bottom: 1px solid #eef2f6;
            color: #1e293b;
        }
        .top-table tr:last-child td {
            border-bottom: none;
        }
        .top-table .repo {
            font-weight: 550;
            color: #0f172a;
        }
        .top-table .stars-num {
            font-weight: 600;
            color: #0f172a;
            text-align: right;
        }

        /* ----- 脚注 / 互动 ----- */
        .footer-note {
            margin-top: 32px;
            padding-top: 20px;
            border-top: 2px solid #eef2f6;
            font-size: 14px;
            color: #475569;
            line-height: 1.7;
        }
        .footer-note strong {
            color: #0f172a;
        }
        .footer-note .bubble {
            background: #f1f5f9;
            padding: 12px 18px;
            border-radius: 16px;
            margin-bottom: 14px;
            color: #0f172a;
        }

        /* ----- 响应式微调 ----- */
        @media (max-width: 600px) {
            .weekly-wrapper {
                padding: 18px 14px;
            }
            .card {
                padding: 16px 16px;
            }
            .card-header .stars {
                margin-left: 0;
                width: 100%;
            }
            .weekly-header h1 {
                font-size: 22px;
            }
            .top-table {
                font-size: 13px;
                min-width: 400px;
            }
        }
    </style>
</head>
<body>
    <div class="weekly-wrapper">

        <!-- ========================================= -->
        <!-- 头部 -->
        <!-- ========================================= -->
        <div class="weekly-header">
            <h1>📌 本周 DBA 速览</h1>
            <div class="meta">
                <span>📊 数据源：GitHub</span>
                <span class="tag">聚焦开源工具 · 实验项目</span>
                <span>📅 2026-09-07</span>
                <span class="tag">⚠️ 生产可用性请自行评估</span>
            </div>
        </div>

        <!-- ========================================= -->
        <!-- 板块一 · 国际主流数据库 -->
        <!-- ========================================= -->
        <div class="section-title">🗄️ 板块一 · 国际主流数据库</div>
        <div class="section-sub">Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse</div>

        <!-- 活跃榜 Top3 -->
        <p style="font-weight:600; font-size:16px; margin: 10px 0 12px 0;">🔥 活跃榜 Top3</p>

        <!-- Card 1 -->
        <div class="card">
            <div class="card-header">
                <span class="name">🥇 databasement</span>
                <span class="badge">备份</span>
                <span class="stars">⭐ 2.3k · 本周 <strong>+267</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> SQL Server / MySQL / PostgreSQL / MariaDB
                <span style="margin-left:auto;">🔗 <a href="https://github.com/David-Crty/databasement" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：自托管数据库备份管理工具，提供 Web 界面，支持定时备份与恢复，可存储至 S3、SFTP 等，并支持 SSH 隧道连接。<br />
                <strong>适用场景</strong>：适合需统一管理多种数据库备份的中小团队，特别是数据库位于私有网络、需通过跳板机访问的环境。
            </div>
        </div>

        <!-- Card 2 -->
        <div class="card">
            <div class="card-header">
                <span class="name">🥈 pgbot</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 984 · 本周 <strong>+159</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> PostgreSQL
                <span style="margin-left:auto;">🔗 <a href="https://github.com/pgrundev/pgbot" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：PostgreSQL 只读诊断工具，静态连接数据库，读取统计视图并输出健康报告及变更对比，支持 PG 14–18。<br />
                <strong>适用场景</strong>：适合 DBA 日常巡检、版本升级前后的健康对比。
            </div>
        </div>

        <!-- Card 3 -->
        <div class="card">
            <div class="card-header">
                <span class="name">🥉 TablePro</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 5.8k · 本周 <strong>+149</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 7+ 种数据库（Oracle / SQL Server / MySQL 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/TableProApp/TablePro" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：免费开源数据库客户端，原生支持多类 SQL 及 NoSQL 数据库，集成 AI 辅助与 MCP 服务。<br />
                <strong>适用场景</strong>：适合需要统一客户端管理多种数据库的开发者。
            </div>
        </div>

        <!-- 新锐发现 -->
        <p style="font-weight:600; font-size:16px; margin: 22px 0 12px 0;">🌱 新锐发现</p>

        <div class="card card-compact">
            <div class="card-header">
                <span class="name">① model</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 5 · 本周 +5</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> MySQL / MariaDB
                <span style="margin-left:auto;">🔗 <a href="https://github.com/el1s7/model" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>一句话解读</strong>：轻量 Python ORM，支持静态类型检查、自动建表与模型生成，专注于 MariaDB/MySQL 及 SQLite。
            </div>
        </div>

        <div class="card card-compact">
            <div class="card-header">
                <span class="name">② Mysql-GUI</span>
                <span class="badge">平台</span>
                <span class="stars">⭐ 4 · 本周 +4</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> SQL Server / MySQL
                <span style="margin-left:auto;">🔗 <a href="https://github.com/Jayavisaag/Mysql-GUI" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>一句话解读</strong>：基于 Python Tkinter 的 MySQL 图形管理工具，支持建库建表、权限管理、CSV 导出等日常运维操作。
            </div>
        </div>

        <div class="card card-compact">
            <div class="card-header">
                <span class="name">③ branchbase</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 3 · 本周 +3</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> MySQL / PostgreSQL
                <span style="margin-left:auto;">🔗 <a href="https://github.com/oscarbol09/branchbase" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>一句话解读</strong>：为数据库提供 Git 原生分支能力，可随代码分支切换本地库状态，减少手动重建或回滚迁移。
            </div>
        </div>

        <!-- 本周解读 -->
        <p style="font-weight:600; font-size:16px; margin: 22px 0 12px 0;">🔍 本周解读 · databasement</p>

        <div class="card">
            <div class="card-header">
                <span class="name">databasement</span>
                <span class="badge">备份</span>
                <span class="stars">⭐ 2.3k · 本周 +267</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> SQL Server / MySQL / PostgreSQL / MariaDB
                <span style="margin-left:auto;">🔗 <a href="https://github.com/David-Crty/databasement" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>解决什么问题</strong>：自托管数据库备份管理工具，通过 Web 界面统一调度备份任务，解决多类型数据库备份分散、恢复流程复杂的问题。<br /><br />
                <strong>核心亮点</strong>：支持多种数据库定时备份与恢复；提供 SSH 隧道和远程代理访问隔离网络；支持 S3、SFTP、Samba 及本地存储。<br /><br />
                <strong>适用场景</strong>：适用于需要统一管理多种数据库备份的中小团队或运维人员；适合数据库位于私有网络、需通过跳板机访问的环境；适合对备份安全性与自动化恢复流程有要求的自托管部署场景。
            </div>
        </div>

        <!-- ========================================= -->
        <!-- 板块二 · 国内数据库 -->
        <!-- ========================================= -->
        <div class="section-title">🇨🇳 板块二 · 国内数据库</div>
        <div class="section-sub">openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB</div>

        <p style="font-weight:600; font-size:16px; margin: 10px 0 12px 0;">🔥 活跃榜 Top3</p>

        <div class="card">
            <div class="card-header">
                <span class="name">🥇 Bytebase</span>
                <span class="badge">管理</span>
                <span class="stars">⭐ 14.5k · 本周 <strong>+17</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 8+ 种数据库（Oracle / SQL Server / MySQL 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/bytebase/bytebase" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：开源数据库治理平台，统一管理变更、访问与合规。支持 GUI 工作流、GitOps、200+ SQL 审查规则、动态列级脱敏及 MCP 协议接入 AI 代理。<br />
                <strong>适用场景</strong>：适合需规范化数据库变更流程的开发团队、要求敏感数据访问可控的安全合规场景。
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="name">🥈 DBBridge</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 16 · 本周 <strong>+15</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 8+ 种数据库（MySQL / PostgreSQL / MariaDB 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/suoten/dbbridge" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：开源免费、零依赖的数据库迁移与 SQL 转换工具，单文件免安装，图形界面操作，支持十余种数据库间数据互转。<br />
                <strong>适用场景</strong>：适合需要跨数据库迁移数据的个人开发者或小型团队。
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="name">🥉 pprof-rs</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 1.7k · 本周 <strong>+3</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> TiDB
                <span style="margin-left:auto;">🔗 <a href="https://github.com/tikv/pprof-rs" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：Rust 编写的 CPU 分析器，基于 backtrace-rs 实现，可定位 CPU 热点并生成调用栈报告。<br />
                <strong>适用场景</strong>：适合 TiDB 等数据库开发者进行性能调优。
            </div>
        </div>

        <p style="font-weight:600; font-size:16px; margin: 22px 0 12px 0;">🔍 本周解读 · Bytebase</p>

        <div class="card">
            <div class="card-header">
                <span class="name">Bytebase</span>
                <span class="badge">管理</span>
                <span class="stars">⭐ 14.5k · 本周 +17</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 8+ 种数据库（Oracle / SQL Server / MySQL 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/bytebase/bytebase" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>解决什么问题</strong>：数据库变更与访问管控分散在多个工具中，导致流程割裂且难以审计。Bytebase 提供统一控制平面，整合变更管理、权限控制和合规记录。<br /><br />
                <strong>核心亮点</strong>：支持 GUI 与 GitOps 双模式变更流程；内置 200+ SQL 审查规则；基于角色的细粒度权限、临时授权及动态列级脱敏；完整审计日志；可通过 MCP 协议接入 AI 代理执行操作。<br /><br />
                <strong>适用场景</strong>：适合需要规范化数据库变更流程的开发团队、需集中管理多环境数据库的 DBA，以及要求敏感数据访问可控、操作可追溯的安全合规场景。支持自托管或 Kubernetes 部署。
            </div>
        </div>

        <!-- ========================================= -->
        <!-- 板块三 · AI 工具 -->
        <!-- ========================================= -->
        <div class="section-title">🤖 板块三 · AI 工具</div>
        <div class="section-sub">板块一 / 板块二所列数据库生态的 AI 辅助工具（text2sql / AI DBA / DB-MCP 等）</div>

        <p style="font-weight:600; font-size:16px; margin: 10px 0 12px 0;">🔥 活跃榜 Top3</p>

        <div class="card">
            <div class="card-header">
                <span class="name">🥇 dbx</span>
                <span class="badge">平台</span>
                <span class="stars">⭐ 18.2k · 本周 <strong>+630</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 15+ 种数据库（Oracle / SQL Server / DB2 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/t8y2/dbx" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：20MB 轻量级客户端支持 90 余种数据库；内置 AI 助手辅助查询与排错；集成 MCP Server；支持桌面端、Docker、CLI 三种运行形态。<br />
                <strong>适用场景</strong>：适合需同时管理多种数据库的开发运维人员、资源受限设备常驻，Docker 快速搭建临时环境，或通过 MCP 协议接入 AI 工作流。
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="name">🥈 Tabularis</span>
                <span class="badge">平台</span>
                <span class="stars">⭐ 4.8k · 本周 <strong>+249</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 9+ 种数据库（Oracle / SQL Server / DB2 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/TabularisDB/tabularis" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：开源桌面 SQL 工作台，支持十余种数据库，内置 MCP 服务器。<br />
                <strong>适用场景</strong>：适合需要本地化 SQL 工作台并希望接入 AI 工具链的开发者。
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <span class="name">🥉 WrenAI</span>
                <span class="badge">平台</span>
                <span class="stars">⭐ 17.5k · 本周 <strong>+85</strong></span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> PostgreSQL / ClickHouse
                <span style="margin-left:auto;">🔗 <a href="https://github.com/Canner/WrenAI" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>核心亮点</strong>：开源生成式 BI 引擎，提供受治理的 text-to-SQL 与语义层，支持 20 余种数据源，可将自然语言转为 SQL、图表及仪表盘。<br />
                <strong>适用场景</strong>：适合希望为业务团队提供自然语言查询能力的数据平台团队。
            </div>
        </div>

        <p style="font-weight:600; font-size:16px; margin: 22px 0 12px 0;">🌱 新锐发现</p>

        <div class="card card-compact">
            <div class="card-header">
                <span class="name">① ledger</span>
                <span class="badge">其他</span>
                <span class="stars">⭐ 4 · 本周 +4</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> PostgreSQL
                <span style="margin-left:auto;">🔗 <a href="https://github.com/CesarPetrescu/ledger" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>一句话解读</strong>：自托管 MCP 服务器，基于 PostgreSQL 存储数据，为 AI 助手提供跨对话的项目记忆与上下文检索功能。
            </div>
        </div>

        <p style="font-weight:600; font-size:16px; margin: 22px 0 12px 0;">🔍 本周解读 · dbx</p>

        <div class="card">
            <div class="card-header">
                <span class="name">dbx</span>
                <span class="badge">平台</span>
                <span class="stars">⭐ 18.2k · 本周 +630</span>
            </div>
            <div class="card-tags">
                <span class="label">适用</span> 15+ 种数据库（Oracle / SQL Server / DB2 等）
                <span style="margin-left:auto;">🔗 <a href="https://github.com/t8y2/dbx" target="_blank">GitHub</a></span>
            </div>
            <div class="card-desc">
                <strong>解决什么问题</strong>：20MB 安装包集成 90 余种数据库访问能力，覆盖 MySQL、PostgreSQL、文件、内存、文档、Oracle、SQL Server、DB2、达梦等，提供统一桌面端、Docker 与命令行入口。<br /><br />
                <strong>核心亮点</strong>：内置 AI 助手辅助查询与排错，集成 MCP Server 便于接入外部 AI 编排工具。支持桌面端、Docker、CLI 三种运行形态，适配不同部署环境。安装包约 20MB，资源占用低，便于分发与携带。<br /><br />
                <strong>适用场景</strong>：适用于需同时管理多种数据库的开发运维人员；适合资源受限设备常驻，Docker 快速搭建临时环境，命令行或脚本执行操作，及通过 MCP 协议接入 AI 工作流。
            </div>
        </div>

        <!-- ========================================= -->
        <!-- Top 总榜 -->
        <!-- ========================================= -->
        <div class="section-title" style="margin-top:44px;">📊 Top 总榜（历史 Star 总数）</div>

        <div class="top-table-wrap">
            <table class="top-table">
                <thead>
                    <tr>
                        <th>项目</th>
                        <th>总 Star</th>
                        <th>板块</th>
                        <th>分类</th>
                        <th>一句话定位</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="repo"><a href="https://github.com/grafana/grafana" target="_blank" style="color:#2563eb; text-decoration:none;">grafana/grafana</a></td>
                        <td class="stars-num">76.6k</td>
                        <td>国外数据库</td>
                        <td>监控</td>
                        <td>开源可观测性与数据可视化平台</td>
                    </tr>
                    <tr>
                        <td class="repo"><a href="https://github.com/dbeaver/dbeaver" target="_blank" style="color:#2563eb; text-decoration:none;">dbeaver/dbeaver</a></td>
                        <td class="stars-num">51.7k</td>
                        <td>国外数据库</td>
                        <td>其他</td>
                        <td>免费通用数据库工具及 SQL 客户端</td>
                    </tr>
                    <tr>
                        <td class="repo"><a href="https://github.com/drawdb-io/drawdb" target="_blank" style="color:#2563eb; text-decoration:none;">drawdb-io/drawdb</a></td>
                        <td class="stars-num">39.4k</td>
                        <td>国外数据库</td>
                        <td>其他</td>
                        <td>免费在线数据库关系图编辑器及 SQL 生成器</td>
                    </tr>
                    <tr>
                        <td class="repo"><a href="https://github.com/OtterMind/Chat2DB" target="_blank" style="color:#2563eb; text-decoration:none;">OtterMind/Chat2DB</a></td>
                        <td class="stars-num">28.1k</td>
                        <td>AI工具</td>
                        <td>管理</td>
                        <td>免费、跨平台、本地优先的数据库客户端及 SQL 工具</td>
                    </tr>
                    <tr>
                        <td class="repo"><a href="https://github.com/PostgREST/postgrest" target="_blank" style="color:#2563eb; text-decoration:none;">PostgREST/postgrest</a></td>
                        <td class="stars-num">27.6k</td>
                        <td>国外数据库</td>
                        <td>其他</td>
                        <td>为任意 Postgres 数据库提供 REST API</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- ========================================= -->
        <!-- 底部互动与说明 -->
        <!-- ========================================= -->
        <div class="footer-note">
            <div class="bubble">
                💬 <strong>互动</strong>：本周你最关注哪个项目？欢迎留言分享你的试用体验。
            </div>

            <p>
                <strong>📌 板块范围说明</strong>：<br />
                板块一：Oracle / SQL Server / DB2 / MySQL / PostgreSQL / MariaDB / ClickHouse<br />
                板块二：openGauss / GaussDB / TiDB / OceanBase / TDSQL / PolarDB / PolarDB-X / YashanDB / GBase / DM / GoldenDB<br />
                板块三：上述数据库生态的 AI 辅助工具。范围外数据库项目不入周报。
            </p>
            <p style="margin-top:6px;">
                <strong>📌 数据说明</strong>：由 <code>ai_db_weekly</code> 基于 GitHub 数据自动采集（截至 2026-09-07）。项目描述来自 GitHub 的 description 字段；AI 解读基于 README 生成，仅供参考。国产数据库板块仅收录在 GitHub 上活跃的开源项目，内核以各厂商官方为准。
            </p>
        </div>

    </div>
</body>
</html>


## 往期周报

<!-- ARCHIVE:START -->
| 期数 | 日期 | 链接 |
|------|------|------|
| 第 4 期 | 2026-08-31 | [report_snapshot_20260831.md](v2/reports/report_snapshot_20260831.md) |
| 第 3 期 | 2026-08-24 | [report_snapshot_20260824.md](v2/reports/report_snapshot_20260824.md) |
| 第 2 期 | 2026-08-17 | [report_snapshot_20260817.md](v2/reports/report_snapshot_20260817.md) |
<!-- ARCHIVE:END -->
