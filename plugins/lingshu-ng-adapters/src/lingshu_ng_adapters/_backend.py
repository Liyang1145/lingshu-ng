# -*- coding: utf-8 -*-
"""适配器共用后端：在一个 :class:`lingshu_ng.engine.MemoryEngine` 上提供「带作用域的记录」读写。

- 记录 = 知识层节点（``skip_dedup=True`` 写入：去重由本层**在作用域内**判定——核心 M5 去重不看标签，
  直接用会把不同 user_id 的同一句话合并成一个节点，造成租户串号）。
- 作用域 = 精确标签（``<ns>:<键>:<值>``，例如 ``mem0:user_id:alice``）；标签查询走 ``json_each`` 精确匹配（核心 N2），
  不会出现 ``alice`` 命中 ``alice2``。
- 元数据 = 节点 ``state_attributes["ad_meta"]``（JSON 可序列化字典）；不进标签、不影响召回打分。
- 变更历史 = 同一个 SQLite 库里的旁表 ``ngad_history``（适配器自建，不在核心 schema 内；核心 ``export_all`` 不导出它）。

本模块只用标准库与核心公开组件（``engine.store.nodes`` / ``engine.store.db`` / ``engine.recall``）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import threading
import uuid
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = ["Backend", "Record", "match_filters", "iso"]

META = "ad_meta"
HISTORY_DDL = ("CREATE TABLE IF NOT EXISTS ngad_history (id TEXT PRIMARY KEY, memory_id TEXT, old_memory TEXT, "
               "new_memory TEXT, event TEXT, created_at TEXT, updated_at TEXT, is_deleted INTEGER, "
               "actor_id TEXT, role TEXT, seq INTEGER)")
HISTORY_IDX = "CREATE INDEX IF NOT EXISTS ngad_history_mid ON ngad_history(memory_id, seq)"


def iso(ts: Optional[float]) -> Optional[str]:
    """epoch 秒 → ISO 8601（UTC，带时区）；None → None。"""
    if ts is None:
        return None
    return _dt.datetime.fromtimestamp(float(ts), _dt.timezone.utc).isoformat()


def md5(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()


class Record:
    """一条记录的只读视图（节点 + 适配器元数据 + 分数）。"""
    __slots__ = ("node", "meta", "score")

    def __init__(self, node, score: Optional[float] = None):
        self.node = node
        sa = node.state_attributes if isinstance(node.state_attributes, dict) else {}
        m = sa.get(META)
        self.meta: Dict[str, Any] = dict(m) if isinstance(m, dict) else {}
        self.score = score

    @property
    def id(self) -> str:
        return self.node.id

    @property
    def text(self) -> str:
        return self.node.content or ""

    @property
    def tags(self) -> List[str]:
        return list(self.node.tags or [])


# --------------------------------------------------------------------------- 元数据过滤（mem0 2.x 口径的子集）
_OPS = ("eq", "ne", "in", "nin", "gt", "gte", "lt", "lte", "contains", "icontains")


def _cmp(v: Any, op: str, want: Any) -> bool:
    try:
        if op == "eq":
            return v == want
        if op == "ne":
            return v != want
        if op == "in":
            return v in want
        if op == "nin":
            return v not in want
        if v is None:
            return False
        if op == "gt":
            return v > want
        if op == "gte":
            return v >= want
        if op == "lt":
            return v < want
        if op == "lte":
            return v <= want
        if op == "contains":
            return str(want) in str(v)
        if op == "icontains":
            return str(want).lower() in str(v).lower()
    except TypeError:
        return False
    raise ValueError(f"未知过滤运算符 {op!r}；可用 {list(_OPS)}")


def match_filters(fields: Dict[str, Any], flt: Optional[Dict[str, Any]]) -> bool:
    """``{"k": v}`` 精确、``{"k": {"op": v}}`` 运算符、``{"k": "*"}`` 通配（键存在即可）、
    ``AND`` / ``OR`` / ``NOT`` 逻辑组合。缺键：除 ``ne`` / ``nin`` 外都判不命中。"""
    if not flt:
        return True
    for k, want in flt.items():
        if k in ("AND", "OR", "NOT"):
            subs = want if isinstance(want, list) else [want]
            if k == "AND" and not all(match_filters(fields, s) for s in subs):
                return False
            if k == "OR" and not any(match_filters(fields, s) for s in subs):
                return False
            if k == "NOT" and any(match_filters(fields, s) for s in subs):
                return False
            continue
        has, v = k in fields, fields.get(k)
        if want == "*":
            if not has:
                return False
            continue
        if isinstance(want, dict) and want and set(want) <= set(_OPS):
            for op, w in want.items():
                if not has and op not in ("ne", "nin"):
                    return False
                if not _cmp(v, op, w):
                    return False
            continue
        if not has or v != want:
            return False
    return True


# --------------------------------------------------------------------------- 后端
class Backend:
    """一个引擎 + 一个命名空间（标签前缀）。线程安全由核心 Database 的可重入锁保证；本层的多步操作包在 ``db.tx()`` 里。"""

    def __init__(self, engine=None, path: str = ":memory:", namespace: str = "ad"):
        if engine is None:
            from lingshu_ng.engine import MemoryEngine
            engine = MemoryEngine(path)
        self.engine = engine
        self.ns = str(namespace)
        self._hist_ready = False
        self._lock = threading.RLock()

    # ------------------------------------------------------------ 标签
    def tag(self, key: str, value: Any) -> str:
        return f"{self.ns}:{key}:{value}"

    @property
    def owner_tag(self) -> str:
        """本命名空间写入的每条记录都带它（reset / 计数只动自己的记录）。"""
        return f"{self.ns}:owned"

    @property
    def nodes(self):
        return self.engine.store.nodes

    @property
    def db(self):
        return self.engine.store.db

    # ------------------------------------------------------------ 写
    def write(self, text: str, scope_tags: Sequence[str] = (), meta: Optional[Dict[str, Any]] = None,
              dedup: bool = False, importance: float = 0.5, extra_tags: Sequence[str] = ()) -> Tuple[str, bool]:
        """写一条记录，返回 (节点 id, 是否新建)。``dedup`` ⇒ 同作用域（scope_tags 全同）内规范化正文相同的已有记录直接复用。"""
        from lingshu_ng import dedup as _dd
        from lingshu_ng.types import MemoryLayer
        tags = [self.owner_tag] + list(scope_tags) + list(extra_tags)
        with self.db.tx():
            if dedup:
                want = {t for t in tags if t.startswith(self.ns + ":") and t != self.owner_tag}
                for n in self.nodes.by_key(_dd.content_key(text), [MemoryLayer.KNOWLEDGE]):
                    if self.owner_tag in n.tags and _same_scope(n.tags, want, self.ns):
                        return n.id, False
            w = self.engine.perceive(text, tags=tags, skip_dedup=True, importance=importance,
                                     layer=MemoryLayer.KNOWLEDGE)
            if meta:
                sa = dict(self.nodes.get(w.node_id).state_attributes or {})
                sa[META] = dict(meta)
                self.nodes.update(w.node_id, state_attributes=sa)
        return w.node_id, True

    def update(self, node_id: str, text: Optional[str] = None, meta: Optional[Dict[str, Any]] = None,
               merge_meta: bool = True) -> bool:
        with self.db.tx():
            n = self.nodes.get(node_id)
            if n is None:
                return False
            fields: Dict[str, Any] = {}
            if text is not None:
                fields["content"] = text
            if meta is not None:
                sa = dict(n.state_attributes or {})
                old = dict(sa.get(META) or {}) if merge_meta else {}
                old.update(meta)
                sa[META] = old
                fields["state_attributes"] = sa
            from lingshu_ng.types import now
            fields["last_access"] = now()
            self.nodes.update(node_id, **fields)
        if text is not None:
            for idx in (getattr(self.engine, "semantic", None), getattr(self.engine, "chain", None)):
                if idx is not None:
                    idx.note(node_id, text)
        return True

    def delete(self, node_id: str) -> bool:
        return self.nodes.delete(node_id)

    def delete_many(self, ids: Iterable[str]) -> int:
        k = 0
        with self.db.tx():
            for i in list(ids):
                k += bool(self.nodes.delete(i))
        return k

    # ------------------------------------------------------------ 读
    def get(self, node_id: str) -> Optional[Record]:
        n = self.nodes.get(node_id)
        return Record(n) if n is not None else None

    def by_tags(self, tags: Sequence[str]) -> List[Record]:
        """同时带有全部 ``tags`` 的记录（第一个标签走索引精确查，其余在内存里核对），按写入先后。"""
        tags = list(tags) or [self.owner_tag]
        first, rest = tags[0], set(tags[1:])
        out = [Record(n) for n in self.nodes.by_tag(first, limit=None) if rest <= set(n.tags)]
        out.sort(key=lambda r: (r.node.created_at or 0.0, r.id))
        return out

    def search(self, query: str, k: int, keep: Callable[[Record], bool], max_scan: Optional[int] = None) -> List[Record]:
        """引擎组合召回（``engine.recall``，含可选语义 / 重排 / 版本链）→ 按 ``keep`` 过滤作用域与元数据；
        不足 ``k`` 条且召回池已满时把池扩大一倍再取，直至池不再变满或到达库容量（作用域过滤不会因池太小而漏召）。"""
        if k <= 0 or not isinstance(query, str) or not query.strip():
            return []
        total = self.nodes.count()
        cap = total if max_scan is None else min(total, max_scan)
        pool = max(k * 4, 40)
        while True:
            hits = self.engine.recall(query, min(pool, max(cap, 1)))["hits"]
            out, seen = [], set()
            for n, s in hits:
                if n.id in seen:
                    continue
                seen.add(n.id)
                r = Record(n, float(s))
                if keep(r):
                    out.append(r)
                    if len(out) >= k:
                        return out
            if len(hits) < min(pool, cap) or pool >= cap:
                return out
            pool *= 2

    # ------------------------------------------------------------ 历史（mem0 history 形状）
    def _hist(self) -> None:
        if not self._hist_ready:
            with self.db.tx() as c:
                c.execute(HISTORY_DDL)
                c.execute(HISTORY_IDX)
            self._hist_ready = True

    def add_history(self, memory_id: str, old: Optional[str], new: Optional[str], event: str,
                    created_at: Optional[str] = None, updated_at: Optional[str] = None,
                    is_deleted: bool = False, actor_id: Optional[str] = None, role: Optional[str] = None) -> None:
        self._hist()
        with self.db.tx() as c:
            seq = c.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM ngad_history").fetchone()[0]
            c.execute("INSERT INTO ngad_history VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (str(uuid.uuid4()), memory_id, old, new, event, created_at, updated_at,
                       int(bool(is_deleted)), actor_id, role, seq))

    def history(self, memory_id: str) -> List[Dict[str, Any]]:
        self._hist()
        rows = self.db.all("SELECT id, memory_id, old_memory, new_memory, event, created_at, updated_at, is_deleted, "
                           "actor_id, role FROM ngad_history WHERE memory_id=? ORDER BY seq", (memory_id,))
        return [{"id": r[0], "memory_id": r[1], "old_memory": r[2], "new_memory": r[3], "event": r[4],
                 "created_at": r[5], "updated_at": r[6], "is_deleted": bool(r[7]), "actor_id": r[8], "role": r[9]}
                for r in rows]

    def clear_history(self) -> None:
        self._hist()
        with self.db.tx() as c:
            c.execute("DELETE FROM ngad_history")

    def close(self) -> None:
        self.engine.close()


def _same_scope(tags: Sequence[str], want: set, ns: str) -> bool:
    """节点的作用域标签（``<ns>:`` 前缀、非 owned）与 ``want`` 完全相同。"""
    have = {t for t in tags if t.startswith(ns + ":") and t != f"{ns}:owned"}
    return have == set(want)
