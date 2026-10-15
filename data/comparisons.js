/* AI 构建期生成的对比解读。
   样例由 AI 基于 README 全文摘录 + 站内信号撰写（正式版由 build/ai_compare.py 接 LLM 自动生成）。
   键 = 参与项目 fns 排序后用 | 拼接。 */
window.COMPARE = {
"OtterMind/Chat2DB|TableProApp/TablePro|dbeaver/dbeaver": {
  "title": "数据库客户端三国杀：全功能 · AI 原生 · 原生轻快",
  "verdict": "要功能全、生态成熟选 DBeaver；要 AI 优先且自带模型选 Chat2DB；嫌重只要快、能接受早期版本选 TablePro。",
  "sections": [
    {"h": "定位差异", "text": "DBeaver 是「重装瑞士军刀」：README 功能清单覆盖 schema/SQL/数据编辑器、ER 图、导入导出与迁移、执行计划、管理面板、空间数据查看、SSH 隧道，开箱支持 100+ 数据库驱动、任何有 JDBC/ODBC 驱动的库。Chat2DB 定位「AI 驱动的 SQL 工作台」：支持 40+ 数据库（含 TiDB、Greenplum、IoTDB），新 JDBC 库仅靠配置即可添加；AI 助手采用自带模型（BYO model）方式，生成与解释 SQL。TablePro 只讲一件事：fast, native database client——以原生（无 WebView）换启动速度与低占用。"},
    {"h": "数据信号", "text": "三者均活跃：近两周内都有发版（DBeaver 09-21、Chat2DB 09-23、TablePro 09-17）。体量差距明显：DBeaver ★51.9k、Chat2DB ★28.3k、TablePro ★6.1k。站内跨库标记 DBeaver 覆盖 5 库、Chat2DB 6 库、TablePro 3 库。TablePro 本周 +129 星处于明显上升期。"},
    {"h": "风险与观察点", "text": "DBeaver 功能最全但 Java 系体积与内存开销也最大，社区版与 PRO 版存在功能分界；Chat2DB 的 AI 能力依赖你自配的模型 API，未配置时退化为普通客户端；TablePro 为 AGPL v3 + v0.75 早期版本，商用分发需注意许可证传染，生产重度使用前建议再观察两个版本周期。"}
  ],
  "picks": [
    {"scene": "全场景日常使用 · 要老牌稳定", "pick": "DBeaver", "why": "100+ 驱动、功能最全、社区最成熟"},
    {"scene": "以 AI 辅助写 SQL 为主", "pick": "Chat2DB", "why": "AI 原生工作台，自带模型数据不出本机"},
    {"scene": "嫌现有客户端重 · 只要快", "pick": "TablePro", "why": "原生无 WebView，轻快，上升期"}
  ]
},
"EnterpriseDB/barman|pgbackrest/pgbackrest": {
  "title": "PG 备份双雄：并行性能派 vs 多机灾备管理派",
  "verdict": "单库大、备份窗口紧选 pgBackRest（并行+压缩优化）；多套实例要集中灾备管理选 Barman。",
  "sections": [
    {"h": "定位差异", "text": "pgBackRest 自述为「可靠备份恢复方案，无缝扩展到最大的数据库与工作负载」，核心卖点是并行备份/恢复——文档直言「压缩通常是瓶颈」，工程取向是吞吐与规模。Barman（EnterpriseDB 维护，Python/GPL3）定位「PostgreSQL 灾备管理器」：强调对多台服务器的远程备份、面向业务关键环境降低风险、在恢复阶段辅助 DBA——取向是集中管理与流程编排。"},
    {"h": "数据信号", "text": "pgBackRest ★4.4k 高于 Barman ★3.2k；pgBackRest 两天前（09-27）刚发布 2.59.2 稳定版，近两月发版密集（2.59.1 → 2.59.2），Barman 最近发版为 08-27。两者均专注 PostgreSQL 生态，各自路线上的事实标准。"},
    {"h": "风险与观察点", "text": "pgBackRest 社区驱动、面向大规模打磨，配置项多、上手曲线略陡；Barman 由商业公司 EnterpriseDB 主导维护（注意其与商业产品线的协同可能），Python 实现在超大规模吞吐上不及 C 实现的 pgBackRest。两者均为 GPL 系许可证，内部使用无碍。"}
  ],
  "picks": [
    {"scene": "超大库 / 备份窗口紧张", "pick": "pgBackRest", "why": "并行备份恢复 + 压缩瓶颈优化"},
    {"scene": "多实例集中灾备管理", "pick": "Barman", "why": "多服务器远程备份与恢复编排"},
    {"scene": "看重发版节奏与社区", "pick": "pgBackRest", "why": "刚发 2.59.2，迭代密集"}
  ]
}
};
