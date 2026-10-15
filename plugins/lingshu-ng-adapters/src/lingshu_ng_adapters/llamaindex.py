# -*- coding: utf-8 -*-
"""LlamaIndex 适配器（需要 ``llama-index-core``；缺库导入本模块即抛 :class:`MissingDependencyError`，写明怎么装）。

对齐 llama-index-core 0.14.25（2026-10 实测）的抽象方法：

- :class:`LingshuRetriever` ← ``llama_index.core.retrievers.BaseRetriever``：``_retrieve(query_bundle)``
  （``retrieve`` / ``aretrieve`` 由基类提供）。返回 ``NodeWithScore(TextNode)``，``node.id_`` = 记忆 id。
- :class:`LingshuChatMemory` ← ``llama_index.core.memory.BaseMemory``：``from_defaults`` / ``get`` / ``get_all`` /
  ``put`` / ``set`` / ``reset``（``aget`` / ``aput`` 等由基类提供）。按 ``session_id`` 存会话消息；每条消息同时是可被
  ``engine.recall`` 召回的长期记忆。
- :class:`LingshuMemoryBlock` ← ``llama_index.core.memory.BaseMemoryBlock[str]``：``_aget`` / ``_aput``，用于新版
  ``llama_index.core.memory.Memory.from_defaults(memory_blocks=[...])``：短期记忆溢出的消息写入 lingshu_ng，
  每轮按最近一条用户消息召回相关长期记忆、以文本块注入提示词。

有意的不同：``LingshuChatMemory.get(input=...)`` 不做 token 截断（``max_messages`` 按条数截取最近消息）；
``LingshuMemoryBlock`` 不实现 ``atruncate``（基类缺省：超预算时整块丢弃）。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from ._optional import require

require("llama_index.core", "lingshu_ng_adapters.llamaindex")

from llama_index.core.base.llms.types import ChatMessage  # noqa: E402
from llama_index.core.memory import BaseMemory, BaseMemoryBlock  # noqa: E402
from llama_index.core.retrievers import BaseRetriever  # noqa: E402
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode  # noqa: E402
from pydantic import ConfigDict, Field, PrivateAttr  # noqa: E402

from ._backend import Backend, Record, iso, match_filters  # noqa: E402

__all__ = ["LingshuRetriever", "LingshuChatMemory", "LingshuMemoryBlock", "record_node"]


def record_node(r: Record, score: Optional[float] = None) -> NodeWithScore:
    meta = {k: v for k, v in r.meta.items() if not k.startswith("_") and k not in ("li_message", "lc_message")}
    meta.update({"lingshu_layer": getattr(r.node.layer, "value", r.node.layer),
                 "lingshu_created_at": iso(r.node.created_at)})
    return NodeWithScore(node=TextNode(id_=r.id, text=r.text, metadata=meta), score=score)


def _msg_text(m: ChatMessage) -> str:
    try:
        t = m.content
    except Exception:  # 非文本块（图像等）：只取文本
        t = None
    return t if isinstance(t, str) else ""


# --------------------------------------------------------------------------- 检索器
class LingshuRetriever(BaseRetriever):
    """``engine.recall`` → ``NodeWithScore`` 列表。``namespace`` / ``filters`` / ``min_score`` 同 LangChain 检索器。"""

    def __init__(self, engine, similarity_top_k: int = 4, namespace: Optional[str] = None,
                 filters: Optional[Dict[str, Any]] = None, min_score: float = 0.0, **kwargs: Any):
        self.engine = engine
        self.similarity_top_k = int(similarity_top_k)
        self.namespace = namespace
        self.filters = filters
        self.min_score = float(min_score)
        super().__init__(**kwargs)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        b = Backend(engine=self.engine, namespace=self.namespace or "_")
        own = b.owner_tag if self.namespace else None

        def keep(r: Record) -> bool:
            return ((own is None or own in r.tags) and (r.score or 0.0) >= self.min_score
                    and match_filters(r.meta, self.filters))

        return [record_node(r, r.score) for r in b.search(query_bundle.query_str, self.similarity_top_k, keep)]


# --------------------------------------------------------------------------- 会话记忆
class LingshuChatMemory(BaseMemory):
    """``BaseMemory``：按 ``session_id`` 存取 ``ChatMessage``（顺序由 ``seq`` 保证），后端为 lingshu_ng 引擎。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str = "default"
    namespace: str = "li"
    max_messages: Optional[int] = Field(default=None, description="get() 只返回最近这么多条；None = 全部")
    engine: Any = None
    _b: Any = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        self._b = Backend(engine=self.engine, namespace=self.namespace)
        self.engine = self._b.engine

    @classmethod
    def class_name(cls) -> str:
        return "LingshuChatMemory"

    @classmethod
    def from_defaults(cls, engine=None, path: str = ":memory:", session_id: str = "default",
                      namespace: str = "li", max_messages: Optional[int] = None, **kwargs: Any) -> "LingshuChatMemory":
        if engine is None:
            from lingshu_ng.engine import MemoryEngine
            engine = MemoryEngine(path)
        return cls(engine=engine, session_id=session_id, namespace=namespace, max_messages=max_messages)

    def _tags(self) -> List[str]:
        return [self._b.owner_tag, self._b.tag("session", self.session_id)]

    def _records(self) -> List[Record]:
        recs = self._b.by_tags(self._tags())
        recs.sort(key=lambda r: (r.meta.get("seq", 0), r.node.created_at or 0.0, r.id))
        return recs

    def get_all(self) -> List[ChatMessage]:
        return [ChatMessage.model_validate(r.meta["li_message"]) for r in self._records()
                if isinstance(r.meta.get("li_message"), dict)]

    def get(self, input: Optional[str] = None, **kwargs: Any) -> List[ChatMessage]:
        msgs = self.get_all()
        if self.max_messages is not None:
            msgs = msgs[-int(self.max_messages):] if self.max_messages > 0 else []
        return msgs

    def put(self, message: ChatMessage) -> None:
        self.put_messages([message])

    def put_messages(self, messages: List[ChatMessage]) -> None:
        with self._b.db.tx():
            seq = max((int(r.meta.get("seq", 0)) for r in self._records()), default=0)
            for m in messages:
                if not isinstance(m, ChatMessage):
                    raise TypeError(f"需要 ChatMessage（收到 {type(m).__name__}）")
                seq += 1
                self._b.write(_msg_text(m), [self._b.tag("session", self.session_id)],
                              {"li_message": m.model_dump(mode="json"), "seq": seq,
                               "role": getattr(m.role, "value", str(m.role)), "session_id": self.session_id})

    def set(self, messages: List[ChatMessage]) -> None:
        with self._b.db.tx():
            self.reset()
            self.put_messages(list(messages))

    def reset(self) -> None:
        self._b.delete_many(r.id for r in self._records())


