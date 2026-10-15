# -*- coding: utf-8 -*-
"""插件描述对象（入口点 ``lingshu_ng.plugins: adapters = lingshu_ng_adapters.plugin:PLUGIN``）。只用标准库，导入不加载第三方库。

本插件只「向外」提供适配器（不向核心提供打分件 / 旧子包）；``provides`` 登记各适配器入口，宿主可按能力名查到。
langchain / llamaindex 两组是可选依赖：``dependencies`` 只列必需的第三方模块（无），可选项见 ``optional_dependencies``。
"""
from . import __version__


class _Plugin:
    name = "adapters"
    distribution = "lingshu-ng-adapters"
    version = __version__
    dependencies = ()
    optional_dependencies = {"langchain": ("langchain_core",), "llamaindex": ("llama_index.core",)}
    provides = {
        "adapter:mem0": "lingshu_ng_adapters.mem0:Memory",
        "adapter:mem0_async": "lingshu_ng_adapters.mem0:AsyncMemory",
        "adapter:langchain_chat_history": "lingshu_ng_adapters.langchain:LingshuChatMessageHistory",
        "adapter:langchain_retriever": "lingshu_ng_adapters.langchain:LingshuRetriever",
        "adapter:langchain_vectorstore": "lingshu_ng_adapters.langchain:LingshuVectorStore",
        "adapter:llamaindex_retriever": "lingshu_ng_adapters.llamaindex:LingshuRetriever",
        "adapter:llamaindex_memory": "lingshu_ng_adapters.llamaindex:LingshuChatMemory",
        "adapter:llamaindex_memory_block": "lingshu_ng_adapters.llamaindex:LingshuMemoryBlock",
        "adapter:mcp_memory": "lingshu_ng_adapters.mcp_memory:KnowledgeGraphServer",
    }

    def __repr__(self):
        return f"<lingshu-ng plugin {self.distribution} {self.version}>"


PLUGIN = _Plugin()
