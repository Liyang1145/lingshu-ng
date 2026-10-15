# -*- coding: utf-8 -*-
"""lingshu-ng-adapters 测试公共设置（同其它插件：未 pip 安装时把仓库根放进 sys.path，源码树发现插件 src）。

SQLite 库一律放 pytest 的 tmp_path（缺省在系统临时目录 /tmp 下）或进程内 ``:memory:``。"""
import importlib
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if importlib.util.find_spec("lingshu_ng") is None and REPO not in sys.path:
    sys.path.insert(0, REPO)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lingshu_ng._alias  # noqa: E402

lingshu_ng._alias.source_plugin_paths()
SRC = os.path.join(os.path.dirname(HERE), "src")
if importlib.util.find_spec("lingshu_ng_adapters") is None and SRC not in sys.path:
    sys.path.append(SRC)


def require(name: str):
    """可选第三方库：任何导入期异常 ⇒ skip（原因带异常原文；同 tests_ng/_optdeps.require 口径）。"""
    try:
        return importlib.import_module(name)
    except Exception as e:  # 第三方包导入期失败类型不可枚举
        pytest.skip(f"可选依赖 {name} 不可用：{type(e).__name__}: {e}", allow_module_level=True)


@pytest.fixture
def engine(tmp_path):
    from lingshu_ng.engine import MemoryEngine
    e = MemoryEngine(str(tmp_path / "adapters.sqlite"))
    yield e
    e.close()



def pytest_configure(config):
    """langchain-tests 标准套件含未加标记的 ``async def`` 用例：装了 pytest-asyncio 且未显式指定模式时用 auto 模式。"""
    if getattr(config.option, "asyncio_mode", "absent") is None:
        config.option.asyncio_mode = "auto"
