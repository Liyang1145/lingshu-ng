# -*- coding: utf-8 -*-
"""lingshu_ng_adapters（插件 lingshu-ng-adapters）· 把 lingshu_ng 当作现有生态里的记忆后端直接替换接入。

| 模块 | 对齐的接口 | 第三方依赖 |
|---|---|---|
| :mod:`lingshu_ng_adapters.mem0` | mem0 ``Memory`` / ``AsyncMemory``（add / search / get / get_all / update / delete / delete_all / history / reset） | 无（纯标准库，不依赖 mem0） |
| :mod:`lingshu_ng_adapters.langchain` | LangChain ``BaseChatMessageHistory`` / ``BaseRetriever`` / ``VectorStore`` | ``langchain-core``（可选：``pip install 'lingshu-ng-adapters[langchain]'``） |
| :mod:`lingshu_ng_adapters.llamaindex` | LlamaIndex ``BaseRetriever`` / ``BaseMemory`` / ``BaseMemoryBlock`` | ``llama-index-core``（可选：``pip install 'lingshu-ng-adapters[llamaindex]'``） |
| :mod:`lingshu_ng_adapters.mcp_memory` | MCP 官方 memory server（``@modelcontextprotocol/server-memory``）的 9 个工具名 + ng 原有 4 个 ``lingshu_*`` 工具 | 无 |

导入本包不加载任何第三方库；只有导入 ``langchain`` / ``llamaindex`` 子模块时才导入对应库，缺库时抛
:class:`MissingDependencyError`（``ImportError`` 子类，信息写明 ``pip install`` 什么）。
"""
__version__ = "1.37.0"

from ._optional import MissingDependencyError  # noqa: E402

__all__ = ["__version__", "MissingDependencyError"]
