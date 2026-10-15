# -*- coding: utf-8 -*-
"""集成面共用的操作层：把 :class:`lingshu_ng.engine.MemoryEngine` 的写入 / 召回 / 状态 / capabilities
包成「JSON 进、JSON 出」的四个函数。HTTP 服务与 MCP 适配器都只调这里，保证两条通道的返回形状一致。

线程：一个 :class:`Service` 持有一个引擎和一把锁，所有操作串行执行（SQLite 单连接；见 docs/API_ng.md §10）。
入参校验沿用引擎本身（:mod:`lingshu_ng.inputs`）：类型错抛 ``TypeError`` / ``ValueError``，由调用方转成 400 /
JSON-RPC 错误。本模块不吞异常。
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from typing import Any, Dict, List, Optional

#: 写入接受的可选字段（其余字段一律拒绝，避免拼写错误被静默忽略）
PERCEIVE_FIELDS = ("content", "tags", "entities", "importance", "confidence", "layer", "skip_dedup")
#: 召回接受的字段
RECALL_FIELDS = ("query", "limit")
#: 单条正文上限（字符）：集成面额外的防护，引擎本身不设上限
MAX_CONTENT_CHARS = 100_000


class BadRequest(ValueError):
    """请求字段不合法（未知字段 / 缺字段 / 类型错）。HTTP 映射为 400，JSON-RPC 映射为 -32602。"""


class NotFound(BadRequest):
    """ent-ui：要操作的节点不存在。HTTP 映射为 404。"""


class Conflict(BadRequest):
    """ent-ui：操作被层规则 / 保护名单拒绝（如删除共享层或受保护节点）。HTTP 映射为 409。"""


#: ent-ui 列表接受的字段与上限
LIST_FIELDS = ("layer", "tag", "offset", "limit")
MAX_PAGE = 200
#: 列表 / 边预览里正文只回前这么多字符（详情页回全文）
PREVIEW_CHARS = 300
#: 节点详情最多回这么多条出边 / 入边
MAX_EDGES = 200
#: 节点 id / 标签的最大长度（字符）
MAX_ID_CHARS = 512
MAX_TAG_CHARS = 512


def _node_id(v: Any) -> str:
    from .. import inputs
    if not isinstance(v, str) or not v or len(v) > MAX_ID_CHARS:
        raise BadRequest(f"id 必须是 1–{MAX_ID_CHARS} 字符的字符串")
    return inputs.content(v, "id")


def _bounded_int(v: Any, name: str, lo: int, hi: int) -> int:
    from .. import inputs
    n = inputs.limit(v, name)
    if n < lo or n > hi:
        raise BadRequest(f"{name} 应在 [{lo}, {hi}] 内（收到 {n}）")
    return n


def _preview(text: Any) -> Dict[str, Any]:
    t = text if isinstance(text, str) else ("" if text is None else str(text))
    return {"content": t[:PREVIEW_CHARS], "truncated": len(t) > PREVIEW_CHARS}


def _split_tags(tags) -> tuple:
    plain = [t for t in tags if not (isinstance(t, str) and t.startswith("ent:"))]
    ents = [t[4:] for t in tags if isinstance(t, str) and t.startswith("ent:")]
    return plain, ents


def _edge_json(e, peer) -> Dict[str, Any]:
    d = {"id": e.id, "source_id": e.source_id, "target_id": e.target_id,
         "relation": getattr(e.relation_type, "value", e.relation_type), "confidence": e.confidence,
         "weight": e.weight, "verified": bool(e.verified), "created_at": e.created_at,
         "source_evidence": e.source_evidence}
    d["peer"] = None if peer is None else {"id": peer.id, "layer": getattr(peer.layer, "value", peer.layer),
                                           **_preview(peer.content)}
    return d


def _check_fields(body: Any, allowed, required) -> Dict[str, Any]:
    if not isinstance(body, dict):
        raise BadRequest("请求体必须是 JSON 对象")
    extra = sorted(set(body) - set(allowed))
    if extra:
        raise BadRequest(f"未知字段 {extra}；可用字段 {list(allowed)}")
    miss = [k for k in required if k not in body]
    if miss:
        raise BadRequest(f"缺少字段 {miss}")
    return body


def node_json(node, score: Optional[float] = None) -> Dict[str, Any]:
    """节点 → JSON 字典（只含对外稳定字段）。"""
    d = {"id": node.id, "content": node.content, "layer": getattr(node.layer, "value", node.layer),
         "tags": list(node.tags), "importance": node.importance, "confidence": node.confidence,
         "created_at": node.created_at}
    if score is not None:
        d["score"] = round(float(score), 6)
    return d


class Service:
    """持有一个引擎的操作层。``engine`` 缺省按 ``path`` 新建 :class:`MemoryEngine`。"""

    def __init__(self, path: str = ":memory:", engine=None):
        if engine is None:
            from ..engine import MemoryEngine
            engine = MemoryEngine(path)
        self.engine, self.path, self.lock = engine, path, threading.Lock()

    def perceive(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """写入一条：``{"content": str, 可选 tags/entities/importance/confidence/layer/skip_dedup}``。"""
        b = _check_fields(body, PERCEIVE_FIELDS, ("content",))
        if isinstance(b["content"], str) and len(b["content"]) > MAX_CONTENT_CHARS:
            raise BadRequest(f"content 超过 {MAX_CONTENT_CHARS} 字符")
        kw = {k: b[k] for k in PERCEIVE_FIELDS[1:] if k in b}
        if "layer" in kw:
            from ..types import MemoryLayer
            kw["layer"] = MemoryLayer.coerce(kw["layer"])
        with self.lock:
            w = self.engine.perceive(b["content"], **kw)
        return {"node_id": w.node_id, "action": w.action, "layer": w.layer, "reason": w.reason}

    def recall(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """召回：``{"query": str, "limit": int=10}`` → ``{"hits": [...], "negative": [...]}``。"""
        b = _check_fields(body, RECALL_FIELDS, ("query",))
        with self.lock:
            r = self.engine.recall(b["query"], b.get("limit", 10))
        neg = [x if isinstance(x, (str, int, float, dict, list, type(None))) else str(x) for x in r["negative"]]
        return {"hits": [node_json(n, s) for n, s in r["hits"]], "negative": neg}

    def status(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """库状态：版本、schema 版本、各层条数。"""
        _check_fields(body or {}, (), ())
        from .. import __version__
        from ..types import MemoryLayer
        with self.lock:
            nodes = self.engine.store.nodes
            counts = {m.value: nodes.count(m) for m in MemoryLayer}
            sv = self.engine.store.db.schema_version
        return {"version": __version__, "schema_version": sv, "db": self.path, "counts": counts,
                "total": sum(counts.values())}

    def capabilities(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """当前生效档位（:meth:`MemoryEngine.capabilities`）。"""
        _check_fields(body or {}, (), ())
        with self.lock:
            return self.engine.capabilities()

    # ------------------------------------------------------------ ent-ui：浏览 / 详情 / 删除 / 导出导入
    def list_nodes(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分页列出：``{"layer"?, "tag"?, "offset"=0, "limit"=50}`` → ``{"nodes", "total", "offset", "limit"}``。

        最新写入在前；正文只回前 :data:`PREVIEW_CHARS` 字符（``truncated`` 标记），全文见 :meth:`get_node`。"""
        b = _check_fields(body or {}, LIST_FIELDS, ())
        layer = None
        if b.get("layer") not in (None, ""):
            from ..types import MemoryLayer
            if not isinstance(b["layer"], str):
                raise BadRequest("layer 必须是字符串")
            layer = MemoryLayer.coerce(b["layer"])
        tag = b.get("tag")
        if tag == "":
            tag = None
        if tag is not None and (not isinstance(tag, str) or len(tag) > MAX_TAG_CHARS):
            raise BadRequest(f"tag 必须是不超过 {MAX_TAG_CHARS} 字符的字符串")
        offset = _bounded_int(b.get("offset", 0), "offset", 0, 10 ** 9)
        limit = _bounded_int(b.get("limit", 50), "limit", 1, MAX_PAGE)
        with self.lock:
            nodes, total = self.engine.store.nodes.page(layer, tag, offset, limit)
        out = []
        for n in nodes:
            tags, ents = _split_tags(list(n.tags))
            out.append({"id": n.id, "layer": getattr(n.layer, "value", n.layer), "tags": tags, "entities": ents,
                        "importance": n.importance, "confidence": n.confidence, "created_at": n.created_at,
                        **_preview(n.content)})
        return {"nodes": out, "total": total, "offset": offset, "limit": limit}

    def get_node(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """节点详情：``{"id"}`` → 全文、标签、实体、重要度、关联边（出 / 入各至多 :data:`MAX_EDGES` 条）。"""
        b = _check_fields(body, ("id",), ("id",))
        nid = _node_id(b["id"])
        with self.lock:
            st = self.engine.store
            n = st.nodes.get(nid)
            if n is None:
                raise NotFound(f"节点 {nid!r} 不存在")
            outs, ins = st.edges.outgoing(nid), st.edges.incoming(nid)
            peers = st.nodes.get_many([e.target_id for e in outs[:MAX_EDGES]] + [e.source_id for e in ins[:MAX_EDGES]])
            protected = nid in set(st.registry.protected_ids())
        from ..layers import LayerPolicy
        tags, ents = _split_tags(list(n.tags))
        cs = n.condition_space
        try:
            cs = json.loads(cs.to_json())
        except (AttributeError, TypeError, ValueError):
            cs = str(cs)
        return {"id": n.id, "content": n.content, "modality": n.modality,
                "layer": getattr(n.layer, "value", n.layer), "tags": tags, "entities": ents,
                "entity_id": n.entity_id, "importance": n.importance, "confidence": n.confidence,
                "access_count": n.access_count, "created_at": n.created_at, "last_access": n.last_access,
                "temporal_coordinate": n.temporal_coordinate, "condition_space": cs,
                "protected": protected, "deletable": LayerPolicy.rule(n.layer).deletable and not protected,
                "edges": {"outgoing": [_edge_json(e, peers.get(e.target_id)) for e in outs[:MAX_EDGES]],
                          "incoming": [_edge_json(e, peers.get(e.source_id)) for e in ins[:MAX_EDGES]],
                          "outgoing_total": len(outs), "incoming_total": len(ins)}}

    def delete_node(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """删除节点及其关联边：``{"id"}``。不存在 ⇒ :class:`NotFound`；共享层 / 受保护 / 级联触及共享层 ⇒ :class:`Conflict`。"""
        b = _check_fields(body, ("id",), ("id",))
        nid = _node_id(b["id"])
        from ..layers import LayerPolicy, LayerViolation
        with self.lock:
            st = self.engine.store
            layer = st.nodes.layer_of(nid)
            if layer is None:
                raise NotFound(f"节点 {nid!r} 不存在")
            if not LayerPolicy.rule(layer).deletable:
                raise Conflict(f"{layer.value} 层节点不可删除")
            if nid in set(st.registry.protected_ids()):
                raise Conflict("节点在保护名单中，拒绝删除")
            n_edges = len(st.edges.outgoing(nid)) + len(st.edges.incoming(nid))
            try:
                st.policy.check_node_cascade(st.edges, st.nodes, nid)
                ok = st.nodes.delete(nid)
            except LayerViolation as e:
                raise Conflict(f"层规则拒绝删除：{e}") from None
        if not ok:
            raise NotFound(f"节点 {nid!r} 不存在")
        return {"deleted": True, "id": nid, "layer": layer.value, "edges_removed": n_edges}

    def export_backup(self, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """全库导出：→ ``{"report": {...}, "backup": <与 MemoryEngine.export_all 写出的 JSON 相同>}``。"""
        _check_fields(body or {}, (), ())
        d = tempfile.mkdtemp(prefix="lingshu-ng-export-")
        try:
            path = os.path.join(d, "backup.json")
            with self.lock:
                rep = self.engine.export_all(path)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        rep = {k: v for k, v in rep.items() if k != "path"}
        return {"report": rep, "backup": data}

    def import_backup(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """全库导入：``{"backup": {...}, "confirm": true}`` → 导入报告（含 ``rejected_rows`` / ``quarantined``）。

        不接受设计者密钥：共享层与治理表按 :func:`lingshu_ng.exchange.import_all` 的规则隔离。"""
        b = _check_fields(body, ("backup", "confirm"), ("backup", "confirm"))
        if b["confirm"] is not True:
            raise BadRequest("导入会覆盖同 id 的节点，须显式给 confirm: true")
        if not isinstance(b["backup"], dict):
            raise BadRequest("backup 必须是 JSON 对象（export 导出的整份备份）")
        d = tempfile.mkdtemp(prefix="lingshu-ng-import-")
        try:
            path = os.path.join(d, "backup.json")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(b["backup"], f, ensure_ascii=False, allow_nan=False)
            with self.lock:
                rep = self.engine.import_all(path)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        return json.loads(json.dumps(rep, ensure_ascii=False, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))

    def close(self) -> None:
        """关闭引擎（幂等）。"""
        with self.lock:
            self.engine.close()


#: 操作名 → 方法名（HTTP 路径与 MCP 工具名都由此派生）
OPERATIONS = {"perceive": "perceive", "recall": "recall", "status": "status", "capabilities": "capabilities"}
