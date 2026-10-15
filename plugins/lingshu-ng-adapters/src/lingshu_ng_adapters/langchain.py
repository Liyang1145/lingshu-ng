# -*- coding: utf-8 -*-
"""LangChain 适配器（需要 ``langchain-core``；缺库导入本模块即抛 :class:`MissingDependencyError`，写明怎么装）。

对齐 langchain-core 1.6.10（2026-10 实测；``langchain_core.chat_history`` / ``retrievers`` / ``vectorstores``）的最小方法集：

- :class:`LingshuChatMessageHistory` ← ``BaseChatMessageHistory``：``messages``（属性）、``add_messages``、
  ``add_message``（基类）、``clear``；异步 ``aget_messages`` / ``aadd_messages`` / ``aclear`` 由基类经线程池调用同步方法。
  每条消息同时是一条可被 ``engine.recall`` 召回的长期记忆（知识层原文），会话内顺序由 ``seq`` 保证。
- :class:`LingshuRetriever` ← ``BaseRetriever``：``_get_relevant_documents``（``invoke`` / ``ainvoke`` / ``batch`` 由基类提供）。
  检索整个引擎（任何写入方写的记忆都能召回）；``namespace`` / ``filter`` 可收窄。
- :class:`LingshuVectorStore` ← ``VectorStore``：``add_texts``、``add_documents``（基类，转调 add_texts）、``delete``、
  ``get_by_ids``、``similarity_search``、``similarity_search_with_score``、``similarity_search_with_relevance_scores``
  （基类，经 ``_similarity_search_with_relevance_scores``）、``from_texts``、``as_retriever``（基类）。

有意的不同：lingshu_ng 不需要外部嵌入模型（词面召回 + 可选本地语义件），``embedding`` 参数被接受、保存在
``embeddings`` 属性上但**不参与**检索；``max_marginal_relevance_search`` 未实现（基类抛 ``NotImplementedError``）；
``*_by_vector`` 系列（需要向量）未实现。
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ._optional import require

require("langchain_core", "lingshu_ng_adapters.langchain")

from langchain_core.chat_history import BaseChatMessageHistory  # noqa: E402
from langchain_core.callbacks import CallbackManagerForRetrieverRun  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict  # noqa: E402
from langchain_core.retrievers import BaseRetriever  # noqa: E402
from langchain_core.vectorstores import VectorStore  # noqa: E402
from pydantic import ConfigDict  # noqa: E402  （langchain-core 的必需依赖）

from ._backend import Backend, Record, iso, match_filters  # noqa: E402

#: 适配器内部元数据键（不回给调用方）
_INTERNAL = frozenset({"_lc_id", "_ts", "_updated_at", "lc_message"})

__all__ = ["LingshuChatMessageHistory", "LingshuRetriever", "LingshuVectorStore", "record_document"]


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p if isinstance(p, str) else str(p.get("text", "")) for p in content
                         if isinstance(p, str) or (isinstance(p, dict) and p.get("type") in (None, "text")))
    return "" if content is None else str(content)


def record_document(r: Record, score: Optional[float] = None, ext_id: Optional[str] = None,
                    provenance: bool = True) -> Document:
    """记录 → ``Document``：``page_content`` 为原文；``metadata`` = 写入时的元数据（``provenance`` 时另加 ``lingshu_*``
    溯源字段与 ``score``；向量库接口按 LangChain 约定原样返回写入时的元数据，不加）。"""
    meta = {k: v for k, v in r.meta.items() if k not in _INTERNAL}
    if provenance:
        meta.update({"lingshu_id": r.id, "lingshu_layer": getattr(r.node.layer, "value", r.node.layer),
                     "lingshu_created_at": iso(r.node.created_at)})
        if score is not None:
            meta["score"] = round(float(score), 6)
    return Document(page_content=r.text, metadata=meta, id=ext_id or r.meta.get("_lc_id") or r.id)


# --------------------------------------------------------------------------- 会话历史
class LingshuChatMessageHistory(BaseChatMessageHistory):
    """按 ``session_id`` 存取的会话消息历史（可与 ``RunnableWithMessageHistory`` 直接配合）。

    ``engine`` 缺省按 ``path`` 新建 :class:`lingshu_ng.engine.MemoryEngine`；多个会话 / 多个适配器可共用一个引擎。"""

    def __init__(self, session_id: str, *, engine=None, path: str = ":memory:", namespace: str = "lc"):
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id 必须是非空 str")
        self.session_id = session_id
        self._b = Backend(engine=engine, path=path, namespace=namespace)
        self.engine = self._b.engine

    @property
    def _tags(self) -> List[str]:
        return [self._b.owner_tag, self._b.tag("session", self.session_id)]

    def _records(self) -> List[Record]:
        recs = self._b.by_tags(self._tags)
        recs.sort(key=lambda r: (r.meta.get("seq", 0), r.node.created_at or 0.0, r.id))
        return recs

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore[override]
        dicts = [r.meta["lc_message"] for r in self._records() if isinstance(r.meta.get("lc_message"), dict)]
        return messages_from_dict(dicts)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        msgs = list(messages)
        if not msgs:
            return
        with self._b.db.tx():
            recs = self._records()
            seq = max((int(r.meta.get("seq", 0)) for r in recs), default=0)
            for m in msgs:
                if not isinstance(m, BaseMessage):
                    raise TypeError(f"add_messages 需要 BaseMessage（收到 {type(m).__name__}）")
                seq += 1
                self._b.write(_text(m.content), [self._b.tag("session", self.session_id)],
                              {"lc_message": message_to_dict(m), "seq": seq, "role": m.type,
                               "session_id": self.session_id})

    def clear(self) -> None:
        self._b.delete_many(r.id for r in self._records())


# --------------------------------------------------------------------------- 检索器
class LingshuRetriever(BaseRetriever):
    """LangChain 检索器：``engine.recall`` 组合召回 → ``Document`` 列表（分数在 ``metadata["score"]``）。

    参数：``engine``（必填，:class:`MemoryEngine`）、``k``（缺省 4）、``namespace``（只要某个适配器命名空间写入的记录；
    缺省不限）、``filter``（按写入元数据过滤，口径同 mem0 适配器）、``min_score``（缺省 0）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    engine: Any
    k: int = 4
    namespace: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    min_score: float = 0.0

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun,
                                k: Optional[int] = None, **kwargs: Any) -> List[Document]:
        """``invoke(query, k=3)`` 可临时覆盖 ``self.k``（LangChain 标准检索器约定）。"""
        k = int(self.k if k is None else k)
        b = Backend(engine=self.engine, namespace=self.namespace or "_")
        own = b.owner_tag if self.namespace else None

        def keep(r: Record) -> bool:
            return ((own is None or own in r.tags) and (r.score or 0.0) >= self.min_score
                    and match_filters(r.meta, self.filter))

        return [record_document(r, r.score) for r in b.search(query, k, keep)]


