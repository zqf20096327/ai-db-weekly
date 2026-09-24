"""site-build 专用驱动：在仓库内运行 v2 的 run_categories.py。

背景：v2/run_categories.py 硬编码 SITE_EXPORT = D:\\db-oss-observer\\site_export
（旧本机布局），CI/Linux 上该路径不存在，import site_common 与缓存写入都会
落空。为遵守「v2 采集层零改动」的约定，用导入缓存绕开，不改 v2 代码：

  1. 设 V2_ROOT=仓库/v2，先导入本目录（site/site_export/）的 site_common
     —— 进 sys.modules 缓存；
  2. 再 import v2 的 run_categories —— 其内部 `import site_common` 命中缓存，
     不会解析到旧路径；它多余的一次 sys.path.insert 无副作用；
  3. 覆盖其模块级 SITE_EXPORT 指向本目录后执行 main()。

效果：categories 缓存读写都落在 site/site_export/categories.json，与
site_common.load_categories() 的读取位置一致，由 site-build workflow 提交入库。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent        # <repo>/site/site_export
REPO = HERE.parent.parent                      # 仓库根
V2 = REPO / "v2"

os.environ.setdefault("V2_ROOT", str(V2))

sys.path.insert(0, str(HERE))
import site_common  # noqa: E402,F401  本目录副本，按 V2_ROOT 绑定采集层

sys.path.insert(0, str(V2))
import run_categories as rc  # noqa: E402

rc.SITE_EXPORT = HERE
rc.main()
