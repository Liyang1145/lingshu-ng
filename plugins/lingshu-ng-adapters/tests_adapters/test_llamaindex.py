# -*- coding: utf-8 -*-
"""LlamaIndex 适配器：装了 llama-index-core 就真跑（含新版 ``Memory`` + 记忆块端到端）；没装只跑缺库报错契约。"""
import asyncio
import os
import subprocess
import sys

import pytest

from conftest import REPO, SRC

HAS_LI = True
try:
    import llama_index.core  # noqa: F401
except Exception:  # 第三方包导入失败类型不可枚举
    HAS_LI = False


def test_missing_llamaindex_gives_clear_error():
    code = ("import sys; sys.modules['llama_index'] = None; sys.modules['llama_index.core'] = None\n"
            "import lingshu_ng_adapters.mem0\n"
            "from lingshu_ng_adapters import MissingDependencyError\n"
            "try:\n    import lingshu_ng_adapters.llamaindex\nexcept MissingDependencyError as e:\n"
            "    assert isinstance(e, ImportError); print('MDE', e)\nelse:\n    print('NO-ERROR')\n")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([REPO, SRC, os.environ.get("PYTHONPATH", "")]))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("MDE") and "pip install" in out.stdout and "llama-index-core" in out.stdout


if not HAS_LI:
    pytest.skip("llama-index-core 未安装：只跑缺库契约（上面一条）", allow_module_level=True)

from llama_index.core.base.llms.types import ChatMessage  # noqa: E402
from llama_index.core.memory import BaseMemory, BaseMemoryBlock  # noqa: E402
from llama_index.core.retrievers import BaseRetriever  # noqa: E402
from llama_index.core.schema import QueryBundle  # noqa: E402

from lingshu_ng_adapters.llamaindex import LingshuChatMemory, LingshuMemoryBlock, LingshuRetriever  # noqa: E402


def test_abstract_methods_all_implemented():
    """三个类都是对应基类的子类，且没有未实现的抽象方法。"""
    assert issubclass(LingshuRetriever, BaseRetriever) and not getattr(LingshuRetriever, "__abstractmethods__", None)
    assert issubclass(LingshuChatMemory, BaseMemory) and not LingshuChatMemory.__abstractmethods__
    assert issubclass(LingshuMemoryBlock, BaseMemoryBlock) and not LingshuMemoryBlock.__abstractmethods__


def test_retriever(engine):
    for t in ["The VPN password rotates every 90 days", "Lunch is served at noon", "合同续签截止日期是十一月三十日"]:
        engine.perceive(t)
    r = LingshuRetriever(engine, similarity_top_k=2)
    res = r.retrieve("when does the VPN password rotate")
    assert res and res[0].node.get_content().startswith("The VPN password") and res[0].score > 0
    assert res[0].node.node_id.startswith("node_")
    assert r.retrieve(QueryBundle("合同续签"))[0].node.get_content().startswith("合同")
    assert asyncio.run(r.aretrieve("lunch"))[0].node.get_content() == "Lunch is served at noon"


def test_chat_memory(engine):
    m = LingshuChatMemory.from_defaults(engine=engine, session_id="u1", max_messages=2)
    m.put(ChatMessage(role="user", content="hi"))
    m.put(ChatMessage(role="assistant", content="hello"))
    m.put(ChatMessage(role="user", content="合同什么时候续签"))
    assert [x.content for x in m.get()] == ["hello", "合同什么时候续签"]
    assert [x.content for x in m.get_all()] == ["hi", "hello", "合同什么时候续签"]
    assert LingshuChatMemory.from_defaults(engine=engine, session_id="u2").get_all() == []
    m.set([ChatMessage(role="user", content="reset")])
    assert [x.content for x in m.get_all()] == ["reset"]
    assert [x.content for x in asyncio.run(m.aget())] == ["reset"]
    asyncio.run(m.aput(ChatMessage(role="assistant", content="ok")))
    assert [x.role.value for x in m.get_all()] == ["user", "assistant"]
    m.reset()
    assert m.get_all() == []


def test_chat_memory_persists(tmp_path):
    p = str(tmp_path / "li.sqlite")
    m = LingshuChatMemory.from_defaults(path=p, session_id="s")
    m.put(ChatMessage(role="user", content="persist"))
    m.engine.close()
    m2 = LingshuChatMemory.from_defaults(path=p, session_id="s")
    assert [x.content for x in m2.get_all()] == ["persist"]
    m2.engine.close()


def test_memory_block_with_new_memory_class(engine):
    """新版 llama_index.core.memory.Memory：短期记忆溢出 → 写入 lingshu；之后按最近用户消息召回注入。"""
    from llama_index.core.memory import Memory
    block = LingshuMemoryBlock(engine=engine)
    mem = Memory.from_defaults(session_id="s9", token_limit=60, chat_history_token_ratio=0.5, token_flush_size=10,
                               memory_blocks=[block], tokenizer_fn=lambda s: s.split())

    async def go():
        for i in range(12):
            await mem.aput(ChatMessage(role="user", content=f"fact {i}: my dog is named Biscuit and likes carrots {i}"))
        await mem.aput(ChatMessage(role="user", content="what is my dog called?"))
        return await mem.aget()

    out = asyncio.run(go())
    text = out[0].content
    assert "<lingshu_memory>" in text and "Biscuit" in text
    assert engine.recall("Biscuit carrots", 3)["hits"]               # 溢出的消息进了 lingshu 长期记忆


def test_memory_block_session_scope(engine):
    b = LingshuMemoryBlock(engine=engine, scope_to_session=True)
    asyncio.run(b.aput([ChatMessage(role="user", content="alpha likes jazz")], session_id="A"))
    asyncio.run(b.aput([ChatMessage(role="user", content="beta likes jazz")], session_id="B"))
    got = asyncio.run(b.aget([ChatMessage(role="user", content="who likes jazz", additional_kwargs={"session_id": "A"})]))
    assert got == "- alpha likes jazz"
    other = LingshuMemoryBlock(engine=engine, namespace="other_ns")
    assert asyncio.run(other.aget([ChatMessage(role="user", content="jazz")])) == ""   # 不同命名空间互不可见