# --------------------------------------------------------------------------- 向量库接口
class LingshuVectorStore(VectorStore):
    """``VectorStore`` 接口的 lingshu_ng 实现（检索不用外部向量；见模块说明）。

    ``collection_name`` 把同一引擎里的多个集合隔开（同一 ``namespace`` 下按标签区分）。``fill_k``（缺省 True）：
    召回到的文档不足 ``k`` 条时按写入顺序用其余文档（分数 0）补足——向量库的 kNN 约定；False ⇒ 只返回召回命中。``ids`` 为调用方给定的外部 id：
    同 id 再次写入 = 覆盖（先删后写）。"""

    def __init__(self, embedding: Any = None, *, engine=None, path: str = ":memory:", namespace: str = "lcvs",
                 collection_name: str = "default", fill_k: bool = True):
        self._embedding = embedding
        #: True（缺省）⇒ 召回不足 k 条时用集合里其余文档（0 分）补足，符合 VectorStore「返回 k 个最近邻」的约定
        self.fill_k = bool(fill_k)
        self._b = Backend(engine=engine, path=path, namespace=namespace)
        self.engine = self._b.engine
        self.collection_name = collection_name

    @property
    def embeddings(self):
        return self._embedding

    # ------------------------------------------------------------ 内部
    @property
    def _scope(self) -> List[str]:
        return [self._b.tag("collection", self.collection_name)]

    def _id_tag(self, ext_id: str) -> str:
        return self._b.tag("id", ext_id)

    def _by_ext(self, ext_id: str) -> List[Record]:
        return self._b.by_tags([self._id_tag(ext_id), self._b.owner_tag] + self._scope)

    # ------------------------------------------------------------ 写
    def add_texts(self, texts: Iterable[str], metadatas: Optional[List[Dict[str, Any]]] = None, *,
                  ids: Optional[List[str]] = None, **kwargs: Any) -> List[str]:
        texts = list(texts)
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError(f"metadatas 条数 {len(metadatas)} ≠ texts 条数 {len(texts)}")
        if ids is not None and len(ids) != len(texts):
            raise ValueError(f"ids 条数 {len(ids)} ≠ texts 条数 {len(texts)}")
        out: List[str] = []
        with self._b.db.tx():
            for i, t in enumerate(texts):
                meta = dict((metadatas or [None] * len(texts))[i] or {})
                ext = ids[i] if ids is not None and ids[i] else None
                if ext is not None:
                    ext = str(ext)
                    self._b.delete_many(r.id for r in self._by_ext(ext))
                    meta["_lc_id"] = ext
                    nid, _ = self._b.write(t, self._scope, meta, extra_tags=[self._id_tag(ext)])
                else:
                    nid, _ = self._b.write(t, self._scope, meta)
                    ext = nid
                    self._b.update(nid, meta={"_lc_id": nid})
                    self._b.nodes.add_tags(nid, [self._id_tag(nid)])
                out.append(ext)
        return out

    def delete(self, ids: Optional[List[str]] = None, **kwargs: Any) -> Optional[bool]:
        """按外部 id 删除；``ids=None`` ⇒ 删除本集合全部（LangChain 约定）。"""
        if ids is None:
            self._b.delete_many(r.id for r in self._b.by_tags([self._b.owner_tag] + self._scope))
            return True
        with self._b.db.tx():
            for i in ids:
                self._b.delete_many(r.id for r in self._by_ext(str(i)))
        return True

    # ------------------------------------------------------------ 读
    def get_by_ids(self, ids: Sequence[str], /) -> List[Document]:
        out: List[Document] = []
        for i in ids:
            for r in self._by_ext(str(i)):
                out.append(record_document(r, ext_id=str(i), provenance=False))
        return out

    def similarity_search_with_score(self, query: str, k: int = 4, filter: Optional[Dict[str, Any]] = None,
                                     **kwargs: Any) -> List[Tuple[Document, float]]:
        need = set(self._scope) | {self._b.owner_tag}

        def keep(r: Record) -> bool:
            return need <= set(r.tags) and match_filters(r.meta, filter)

        k = int(k)
        hits = self._b.search(query, k, keep)
        if self.fill_k and len(hits) < k:
            # 向量库约定：返回 min(k, 集合大小) 条最近邻。词面 / 语义召回不到的其余文档以 0 分按写入顺序补足。
            seen = {r.id for r in hits}
            for r in self._b.by_tags([self._b.owner_tag] + self._scope):
                if len(hits) >= k:
                    break
                if r.id not in seen and match_filters(r.meta, filter):
                    r.score = 0.0
                    hits.append(r)
        return [(record_document(r, provenance=False), float(r.score or 0.0)) for r in hits]

    def similarity_search(self, query: str, k: int = 4, **kwargs: Any) -> List[Document]:
        return [d for d, _ in self.similarity_search_with_score(query, k, **kwargs)]

    def _similarity_search_with_relevance_scores(self, query: str, k: int = 4,
                                                 **kwargs: Any) -> List[Tuple[Document, float]]:
        """相关度 ∈ [0, 1]：引擎组合召回分截到 [0, 1]（防御性截断；组合召回分通常已落在 0–1）。"""
        return [(d, min(1.0, max(0.0, s))) for d, s in self.similarity_search_with_score(query, k, **kwargs)]

    @classmethod
    def from_texts(cls, texts: List[str], embedding: Any = None, metadatas: Optional[List[Dict[str, Any]]] = None, *,
                   ids: Optional[List[str]] = None, **kwargs: Any) -> "LingshuVectorStore":
        vs = cls(embedding, **kwargs)
        vs.add_texts(texts, metadatas, ids=ids)
        return vs
