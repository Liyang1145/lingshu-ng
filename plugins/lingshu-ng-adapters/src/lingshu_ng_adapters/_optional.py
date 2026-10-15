# -*- coding: utf-8 -*-
"""可选第三方库的导入：缺库 / 导入失败时给出清晰的安装提示（不静默降级）。"""
from __future__ import annotations

import importlib

__all__ = ["MissingDependencyError", "require"]

#: 模块名 → (发行包, 本插件 extra)
_HINT = {
    "langchain_core": ("langchain-core", "langchain"),
    "llama_index.core": ("llama-index-core", "llamaindex"),
}


class MissingDependencyError(ImportError):
    """适配器需要的第三方库没装（或装了但导入失败）。``ImportError`` 子类，旧的 ``except ImportError`` 照常接住。"""


def require(module: str, feature: str):
    """导入 ``module``；失败抛 :class:`MissingDependencyError`，信息写明缺什么、怎么装、原始异常。"""
    try:
        return importlib.import_module(module)
    except Exception as e:  # 第三方包导入期失败类型不可枚举（缺包 / DLL / 版本冲突）
        dist, extra = _HINT.get(module, (module, None))
        how = f"pip install 'lingshu-ng-adapters[{extra}]'（或 pip install {dist}）" if extra else f"pip install {dist}"
        raise MissingDependencyError(
            f"{feature} 需要第三方库 {dist}（导入 {module} 失败：{type(e).__name__}: {e}）。安装：{how}。"
            "lingshu_ng 核心与 mem0 / MCP 适配器不需要它。") from e
