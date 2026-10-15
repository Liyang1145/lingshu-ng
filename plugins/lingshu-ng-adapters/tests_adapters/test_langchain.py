# -*- coding: utf-8 -*-
"""LangChain 适配器：装了 langchain-core 就真跑（含 langchain-tests 官方标准套件，装了才跑）；没装只跑缺库报错契约。"""
import os
import subprocess
import sys

import pytest

from conftest import REPO, SRC, require

HAS_LC = True
try:
    import langchain_core  # noqa: F401
except Exception:  # 第三方包导入失败类型不可枚举
    HAS_LC = False


def test_missing_langchain_gives_clear_error():
    """缺库契约（任何环境都跑）：子进程里屏蔽 langchain_core，导入适配器 ⇒ MissingDependencyError（ImportError 子类），
    信息含安装命令；核心与 mem0 / mcp 适配器照常可导入。"""
    code = ("import sys; sys.modules['langchain_core'] = None\n"
            "import lingshu_ng_adapters.mem0, lingshu_ng_adapters.mcp_memory\n"
            "from lingshu_ng_adapters import MissingDependencyError\n"
            "try:\n    import lingshu_ng_adapters.langchain\nexcept MissingDependencyError as e:\n"
            "    assert isinstance(e, ImportError); print('MDE', e)\nelse:\n    print('NO-ERROR')\n")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([REPO, SRC, os.environ.get("PYTHONPATH", "")]))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("MDE") and "pip install" in out.stdout and "langchain" in out.stdout


if not HAS_LC:
    pytest.skip("langchain-core 未安装：只跑缺库契约（上面一条）", allow_module_level=True)

from langchain_core.documents import Document  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402

from lingshu_ng_adapters.langchain import (LingshuChatMessageHistory, LingshuRetriever,  # noqa: E402
                                           LingshuVectorStore)


# --------------------------------------------------------------------------- 会话历史
def test_chat_history_roundtrip_and_isolation(engine):
    h = LingshuChatMessageHistory("s1", engine=engine)
    h.add_messages([SystemMessage("be brief"), HumanMessage("我叫小王，喜欢爵士乐"), AIMessage("好的")])
    h.add_message(HumanMessage("推荐一张专辑", additional_kwargs={"k": 1}))
    msgs = h.messages
    assert [type(x).__name__ for x in msgs] == ["SystemMessage", "HumanMessage", "AIMessage", "HumanMessage"]
    assert msgs[-1].content == "推荐一张专辑" and msgs[-1].additional_kwargs == {"k": 1}
    assert LingshuChatMessageHistory("s2", engine=engine).messages == []
    hits = engine.recall("爵士乐", 5)["hits"]                      # 会话消息同时是可召回的长期记忆
    assert any("爵士乐" in n.content for n, _ in hits)
    h.clear()
    assert h.messages == []


def test_chat_history_persists(tmp_path):
    p = str(tmp_path / "hist.sqlite")
    h = LingshuChatMessageHistory("s", path=p)
    h.add_messages([HumanMessage("one"), AIMessage("two")])
    h.engine.close()
    h2 = LingshuChatMessageHistory("s", path=p)
    assert [m.content for m in h2.messages] == ["one", "two"]
    h2.engine.close()


def test_chat_history_async(engine):
    import asyncio
    h = LingshuChatMessageHistory("a", engine=engine)

    async def go():
        await h.aadd_messages([HumanMessage("hi")])
        return await h.aget_messages()

    assert [m.content for m in asyncio.run(go())] == ["hi"]


def test_runnable_with_message_history(engine):
    """LangChain 官方会话包装 RunnableWithMessageHistory 直接用本历史类。"""
    from langchain_core.runnables import RunnableLambda
    from langchain_core.runnables.history import RunnableWithMessageHistory

    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    chain = ChatPromptTemplate.from_messages([MessagesPlaceholder("history"), ("human", "{input}")]) | \
        RunnableLambda(lambda pv: AIMessage(f"seen {len(pv.to_messages())}"))
    store = {}

    def get(sid):
        return store.setdefault(sid, LingshuChatMessageHistory(sid, engine=engine))

    rw = RunnableWithMessageHistory(chain, get, input_messages_key="input", history_messages_key="history")
    cfg = {"configurable": {"session_id": "x"}}
    assert rw.invoke({"input": "a"}, config=cfg).content == "seen 1"
    assert rw.invoke({"input": "b"}, config=cfg).content == "seen 3"
    assert [m.content for m in get("x").messages] == ["a", "seen 1", "b", "seen 3"]


