# -*- coding: utf-8 -*-
"""mem0 兼容 API（纯标准库，不依赖 mem0）：把 ``from mem0 import Memory`` 换成
``from lingshu_ng_adapters.mem0 import Memory`` 即可接入 lingshu_ng 作为记忆后端。

对齐对象：mem0ai 2.2.1（PyPI，2026-10 实测签名；源码 mem0/memory/main.py、mem0/memory/storage.py）的
``Memory`` / ``AsyncMemory``：

==============  =====================================================================================
方法             行为
==============  =====================================================================================
add             ``messages``：str / dict / list[dict]；``user_id`` / ``agent_id`` / ``run_id`` 至少一个（同 mem0）。
                返回 ``{"results": [{"id", "memory", "event": "ADD"}]}``。
get             ``{"id", "memory", "hash", "created_at", "updated_at", <user_id/agent_id/run_id/actor_id/role/
                expiration_date>, "metadata"}``；不存在 ⇒ ``None``。
get_all         ``filters`` 必须含 user_id / agent_id / run_id 之一（同 mem0 2.x）；``{"results": [...]}``，新→旧。
search          ``{"results": [... , "score"]}``，分数降序，``threshold`` 过滤（缺省 0.1，同 mem0）。
update          ``text`` / ``metadata`` / ``expiration_date`` 至少一个；``data`` 为 ``text`` 的旧别名；
                返回 ``{"message": "Memory updated successfully!"}``；不存在 ⇒ ``ValueError``。
delete          ``{"message": "Memory deleted successfully!"}``；不存在 ⇒ ``ValueError``。
delete_all      至少一个实体 id；``{"message": "Memories deleted successfully!"}``。
history         ``[{"id", "memory_id", "old_memory", "new_memory", "event", "created_at", "updated_at",
                "is_deleted", "actor_id", "role"}]``，时间正序（同 mem0 SQLiteManager.get_history）。
reset           清空本适配器命名空间写入的全部记忆与历史（**不动**同一库里其它来源写入的节点）。
==============  =====================================================================================

有意的不同（零 LLM 写入是 lingshu_ng 的设计前提）：

- ``infer=True`` 不调用 LLM 抽取事实：每条非 system 消息的**原文**作为一条记忆写入；同一作用域
  （user_id/agent_id/run_id 组合完全相同）内规范化正文相同的记忆不重复写（该条不出现在返回 results 里，
  对应 mem0 的 NONE 事件）。``infer=False`` 与 mem0 相同：逐条原样写入、不去重。
- ``memory_type="procedural_memory"``（需 LLM 总结）⇒ ``NotImplementedError``；``prompt`` 被忽略（打一次 WARNING）。
- ``search`` / ``get_all`` 额外接受 mem0 0.x/1.x 的顶层 ``user_id`` / ``agent_id`` / ``run_id`` / ``limit``
  （合并进 ``filters`` / ``top_k``），mem0 2.x 对此抛 ``ValueError``；旧代码因此可原样运行。
- ``score`` 是 lingshu_ng 组合召回分（词面 + 可选语义 / 重排），不是向量余弦；``rerank`` 参数被接受但无额外作用
  （重排是否启用由引擎档位决定，见 ``engine.capabilities()``）。
- 作用域隔离：不同 user_id 的同一句话是两条记忆（核心 M5 去重不看标签，本适配器写入时关闭它、改在作用域内去重）。
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import logging
from typing import Any, Dict, List, Optional

from ._backend import Backend, Record, iso, match_filters, md5

__all__ = ["Memory", "AsyncMemory", "MemoryValidationError"]

_log = logging.getLogger("lingshu_ng_adapters.mem0")
ENTITY_PARAMS = ("user_id", "agent_id", "run_id")
_IDENTITY = set(ENTITY_PARAMS) | {"actor_id"}
_PROMOTED = ("user_id", "agent_id", "run_id", "actor_id", "role", "expiration_date")
_RESERVED = set(_PROMOTED) | {"_ts", "_updated_at"}
_UNSET = object()
_warned = set()


class MemoryValidationError(ValueError):
    """入参不合法（对应 mem0 的 ``Mem0ValidationError``；``ValueError`` 子类）。"""


def _warn_once(key: str, msg: str) -> None:
    if key not in _warned:
        _warned.add(key)
        _log.warning(msg)


def _entity(value: Any, name: str) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip()
    if not v:
        raise MemoryValidationError(f"{name} 不能为空字符串")
    return v


def _norm_date(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date().isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    try:
        return _dt.date.fromisoformat(str(v).strip()[:10]).isoformat()
    except ValueError as e:
        raise MemoryValidationError(f"expiration_date 须为 YYYY-MM-DD：{v!r}") from e


def _norm_ts(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, _dt.datetime):
        return (v if v.tzinfo else v.replace(tzinfo=_dt.timezone.utc)).timestamp()
    try:
        d = _dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError as e:
        raise MemoryValidationError(f"timestamp 须为 epoch 秒或 ISO 8601：{v!r}") from e
    return (d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)).timestamp()


def _text_of(content: Any) -> str:
    """消息 content：str 或 OpenAI 多段 list[{"type": "text", "text": ...}]（图像段跳过）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content
                         if isinstance(p, dict) and p.get("type") in (None, "text") and p.get("text"))
    if isinstance(content, dict) and content.get("type") in (None, "text"):
        return str(content.get("text", ""))
    return "" if content is None else str(content)