# --------------------------------------------------------------------------- 新版 Memory 的长期记忆块
class LingshuMemoryBlock(BaseMemoryBlock[str]):
    """``Memory.from_defaults(memory_blocks=[LingshuMemoryBlock(engine=e)])``：写入溢出消息、召回相关长期记忆。

    ``scope_to_session=True`` 时只召回同一 ``session_id`` 写入的记忆（session_id 由 ``Memory`` 传给 ``aput``）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "lingshu_memory"
    description: Optional[str] = "lingshu_ng 长期记忆（原文召回）"
    engine: Any = None
    namespace: str = "li_block"
    top_k: int = 5
    min_score: float = 0.0
    scope_to_session: bool = False
    _b: Any = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        self._b = Backend(engine=self.engine, namespace=self.namespace)
        self.engine = self._b.engine

    def _query(self, messages: Optional[List[ChatMessage]]) -> str:
        for m in reversed(messages or []):
            if getattr(m.role, "value", m.role) == "user" and _msg_text(m).strip():
                return _msg_text(m)
        for m in reversed(messages or []):
            if _msg_text(m).strip():
                return _msg_text(m)
        return ""

    def recall(self, query: str, session_id: Optional[str] = None) -> List[Record]:
        need = {self._b.owner_tag}
        if self.scope_to_session and session_id:
            need.add(self._b.tag("session", session_id))

        def keep(r: Record) -> bool:
            return need <= set(r.tags) and (r.score or 0.0) >= self.min_score

        return self._b.search(query, int(self.top_k), keep)

    async def _aget(self, messages: Optional[List[ChatMessage]] = None, **block_kwargs: Any) -> str:
        q = self._query(messages)
        if not q.strip():
            return ""
        sid = block_kwargs.get("session_id")
        if sid is None:
            for m in reversed(messages or []):
                sid = (m.additional_kwargs or {}).get("session_id")
                if sid:
                    break
        recs = await asyncio.to_thread(self.recall, q, sid)
        return "\n".join(f"- {r.text}" for r in recs)

    async def _aput(self, messages: List[ChatMessage]) -> None:
        def put() -> None:
            with self._b.db.tx():
                for m in messages:
                    t = _msg_text(m).strip()
                    if not t:
                        continue
                    sid = (m.additional_kwargs or {}).get("session_id")
                    scope = [self._b.tag("session", sid)] if sid else []
                    self._b.write(t, scope, {"role": getattr(m.role, "value", str(m.role)),
                                             **({"session_id": sid} if sid else {})}, dedup=True)
        await asyncio.to_thread(put)