# --------------------------------------------------------------------------- 检索器
def test_retriever_over_engine(engine):
    for t in ["The VPN password rotates every 90 days", "Lunch is served at noon", "合同续签截止日期是十一月三十日"]:
        engine.perceive(t)
    r = LingshuRetriever(engine=engine, k=2)
    docs = r.invoke("when does the VPN password rotate")
    assert docs and docs[0].page_content.startswith("The VPN password")
    assert {"lingshu_id", "score", "lingshu_layer"} <= set(docs[0].metadata)
    assert r.invoke("合同续签")[0].page_content.startswith("合同续签")
    assert LingshuRetriever(engine=engine, k=2, min_score=1.01).invoke("VPN") == []
    assert len(r.batch(["VPN", "lunch"])) == 2


def test_retriever_namespace_and_filter(engine):
    from lingshu_ng_adapters.mem0 import Memory
    Memory(engine=engine).add("tea preference: oolong", user_id="u", metadata={"src": "chat"})
    engine.perceive("tea preference: green (foreign writer)")
    only_mem0 = LingshuRetriever(engine=engine, namespace="mem0").invoke("tea preference")
    assert [d.page_content for d in only_mem0] == ["tea preference: oolong"]
    flt = LingshuRetriever(engine=engine, filter={"src": "chat"}).invoke("tea preference")
    assert [d.page_content for d in flt] == ["tea preference: oolong"]


# --------------------------------------------------------------------------- 向量库接口
def test_vectorstore_basic(engine):
    vs = LingshuVectorStore(engine=engine)
    ids = vs.add_texts(["Paris is the capital of France", "Berlin is in Germany"], [{"s": "a"}, {"s": "b"}], ids=["d1", "d2"])
    assert ids == ["d1", "d2"]
    assert vs.add_documents([Document(page_content="Rome is in Italy", metadata={"s": "c"})])
    top = vs.similarity_search("capital of France", k=1)[0]
    assert top.id == "d1" and top.metadata == {"s": "a"}
    (d, s), = vs.similarity_search_with_relevance_scores("Germany", k=1, filter={"s": "b"})
    assert d.id == "d2" and 0.0 <= s <= 1.0
    assert vs.as_retriever(search_kwargs={"k": 1}).invoke("Italy")[0].page_content == "Rome is in Italy"
    vs.add_texts(["Berlin is the German capital"], ids=["d2"])          # 同 id 覆盖
    assert [x.page_content for x in vs.get_by_ids(["d2"])] == ["Berlin is the German capital"]
    assert vs.delete(["d1"]) is True and vs.get_by_ids(["d1"]) == []
    other = LingshuVectorStore(engine=engine, collection_name="other")
    assert other.similarity_search("Berlin") == []                    # 集合隔离
    vs.delete()
    assert vs.similarity_search("Rome") == []
    assert LingshuVectorStore.from_texts(["a cat sat"], None, engine=engine, collection_name="c2").similarity_search("cat")


# --------------------------------------------------------------------------- langchain-tests 官方标准套件（装了才跑）
try:
    from langchain_tests.integration_tests import RetrieversIntegrationTests, VectorStoreIntegrationTests
    HAS_STD = True
except Exception:  # 第三方包导入失败类型不可枚举
    HAS_STD = False

if HAS_STD:
    class TestLingshuVectorStoreStandard(VectorStoreIntegrationTests):
        """LangChain 官方 VectorStore 标准集成测试（langchain-tests）。"""

        @pytest.fixture()
        def vectorstore(self, tmp_path):
            from lingshu_ng.engine import MemoryEngine
            e = MemoryEngine(str(tmp_path / "std_vs.sqlite"))
            yield LingshuVectorStore(self.get_embeddings(), engine=e)
            e.close()

    class TestLingshuRetrieverStandard(RetrieversIntegrationTests):
        """LangChain 官方 Retriever 标准集成测试（langchain-tests）。"""

        @property
        def retriever_constructor(self):
            return _seeded_retriever

        @property
        def retriever_constructor_params(self):
            return {}

        @property
        def retriever_query_example(self) -> str:
            return "example query"


def _seeded_retriever(k: int = 4, **kw):
    from lingshu_ng.engine import MemoryEngine
    e = MemoryEngine(":memory:")
    for i in range(8):
        e.perceive(f"example query document number {i}", skip_dedup=True)
    return LingshuRetriever(engine=e, k=k, **kw)