def _expired(meta: Dict[str, Any], today: Optional[str] = None) -> bool:
    exp = meta.get("expiration_date")
    return bool(exp) and str(exp) < (today or _dt.date.today().isoformat())


class Memory:
    """mem0 ``Memory`` 的同名同签名实现，后端为 :class:`lingshu_ng.engine.MemoryEngine`。

    构造：``Memory()``（进程内库）、``Memory(path="/data/mem.sqlite")``、``Memory(engine=已有引擎)``，或
    ``Memory.from_config({"path": ...})`` / ``Memory.from_config({"lingshu": {"path": ..., "namespace": ...}})``。
    ``namespace``（缺省 ``"mem0"``）把本适配器的记忆与同库其它来源隔开。
    """

    def __init__(self, config: Any = None, *, engine=None, path: Optional[str] = None, namespace: str = "mem0"):
        if isinstance(config, dict):
            sub = config.get("lingshu") if isinstance(config.get("lingshu"), dict) else config
            path = path or sub.get("path")
            namespace = sub.get("namespace", namespace)
        self._b = Backend(engine=engine, path=path or ":memory:", namespace=namespace)
        self.engine = self._b.engine
        self.api_version = "v1.1"

    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> "Memory":
        """``{"path": str, "namespace": str}`` 或 ``{"lingshu": {...}}``；mem0 其它配置键（llm / embedder /
        vector_store …）与零 LLM 后端无关，被忽略（打一次 WARNING）。"""
        cfg = dict(config_dict or {})
        other = set(cfg) - {"path", "namespace", "lingshu"}
        if other:
            _warn_once("from_config", f"Memory.from_config：忽略与 lingshu_ng 后端无关的配置键 {sorted(other)}")
        return cls(cfg)

    # ------------------------------------------------------------ 内部
    def _item(self, r: Record, score: Optional[float] = None, explain: bool = False) -> Dict[str, Any]:
        m = r.meta
        created = m.get("_ts", r.node.created_at)
        d: Dict[str, Any] = {"id": r.id, "memory": r.text, "hash": md5(r.text), "created_at": iso(created),
                             "updated_at": iso(m.get("_updated_at", created))}
        for k in _PROMOTED:
            if k in m and m[k] is not None:
                d[k] = m[k]
        extra = {k: v for k, v in m.items() if k not in _RESERVED}
        if extra:
            d["metadata"] = extra
        if score is not None:
            d["score"] = round(float(score), 6)
            if explain:
                d["score_details"] = {"source": "lingshu_ng.engine.recall", "score": round(float(score), 6)}
        return d

    @staticmethod
    def _filters(filters: Optional[Dict[str, Any]], kwargs: Dict[str, Any], method: str) -> Dict[str, Any]:
        f = dict(filters or {})
        for k in ENTITY_PARAMS:
            if k in kwargs:
                v = kwargs.pop(k)
                if v is not None:
                    f.setdefault(k, v)
        for k in ENTITY_PARAMS:
            if k in f and not isinstance(f[k], dict) and f[k] != "*":
                f[k] = _entity(f[k], k)
        if not any(k in f for k in ENTITY_PARAMS):
            raise MemoryValidationError(f"{method}()：filters 必须含 user_id / agent_id / run_id 之一，"
                                        "例如 filters={'user_id': 'u1'}")
        return f

    @staticmethod
    def _rest(kwargs: Dict[str, Any], method: str) -> None:
        if kwargs:
            _warn_once(f"kw:{method}:{sorted(kwargs)}", f"{method}()：忽略未支持的参数 {sorted(kwargs)}")

    def _scope_tags(self, f: Dict[str, Any]) -> List[str]:
        return [self._b.tag(k, f[k]) for k in ENTITY_PARAMS if isinstance(f.get(k), str) and f[k] != "*"]

    # ------------------------------------------------------------ add
    def add(self, messages, *, user_id: Optional[str] = None, agent_id: Optional[str] = None,
            run_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
            timestamp: Optional[Any] = None, expiration_date: Optional[Any] = None, infer: bool = True,
            memory_type: Optional[str] = None, prompt: Optional[str] = None):
        ids = {k: _entity(v, k) for k, v in (("user_id", user_id), ("agent_id", agent_id), ("run_id", run_id))}
        ids = {k: v for k, v in ids.items() if v}
        if not ids:
            raise MemoryValidationError("At least one of 'user_id', 'agent_id', or 'run_id' must be provided.")
        if memory_type is not None:
            if memory_type != "procedural_memory":
                raise MemoryValidationError("memory_type 只接受 'procedural_memory'")
            raise NotImplementedError("procedural_memory 需要 LLM 总结，lingshu_ng 零 LLM 写入不提供；请改用普通 add()")
        if prompt is not None:
            _warn_once("prompt", "add(prompt=...)：lingshu_ng 不调用 LLM，prompt 被忽略")
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        elif isinstance(messages, dict):
            messages = [messages]
        elif not isinstance(messages, list):
            raise MemoryValidationError(f"messages must be str, dict, or list[dict]（收到 {type(messages).__name__}）")
        if metadata is not None and not isinstance(metadata, dict):
            raise MemoryValidationError("metadata 必须是 dict")
        base = {k: v for k, v in (metadata or {}).items() if k not in _IDENTITY and k not in ("_ts", "_updated_at")}
        dropped = sorted(set(metadata or {}) & _IDENTITY)
        if dropped:
            _warn_once("idmeta", f"add()：忽略 metadata 里的身份键 {dropped}（作用域只由 user_id/agent_id/run_id 参数决定）")
        base.update(ids)
        exp = _norm_date(expiration_date)
        if exp:
            base["expiration_date"] = exp
        ts = _norm_ts(timestamp)
        if ts is not None:
            base["_ts"] = ts
        scope = [self._b.tag(k, v) for k, v in sorted(ids.items())]
        out: List[Dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                raise MemoryValidationError("messages 列表的元素必须是 dict（{'role': ..., 'content': ...}）")
            role = msg.get("role", "user")
            if role == "system":
                continue
            text = _text_of(msg.get("content")).strip()
            if not text:
                continue
            meta = dict(base, role=role)
            if msg.get("name"):
                meta["actor_id"] = str(msg["name"])
            nid, created = self._b.write(text, scope, meta, dedup=bool(infer))
            if created:
                r = self._b.get(nid)
                c = iso(meta.get("_ts", r.node.created_at))
                self._b.add_history(nid, None, text, "ADD", created_at=c, updated_at=c,
                                    actor_id=meta.get("actor_id"), role=role)
                out.append({"id": nid, "memory": text, "event": "ADD"})
        return {"results": out}

    # ------------------------------------------------------------ 读
    def get(self, memory_id):
        r = self._b.get(str(memory_id))
        if r is None or self._b.owner_tag not in r.tags:
            return None
        return self._item(r)

    def get_all(self, *, filters: Optional[Dict[str, Any]] = None, top_k: int = 20, show_expired: bool = False,
                **kwargs):
        if "limit" in kwargs:
            top_k = kwargs.pop("limit")
        f = self._filters(filters, kwargs, "get_all")
        self._rest(kwargs, "get_all")
        top_k = _top_k(top_k)
        recs = self._b.by_tags([self._b.owner_tag] + self._scope_tags(f))
        out = [r for r in recs if match_filters(r.meta, f) and (show_expired or not _expired(r.meta))]
        out.sort(key=lambda r: (-(r.meta.get("_ts", r.node.created_at) or 0.0), r.id))
        return {"results": [self._item(r) for r in out[:top_k]]}

    def search(self, query: str, *, top_k: int = 20, filters: Optional[Dict[str, Any]] = None,
               threshold: float = 0.1, rerank: bool = False, explain: bool = False,
               reference_date: Optional[Any] = None, show_expired: bool = False, **kwargs):
        if reference_date is not None:
            raise MemoryValidationError("reference_date 是 mem0 平台版功能（OSS 同样不支持）")
        if "limit" in kwargs:
            top_k = kwargs.pop("limit")
        f = self._filters(filters, kwargs, "search")
        self._rest(kwargs, "search")
        top_k = _top_k(top_k)
        if threshold is not None and not (0.0 <= float(threshold) <= 1.0):
            raise MemoryValidationError("threshold 须在 [0, 1]")
        if not isinstance(query, str) or not query.strip():
            raise MemoryValidationError("query 不能为空")
        th = 0.0 if threshold is None else float(threshold)
        need = set(self._scope_tags(f)) | {self._b.owner_tag}

        def keep(r: Record) -> bool:
            return (need <= set(r.tags) and (r.score or 0.0) >= th and match_filters(r.meta, f)
                    and (show_expired or not _expired(r.meta)))

        hits = self._b.search(query.strip(), top_k, keep)
        return {"results": [self._item(r, r.score, explain) for r in hits]}

    # ------------------------------------------------------------ 改 / 删
    def update(self, memory_id, text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
               expiration_date: Any = _UNSET, data: Optional[str] = None):
        if data is not None:
            _warn_once("data", "update(data=...) 已弃用（同 mem0），请改用 text=")
            if text is None:
                text = data
        if text is None and metadata is None and expiration_date is _UNSET:
            raise MemoryValidationError("At least one of text, metadata, or expiration_date must be provided.")
        mid = str(memory_id)
        r = self._b.get(mid)
        if r is None or self._b.owner_tag not in r.tags:
            raise ValueError(f"Error getting memory with ID {mid}. Please provide a valid 'memory_id'")
        meta: Dict[str, Any] = {}
        if metadata is not None:
            if not isinstance(metadata, dict):
                raise MemoryValidationError("metadata 必须是 dict")
            meta.update({k: v for k, v in metadata.items() if k not in _IDENTITY and k not in ("_ts", "_updated_at")})
        if expiration_date is not _UNSET:
            meta["expiration_date"] = _norm_date(expiration_date)
        from lingshu_ng.types import now
        t = now()
        meta["_updated_at"] = t
        if text is not None and not isinstance(text, str):
            raise MemoryValidationError("text 必须是 str")
        self._b.update(mid, text=text, meta=meta)
        self._b.add_history(mid, r.text, text if text is not None else r.text, "UPDATE",
                            created_at=iso(r.meta.get("_ts", r.node.created_at)), updated_at=iso(t),
                            actor_id=r.meta.get("actor_id"), role=r.meta.get("role"))
        return {"message": "Memory updated successfully!"}

    def _delete_record(self, r: Record) -> None:
        from lingshu_ng.types import now
        self._b.delete(r.id)
        self._b.add_history(r.id, r.text, None, "DELETE", created_at=iso(r.meta.get("_ts", r.node.created_at)),
                            updated_at=iso(now()), is_deleted=True, actor_id=r.meta.get("actor_id"),
                            role=r.meta.get("role"))

    def delete(self, memory_id):
        mid = str(memory_id)
        r = self._b.get(mid)
        if r is None or self._b.owner_tag not in r.tags:
            raise ValueError(f"Memory with id {mid} not found")
        self._delete_record(r)
        return {"message": "Memory deleted successfully!"}

    def delete_all(self, user_id: Optional[str] = None, agent_id: Optional[str] = None, run_id: Optional[str] = None):
        ids = {k: _entity(v, k) for k, v in (("user_id", user_id), ("agent_id", agent_id), ("run_id", run_id))}
        ids = {k: v for k, v in ids.items() if v}
        if not ids:
            raise MemoryValidationError("At least one filter is required to delete all memories. "
                                        "If you want to delete all memories, use the `reset()` method.")
        recs = self._b.by_tags([self._b.owner_tag] + [self._b.tag(k, v) for k, v in sorted(ids.items())])
        with self._b.db.tx():
            for r in recs:
                self._delete_record(r)
        return {"message": "Memories deleted successfully!"}

    def history(self, memory_id):
        return self._b.history(str(memory_id))

    def reset(self):
        """删除本命名空间的全部记忆与历史（同库其它来源写入的节点不动）。"""
        recs = self._b.by_tags([self._b.owner_tag])
        self._b.delete_many(r.id for r in recs)
        self._b.clear_history()

    def close(self) -> None:
        """关闭底层引擎（mem0 无此方法；长驻进程退出前调用即可）。"""
        self._b.close()


def _top_k(v: Any) -> int:
    try:
        k = int(v)
    except (TypeError, ValueError) as e:
        raise MemoryValidationError(f"top_k 须为正整数：{v!r}") from e
    if k <= 0:
        raise MemoryValidationError(f"top_k 须为正整数：{v!r}")
    return k


class AsyncMemory:
    """mem0 ``AsyncMemory`` 对应物：同一组方法的 ``async`` 版本（在线程池里调用 :class:`Memory`；SQLite 单连接串行）。"""

    def __init__(self, config: Any = None, *, engine=None, path: Optional[str] = None, namespace: str = "mem0"):
        self._m = Memory(config, engine=engine, path=path, namespace=namespace)
        self.engine = self._m.engine

    @classmethod
    def from_config(cls, config_dict: Dict[str, Any]) -> "AsyncMemory":
        a = cls.__new__(cls)
        a._m = Memory.from_config(config_dict)
        a.engine = a._m.engine
        return a

    async def add(self, messages, *, user_id: Optional[str] = None, agent_id: Optional[str] = None,
                  run_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                  timestamp: Optional[Any] = None, expiration_date: Optional[Any] = None, infer: bool = True,
                  memory_type: Optional[str] = None, prompt: Optional[str] = None, llm=None):
        return await asyncio.to_thread(self._m.add, messages, user_id=user_id, agent_id=agent_id, run_id=run_id,
                                       metadata=metadata, timestamp=timestamp, expiration_date=expiration_date,
                                       infer=infer, memory_type=memory_type, prompt=prompt)

    async def get(self, memory_id):
        return await asyncio.to_thread(self._m.get, memory_id)

    async def get_all(self, *, filters: Optional[Dict[str, Any]] = None, top_k: int = 20,
                      show_expired: bool = False, **kwargs):
        return await asyncio.to_thread(lambda: self._m.get_all(filters=filters, top_k=top_k,
                                                               show_expired=show_expired, **kwargs))

    async def search(self, query: str, *, top_k: int = 20, filters: Optional[Dict[str, Any]] = None,
                     threshold: float = 0.1, rerank: bool = False, explain: bool = False,
                     reference_date: Optional[Any] = None, show_expired: bool = False, **kwargs):
        return await asyncio.to_thread(lambda: self._m.search(
            query, top_k=top_k, filters=filters, threshold=threshold, rerank=rerank, explain=explain,
            reference_date=reference_date, show_expired=show_expired, **kwargs))

    async def update(self, memory_id, text: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                     expiration_date: Any = _UNSET, data: Optional[str] = None):
        return await asyncio.to_thread(self._m.update, memory_id, text, metadata, expiration_date, data)

    async def delete(self, memory_id):
        return await asyncio.to_thread(self._m.delete, memory_id)

    async def delete_all(self, user_id=None, agent_id=None, run_id=None):
        return await asyncio.to_thread(self._m.delete_all, user_id, agent_id, run_id)

    async def history(self, memory_id):
        return await asyncio.to_thread(self._m.history, memory_id)

    async def reset(self):
        return await asyncio.to_thread(self._m.reset)

    def close(self) -> None:
        self._m.close()
