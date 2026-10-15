# -*- coding: utf-8 -*-
"""MCP 记忆服务器：工具名、入参、返回形状与官方 ``@modelcontextprotocol/server-memory``
（modelcontextprotocol/servers ``src/memory/index.ts``，2026-10 main）对齐，后端换成 lingshu_ng（纯标准库）。

客户端配置里把 ``npx -y @modelcontextprotocol/server-memory`` 换成 ``lingshu-ng-mcp-memory --db /path/mem.sqlite``
（或 ``python -m lingshu_ng_adapters.mcp_memory --db ...``）即可；已有的官方 ``memory.jsonl`` 可用 ``--import-jsonl`` 一次性导入。

工具（官方 9 个，同名同参）：``create_entities``、``create_relations``、``add_observations``、``delete_entities``、
``delete_observations``、``delete_relations``、``read_graph``、``search_nodes``、``open_nodes``；另带 ng 原有的
``lingshu_perceive`` / ``lingshu_recall`` / ``lingshu_status`` / ``lingshu_capabilities``（同一引擎）。
资源：``memory://knowledge-graph``（``resources/list`` / ``resources/read``；``resources/subscribe`` 接受但**不推送**
``notifications/resources/updated``——stdio 传输层只回应答）。

语义（逐条照官方实现）：重名实体跳过（结果带 ``skipped``）；关系端点不存在 ⇒ 工具错误 ``Entity with name X not found``；
重复关系跳过；``add_observations`` 实体不存在 ⇒ 工具错误，已有的同文观察不重复加；删除类工具对不存在的对象不报错、
在 message 里说明；``search_nodes`` = 名称 / 类型 / 观察的大小写不敏感子串匹配，``open_nodes`` 按名取；两者都附带
「至少一端在结果集内」的关系。

lingshu_ng 增量：每条观察是一条知识层记忆，``lingshu_recall`` 能按语义 / 词面召回它们；``recall_search=True``
（命令行 ``--recall-search``）时 ``search_nodes`` 在子串命中之外再并入 ``engine.recall`` 召回到的观察所属实体（排在子串命中之后）。
存储：实体 / 观察 / 关系各是一个带 ``kg:`` 标签的节点；关系另建一条引擎边（``correlational``，证据 ``kg:<relationType>``），
删实体时级联删除其观察、关系节点与边。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from ._backend import Backend, Record

__all__ = ["KnowledgeGraph", "KnowledgeGraphServer", "TOOLS", "OFFICIAL_TOOL_NAMES", "run_stdio", "main"]

_log = logging.getLogger("lingshu_ng_adapters.mcp_memory")
RESOURCE_URI = "memory://knowledge-graph"
SEARCH_QUERY_MAX_LENGTH = 2048
OFFICIAL_TOOL_NAMES = ("create_entities", "create_relations", "add_observations", "delete_entities",
                       "delete_observations", "delete_relations", "read_graph", "search_nodes", "open_nodes")


class ToolError(ValueError):
    """工具执行错误（MCP 结果 ``isError: true``）。"""


def _req_list(args: Dict[str, Any], key: str) -> List[Any]:
    v = args.get(key)
    if not isinstance(v, list):
        raise ToolError(f"参数 {key} 必须是数组")
    return v


def _req_str(d: Any, key: str) -> str:
    if not isinstance(d, dict) or not isinstance(d.get(key), str):
        raise ToolError(f"字段 {key} 必须是字符串")
    return d[key]


def _req_strs(d: Any, key: str) -> List[str]:
    v = d.get(key) if isinstance(d, dict) else None
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise ToolError(f"字段 {key} 必须是字符串数组")
    return v


class KnowledgeGraph:
    """官方 KnowledgeGraphManager 的 lingshu_ng 实现（同名方法、同返回形状；同步）。"""

    def __init__(self, engine=None, path: str = ":memory:", namespace: str = "kg", recall_search: bool = False):
        self._b = Backend(engine=engine, path=path, namespace=namespace)
        self.engine = self._b.engine
        self.recall_search = bool(recall_search)
        self._lock = threading.RLock()
        self._last_seq = 0

    # ------------------------------------------------------------ 内部
    def _seq(self) -> int:
        s = max(time.time_ns(), self._last_seq + 1)
        self._last_seq = s
        return s

    def _t(self, k: str, v: str) -> str:
        return self._b.tag(k, v)

    def _entity_rec(self, name: str) -> Optional[Record]:
        recs = self._b.by_tags([self._t("name", name), self._b.owner_tag, self._t("kind", "entity")])
        return recs[0] if recs else None

    def _obs_recs(self, name: str) -> List[Record]:
        recs = self._b.by_tags([self._t("of", name), self._b.owner_tag])
        recs.sort(key=lambda r: (r.meta.get("seq", 0), r.id))
        return recs

    def _rel_recs(self) -> List[Record]:
        recs = self._b.by_tags([self._t("kind", "relation"), self._b.owner_tag])
        recs.sort(key=lambda r: (r.meta.get("seq", 0), r.id))
        return recs

    def _entities(self) -> List[Record]:
        recs = self._b.by_tags([self._t("kind", "entity"), self._b.owner_tag])
        recs.sort(key=lambda r: (r.meta.get("seq", 0), r.id))
        return recs

    def _entity_json(self, r: Record) -> Dict[str, Any]:
        name = r.meta.get("name", "")
        return {"name": name, "entityType": r.meta.get("entityType", ""),
                "observations": [o.text for o in self._obs_recs(name)]}

    @staticmethod
    def _rel_json(r: Record) -> Dict[str, str]:
        return {"from": r.meta.get("from", ""), "to": r.meta.get("to", ""), "relationType": r.meta.get("relationType", "")}

    def _add_obs(self, name: str, text: str) -> None:
        self._b.write(text, [self._t("of", name)], {"kind": "observation", "entity": name, "seq": self._seq()},
                      extra_tags=[self._t("kind", "observation")])

    # ------------------------------------------------------------ 官方 9 个操作
    def create_entities(self, entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        for e in entities:
            _req_str(e, "name"), _req_str(e, "entityType"), _req_strs(e, "observations")
        created: List[Dict[str, Any]] = []
        skipped: List[str] = []
        with self._lock, self._b.db.tx():
            seen = set()
            for e in entities:
                name = e["name"]
                if name in seen or self._entity_rec(name) is not None:
                    skipped.append(name)
                    continue
                seen.add(name)
                self._b.write(f"{name}（{e['entityType']}）", [self._t("name", name)],
                              {"kind": "entity", "name": name, "entityType": e["entityType"], "seq": self._seq()},
                              extra_tags=[self._t("kind", "entity")])
                for o in e["observations"]:
                    self._add_obs(name, o)
                created.append({"name": name, "entityType": e["entityType"], "observations": list(e["observations"])})
        return created, skipped

    def create_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        for r in relations:
            _req_str(r, "from"), _req_str(r, "to"), _req_str(r, "relationType")
        from lingshu_ng.types import EdgeType
        with self._lock, self._b.db.tx():
            ents = {}
            for r in relations:
                for end in (r["from"], r["to"]):
                    if end not in ents:
                        ents[end] = self._entity_rec(end)
                    if ents[end] is None:
                        raise ToolError(f"Entity with name {end} not found")
            have = {(x["from"], x["to"], x["relationType"]) for x in map(self._rel_json, self._rel_recs())}
            out: List[Dict[str, str]] = []
            for r in relations:
                key = (r["from"], r["to"], r["relationType"])
                if key in have:
                    continue
                have.add(key)
                edge = self.engine.link(ents[r["from"]].id, ents[r["to"]].id, EdgeType.CORRELATIONAL,
                                        evidence=f"kg:{r['relationType']}")
                self._b.write(f"{r['from']} {r['relationType']} {r['to']}",
                              [self._t("from", r["from"]), self._t("to", r["to"])],
                              {"kind": "relation", "from": r["from"], "to": r["to"],
                               "relationType": r["relationType"], "edge_id": edge.id, "seq": self._seq()},
                              extra_tags=[self._t("kind", "relation")])
                out.append({"from": r["from"], "to": r["to"], "relationType": r["relationType"]})
        return out

    def add_observations(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for o in observations:
            _req_str(o, "entityName"), _req_strs(o, "contents")
        with self._lock, self._b.db.tx():
            results = []
            for o in observations:
                name = o["entityName"]
                if self._entity_rec(name) is None:
                    raise ToolError(f"Entity with name {name} not found")
                existing = [x.text for x in self._obs_recs(name)]
                new = [c for c in o["contents"] if c not in existing]
                for c in new:
                    self._add_obs(name, c)
                    existing.append(c)
                results.append({"entityName": name, "addedObservations": new})
        return results

    def delete_entities(self, entity_names: List[str]) -> Tuple[List[str], List[str]]:
        if not all(isinstance(x, str) for x in entity_names):
            raise ToolError("entityNames 必须是字符串数组")
        deleted, not_found = [], []
        with self._lock, self._b.db.tx():
            for name in entity_names:
                e = self._entity_rec(name)
                if e is None:
                    not_found.append(name)
                    continue
                deleted.append(name)
                ids = [r.id for r in self._obs_recs(name)]
                ids += [r.id for r in self._rel_recs() if name in (r.meta.get("from"), r.meta.get("to"))]
                self._b.delete_many(ids + [e.id])        # 节点删除级联删除其边（核心 N5）
        return deleted, not_found

    def delete_observations(self, deletions: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        for d in deletions:
            _req_str(d, "entityName"), _req_strs(d, "observations")
        count, missing = 0, []
        with self._lock, self._b.db.tx():
            for d in deletions:
                name = d["entityName"]
                if self._entity_rec(name) is None:
                    missing.append(name)
                    continue
                drop = set(d["observations"])
                count += self._b.delete_many(r.id for r in self._obs_recs(name) if r.text in drop)
        return count, missing

    def delete_relations(self, relations: List[Dict[str, Any]]) -> int:
        for r in relations:
            _req_str(r, "from"), _req_str(r, "to"), _req_str(r, "relationType")
        want = {(r["from"], r["to"], r["relationType"]) for r in relations}
        n = 0
        with self._lock, self._b.db.tx():
            for rec in self._rel_recs():
                j = self._rel_json(rec)
                if (j["from"], j["to"], j["relationType"]) in want:
                    eid = rec.meta.get("edge_id")
                    if eid:
                        self.engine.store.edges.delete(eid)
                    n += self._b.delete_many([rec.id])
        return n

    def read_graph(self) -> Dict[str, Any]:
        with self._lock:
            return {"entities": [self._entity_json(e) for e in self._entities()],
                    "relations": [self._rel_json(r) for r in self._rel_recs()]}

    def _subgraph(self, names: List[str]) -> Dict[str, Any]:
        ents = [e for e in self._entities() if e.meta.get("name") in names]
        order = {n: i for i, n in enumerate(names)}
        ents.sort(key=lambda e: order.get(e.meta.get("name"), 0))
        sel = {e.meta.get("name") for e in ents}
        rels = [self._rel_json(r) for r in self._rel_recs() if r.meta.get("from") in sel or r.meta.get("to") in sel]
        return {"entities": [self._entity_json(e) for e in ents], "relations": rels}

    def search_nodes(self, query: str) -> Dict[str, Any]:
        if not isinstance(query, str):
            raise ToolError("query 必须是字符串")
        if len(query) > SEARCH_QUERY_MAX_LENGTH:
            raise ToolError(f"query 超过 {SEARCH_QUERY_MAX_LENGTH} 字符")
        q = query.lower()
        with self._lock:
            names: List[str] = []
            for e in self._entities():
                j = self._entity_json(e)
                if q in j["name"].lower() or q in j["entityType"].lower() or any(q in o.lower() for o in j["observations"]):
                    names.append(j["name"])
            if self.recall_search and query.strip():
                own = self._b.owner_tag
                for r in self._b.search(query, 20, lambda r: own in r.tags):
                    n = r.meta.get("entity") or r.meta.get("name")
                    if r.meta.get("kind") in ("observation", "entity") and n and n not in names:
                        names.append(n)
            return self._subgraph(names)

    def open_nodes(self, names: List[str]) -> Dict[str, Any]:
        if not all(isinstance(x, str) for x in names):
            raise ToolError("names 必须是字符串数组")
        with self._lock:
            return self._subgraph(list(names))

    # ------------------------------------------------------------ 迁移
    def import_jsonl(self, path: str) -> Dict[str, int]:
        """导入官方 server-memory 的 ``memory.jsonl``（每行 ``{"type": "entity"|"relation", ...}``）；坏行跳过并计数。"""
        ents, rels, bad = [], [], 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                if isinstance(item, dict) and item.get("type") == "entity":
                    ents.append({k: item.get(k) for k in ("name", "entityType", "observations")})
                elif isinstance(item, dict) and item.get("type") == "relation":
                    rels.append({k: item.get(k) for k in ("from", "to", "relationType")})
                else:
                    bad += 1
        created, skipped = self.create_entities(ents)
        rcreated = self.create_relations(rels)
        return {"entities": len(created), "skipped_entities": len(skipped), "relations": len(rcreated), "bad_lines": bad}

    def close(self) -> None:
        self._b.close()


# --------------------------------------------------------------------------- MCP 协议层
_S = {"type": "string"}
_ENTITY = {"type": "object", "required": ["name", "entityType", "observations"], "additionalProperties": False,
           "properties": {"name": {"type": "string", "description": "The name of the entity"},
                          "entityType": {"type": "string", "description": "The type of the entity"},
                          "observations": {"type": "array", "items": _S,
                                           "description": "An array of observation contents associated with the entity"}}}
_RELATION = {"type": "object", "required": ["from", "to", "relationType"], "additionalProperties": False,
             "properties": {"from": {"type": "string", "description": "The name of the entity where the relation starts"},
                            "to": {"type": "string", "description": "The name of the entity where the relation ends"},
                            "relationType": {"type": "string", "description": "The type of the relation"}}}
_GRAPH_OUT = {"type": "object", "properties": {"entities": {"type": "array", "items": _ENTITY},
                                               "relations": {"type": "array", "items": _RELATION}},
              "required": ["entities", "relations"]}
_MSG_OUT = {"type": "object", "properties": {"success": {"type": "boolean"}, "message": _S},
            "required": ["success", "message"]}


def _obj(props: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {"type": "object", "properties": props, "required": required}


def _ann(ro: bool, destructive: bool, idem: bool) -> Dict[str, bool]:
    return {"readOnlyHint": ro, "destructiveHint": destructive, "idempotentHint": idem, "openWorldHint": False}


#: 官方 9 个工具（名称 / 标题 / 入参 / 出参 / 注解与官方一致；描述沿用官方英文原文）
KG_TOOLS = [
    {"name": "create_entities", "title": "Create Entities",
     "description": "Create multiple new entities in the knowledge graph. An entity whose name already exists, or repeats "
                    "an earlier entity in the same call, is skipped and its observations are not added; the result lists "
                    "the skipped names in `skipped`. Use add_observations to add observations to an existing entity.",
     "inputSchema": _obj({"entities": {"type": "array", "items": _ENTITY}}, ["entities"]),
     "outputSchema": _obj({"entities": {"type": "array", "items": _ENTITY},
                           "skipped": {"type": "array", "items": _S}}, ["entities"]),
     "annotations": _ann(False, False, False)},
    {"name": "create_relations", "title": "Create Relations",
     "description": "Create multiple new relations between entities in the knowledge graph. Relations should be in active voice",
     "inputSchema": _obj({"relations": {"type": "array", "items": _RELATION}}, ["relations"]),
     "outputSchema": _obj({"relations": {"type": "array", "items": _RELATION}}, ["relations"]),
     "annotations": _ann(False, False, False)},
    {"name": "add_observations", "title": "Add Observations",
     "description": "Add new observations to existing entities in the knowledge graph",
     "inputSchema": _obj({"observations": {"type": "array", "items": _obj(
         {"entityName": {"type": "string", "description": "The name of the entity to add the observations to"},
          "contents": {"type": "array", "items": _S, "description": "An array of observation contents to add"}},
         ["entityName", "contents"])}}, ["observations"]),
     "outputSchema": _obj({"results": {"type": "array", "items": _obj(
         {"entityName": _S, "addedObservations": {"type": "array", "items": _S}},
         ["entityName", "addedObservations"])}}, ["results"]),
     "annotations": _ann(False, False, False)},
    {"name": "delete_entities", "title": "Delete Entities",
     "description": "Delete multiple entities and their associated relations from the knowledge graph",
     "inputSchema": _obj({"entityNames": {"type": "array", "items": _S,
                                          "description": "An array of entity names to delete"}}, ["entityNames"]),
     "outputSchema": _MSG_OUT, "annotations": _ann(False, True, True)},
    {"name": "delete_observations", "title": "Delete Observations",
     "description": "Delete specific observations from entities in the knowledge graph",
     "inputSchema": _obj({"deletions": {"type": "array", "items": _obj(
         {"entityName": {"type": "string", "description": "The name of the entity containing the observations"},
          "observations": {"type": "array", "items": _S, "description": "An array of observations to delete"}},
         ["entityName", "observations"])}}, ["deletions"]),
     "outputSchema": _MSG_OUT, "annotations": _ann(False, True, True)},
    {"name": "delete_relations", "title": "Delete Relations",
     "description": "Delete multiple relations from the knowledge graph",
     "inputSchema": _obj({"relations": {"type": "array", "items": _RELATION,
                                        "description": "An array of relations to delete"}}, ["relations"]),
     "outputSchema": _MSG_OUT, "annotations": _ann(False, True, True)},
    {"name": "read_graph", "title": "Read Graph", "description": "Read the entire knowledge graph",
     "inputSchema": {"type": "object", "properties": {}}, "outputSchema": _GRAPH_OUT, "annotations": _ann(True, False, True)},
    {"name": "search_nodes", "title": "Search Nodes", "description": "Search for nodes in the knowledge graph based on a query",
     "inputSchema": _obj({"query": {"type": "string", "maxLength": SEARCH_QUERY_MAX_LENGTH,
                                    "description": "The search query to match against entity names, types, and observation content"}},
                         ["query"]),
     "outputSchema": _GRAPH_OUT, "annotations": _ann(True, False, True)},
    {"name": "open_nodes", "title": "Open Nodes", "description": "Open specific nodes in the knowledge graph by their names",
     "inputSchema": _obj({"names": {"type": "array", "items": _S, "description": "An array of entity names to retrieve"}},
                         ["names"]),
     "outputSchema": _GRAPH_OUT, "annotations": _ann(True, False, True)},
]
assert tuple(t["name"] for t in KG_TOOLS) == OFFICIAL_TOOL_NAMES


def _core_tools():
    from lingshu_ng.integrations import mcp as core_mcp
    return core_mcp


TOOLS = KG_TOOLS + list(_core_tools().TOOLS)


def _json_result(obj: Any, structured: Dict[str, Any], extra_text: Optional[str] = None) -> Dict[str, Any]:
    content = [{"type": "text", "text": json.dumps(obj, ensure_ascii=False, indent=2)}]
    if extra_text:
        content.append({"type": "text", "text": extra_text})
    return {"content": content, "structuredContent": structured, "isError": False}


def _msg_result(message: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "structuredContent": {"success": True, "message": message},
            "isError": False}


class KnowledgeGraphServer(_core_tools().McpServer):
    """核心 :class:`lingshu_ng.integrations.mcp.McpServer` 的扩展：官方 9 个知识图谱工具 + 核心 4 个工具 + 图谱资源。"""

    SERVER_NAME = "lingshu-ng-memory"

    def __init__(self, graph: Optional[KnowledgeGraph] = None, path: str = ":memory:", recall_search: bool = False):
        from lingshu_ng.integrations.service import Service
        self.graph = graph or KnowledgeGraph(path=path, recall_search=recall_search)
        super().__init__(Service(path=path, engine=self.graph.engine))
        self.subscriptions: set = set()

    def _initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        out = super()._initialize(params)
        out["capabilities"]["resources"] = {"subscribe": True, "listChanged": False}
        out["serverInfo"] = {"name": self.SERVER_NAME, "version": self.version}
        return out

    def _kg_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        g = self.graph
        if name == "create_entities":
            created, skipped = g.create_entities(_req_list(args, "entities"))
            notice = None
            if skipped:
                one = len(skipped) == 1
                notice = (f"Skipped {len(skipped)} {'entity that already exists' if one else 'entities that already exist'}: "
                          f"{', '.join(skipped)}. {'Its' if one else 'Their'} observations were not added; "
                          "use add_observations for existing entities.")
            return _json_result(created, {"entities": created, **({"skipped": skipped} if skipped else {})}, notice)
        if name == "create_relations":
            out = g.create_relations(_req_list(args, "relations"))
            return _json_result(out, {"relations": out})
        if name == "add_observations":
            out = g.add_observations(_req_list(args, "observations"))
            return _json_result(out, {"results": out})
        if name == "delete_entities":
            names = _req_list(args, "entityNames")
            deleted, not_found = g.delete_entities(names)
            return _msg_result("Entities deleted successfully" if not not_found else
                               f"Deleted {len(deleted)} of {len(names)} entities. Not found: {', '.join(not_found)}")
        if name == "delete_observations":
            dels = _req_list(args, "deletions")
            count, missing = g.delete_observations(dels)
            requested = sum(len(d["observations"]) for d in dels)
            return _msg_result("Observations deleted successfully" if count == requested else
                               f"Deleted {count} of {requested} observations." +
                               (f" Entities not found: {', '.join(missing)}" if missing else ""))
        if name == "delete_relations":
            rels = _req_list(args, "relations")
            n = g.delete_relations(rels)
            return _msg_result("Relations deleted successfully" if n == len(rels) else
                               f"Deleted {n} of {len(rels)} relations. The rest matched nothing.")
        if name == "read_graph":
            gr = g.read_graph()
            return _json_result(gr, dict(gr))
        if name == "search_nodes":
            if not isinstance(args.get("query"), str):
                raise ToolError("参数 query 必须是字符串")
            gr = g.search_nodes(args["query"])
            return _json_result(gr, dict(gr))
        gr = g.open_nodes(_req_list(args, "names"))
        return _json_result(gr, dict(gr))

    def _call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name, args = params.get("name"), params.get("arguments") or {}
        if name in OFFICIAL_TOOL_NAMES:
            if not isinstance(args, dict):
                return {"content": [{"type": "text", "text": "arguments 必须是对象"}], "isError": True}
            try:
                with self.service.lock:
                    return self._kg_call(name, args)
            except (ToolError, TypeError, ValueError) as e:
                return {"content": [{"type": "text", "text": str(e)}], "isError": True}
        return super()._call(params)

    def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        rpc = _core_tools().RpcError
        if method == "tools/list":
            return {"tools": TOOLS}
        if method == "resources/list":
            return {"resources": [{"uri": RESOURCE_URI, "name": "knowledge-graph", "title": "Knowledge Graph",
                                   "description": "The full knowledge graph with all entities and relations",
                                   "mimeType": "application/json"}]}
        if method == "resources/templates/list":
            return {"resourceTemplates": []}
        if method == "resources/read":
            if params.get("uri") != RESOURCE_URI:
                raise rpc(-32602, f"未知资源 {params.get('uri')!r}")
            with self.service.lock:
                gr = self.graph.read_graph()
            return {"contents": [{"uri": RESOURCE_URI, "mimeType": "application/json",
                                  "text": json.dumps(gr, ensure_ascii=False, indent=2)}]}
        if method == "resources/subscribe":
            self.subscriptions.add(params.get("uri"))
            return {}
        if method == "resources/unsubscribe":
            self.subscriptions.discard(params.get("uri"))
            return {}
        return super().dispatch(method, params)


def run_stdio(db: str = ":memory:", stdin=None, stdout=None, recall_search: bool = False,
              server: Optional[KnowledgeGraphServer] = None) -> None:
    """读 stdin 到 EOF，每行一条 JSON-RPC 消息；应答逐行写 stdout（同核心 ``lingshu_ng.integrations.mcp.run_stdio``）。"""
    core = _core_tools()
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    srv = server or KnowledgeGraphServer(path=db, recall_search=recall_search)
    try:
        for line in stdin:
            if not line.strip():
                continue
            r = core._reply(line, srv)
            if r is not None:
                stdout.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                stdout.flush()
    finally:
        srv.service.close()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="lingshu-ng-mcp-memory",
                                 description="MCP 记忆服务器（官方 server-memory 工具名，lingshu_ng 后端）")
    ap.add_argument("--db", default=os.environ.get("LINGSHU_NG_MCP_DB", ":memory:"),
                    help="SQLite 库路径（缺省环境变量 LINGSHU_NG_MCP_DB，再缺省进程内库）")
    ap.add_argument("--recall-search", action="store_true", help="search_nodes 并入 engine.recall 召回结果")
    ap.add_argument("--import-jsonl", metavar="PATH", help="启动前导入官方 memory.jsonl（导入后继续提供服务）")
    a = ap.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    srv = KnowledgeGraphServer(path=a.db, recall_search=a.recall_search)
    if a.import_jsonl:
        print(json.dumps(srv.graph.import_jsonl(a.import_jsonl), ensure_ascii=False), file=sys.stderr)
    run_stdio(a.db, server=srv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
