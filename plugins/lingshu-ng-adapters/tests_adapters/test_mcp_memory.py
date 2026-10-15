# -*- coding: utf-8 -*-
"""MCP 记忆服务器：与官方 @modelcontextprotocol/server-memory（src/memory/index.ts，2026-10 main）的工具名 / 入参 /
返回形状 / 语义逐条对照的契约测试 + stdio 子进程端到端（纯标准库，任何环境都跑）。"""
import json
import os
import subprocess
import sys

import pytest

from conftest import REPO, SRC
from lingshu_ng_adapters.mcp_memory import (KG_TOOLS, OFFICIAL_TOOL_NAMES, RESOURCE_URI, KnowledgeGraph,
                                            KnowledgeGraphServer)

#: 官方 9 个工具的入参必填键（来自官方 zod inputSchema）
OFFICIAL_INPUT = {"create_entities": ["entities"], "create_relations": ["relations"], "add_observations": ["observations"],
                  "delete_entities": ["entityNames"], "delete_observations": ["deletions"],
                  "delete_relations": ["relations"], "read_graph": [], "search_nodes": ["query"], "open_nodes": ["names"]}
#: 官方 annotations（readOnly, destructive, idempotent）
OFFICIAL_ANN = {"create_entities": (False, False, False), "create_relations": (False, False, False),
                "add_observations": (False, False, False), "delete_entities": (False, True, True),
                "delete_observations": (False, True, True), "delete_relations": (False, True, True),
                "read_graph": (True, False, True), "search_nodes": (True, False, True), "open_nodes": (True, False, True)}


@pytest.fixture
def srv(engine):
    return KnowledgeGraphServer(KnowledgeGraph(engine=engine))


def call(srv, name, **args):
    r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    return r["result"]


def test_tool_list_matches_official(srv):
    tools = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    names = [t["name"] for t in tools]
    assert tuple(names[:9]) == OFFICIAL_TOOL_NAMES
    assert names[9:] == ["lingshu_perceive", "lingshu_recall", "lingshu_status", "lingshu_capabilities"]
    for t in KG_TOOLS:
        assert sorted(t["inputSchema"].get("required", [])) == sorted(OFFICIAL_INPUT[t["name"]]), t["name"]
        a = t["annotations"]
        assert (a["readOnlyHint"], a["destructiveHint"], a["idempotentHint"]) == OFFICIAL_ANN[t["name"]]
        assert a["openWorldHint"] is False and "outputSchema" in t and t["title"]


def test_initialize_advertises_resources(srv):
    r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    caps = r["result"]["capabilities"]
    assert caps["tools"] and caps["resources"]["subscribe"] is True
    assert r["result"]["protocolVersion"] == "2025-06-18"


def test_create_entities_skips_existing_and_batch_repeats(srv):
    r = call(srv, "create_entities", entities=[
        {"name": "John_Smith", "entityType": "person", "observations": ["Speaks fluent Spanish"]},
        {"name": "Anthropic", "entityType": "organization", "observations": []},
        {"name": "John_Smith", "entityType": "person", "observations": ["dup"]}])
    assert r["isError"] is False
    assert r["structuredContent"]["skipped"] == ["John_Smith"]
    assert [e["name"] for e in r["structuredContent"]["entities"]] == ["John_Smith", "Anthropic"]
    assert len(r["content"]) == 2 and "Skipped 1 entity that already exists: John_Smith" in r["content"][1]["text"]
    assert json.loads(r["content"][0]["text"]) == r["structuredContent"]["entities"]
    r2 = call(srv, "create_entities", entities=[{"name": "Anthropic", "entityType": "x", "observations": ["y"]}])
    assert r2["structuredContent"] == {"entities": [], "skipped": ["Anthropic"]}
    g = call(srv, "read_graph")["structuredContent"]
    assert g["entities"][1] == {"name": "Anthropic", "entityType": "organization", "observations": []}


def test_relations_semantics(srv):
    call(srv, "create_entities", entities=[{"name": n, "entityType": "t", "observations": []} for n in ("A", "B", "C")])
    r = call(srv, "create_relations", relations=[{"from": "A", "to": "B", "relationType": "knows"},
                                                 {"from": "A", "to": "B", "relationType": "knows"}])
    assert r["structuredContent"] == {"relations": [{"from": "A", "to": "B", "relationType": "knows"}]}
    assert call(srv, "create_relations", relations=[{"from": "A", "to": "B", "relationType": "knows"}])[
        "structuredContent"] == {"relations": []}
    bad = call(srv, "create_relations", relations=[{"from": "A", "to": "Z", "relationType": "x"}])
    assert bad["isError"] is True and bad["content"][0]["text"] == "Entity with name Z not found"
    call(srv, "create_relations", relations=[{"from": "B", "to": "C", "relationType": "likes"}])
    d = call(srv, "delete_relations", relations=[{"from": "A", "to": "B", "relationType": "knows"},
                                                 {"from": "X", "to": "Y", "relationType": "z"}])
    assert d["structuredContent"] == {"success": True,
                                      "message": "Deleted 1 of 2 relations. The rest matched nothing."}
    assert call(srv, "read_graph")["structuredContent"]["relations"] == [{"from": "B", "to": "C", "relationType": "likes"}]
    ok = call(srv, "delete_relations", relations=[{"from": "B", "to": "C", "relationType": "likes"}])
    assert ok["structuredContent"]["message"] == "Relations deleted successfully"


def test_observations_semantics(srv):
    call(srv, "create_entities", entities=[{"name": "E", "entityType": "t", "observations": ["o1"]}])
    r = call(srv, "add_observations", observations=[{"entityName": "E", "contents": ["o1", "o2", "o3"]}])
    assert r["structuredContent"] == {"results": [{"entityName": "E", "addedObservations": ["o2", "o3"]}]}
    miss = call(srv, "add_observations", observations=[{"entityName": "Nope", "contents": ["x"]}])
    assert miss["isError"] is True and miss["content"][0]["text"] == "Entity with name Nope not found"
    d = call(srv, "delete_observations", deletions=[{"entityName": "E", "observations": ["o2", "zz"]},
                                                    {"entityName": "Ghost", "observations": ["q"]}])
    assert d["structuredContent"]["message"] == "Deleted 1 of 3 observations. Entities not found: Ghost"
    assert call(srv, "open_nodes", names=["E"])["structuredContent"]["entities"][0]["observations"] == ["o1", "o3"]
    ok = call(srv, "delete_observations", deletions=[{"entityName": "E", "observations": ["o3"]}])
    assert ok["structuredContent"]["message"] == "Observations deleted successfully"


def test_delete_entities_cascades(srv, engine):
    call(srv, "create_entities", entities=[{"name": "A", "entityType": "t", "observations": ["a-obs"]},
                                           {"name": "B", "entityType": "t", "observations": []}])
    call(srv, "create_relations", relations=[{"from": "A", "to": "B", "relationType": "r"}])
    edges_before = engine.store.edges.count()
    d = call(srv, "delete_entities", entityNames=["A", "Ghost"])
    assert d["structuredContent"] == {"success": True, "message": "Deleted 1 of 2 entities. Not found: Ghost"}
    g = call(srv, "read_graph")["structuredContent"]
    assert g == {"entities": [{"name": "B", "entityType": "t", "observations": []}], "relations": []}
    assert engine.store.edges.count() == edges_before - 1             # 引擎边随实体级联删除
    assert not engine.recall("a-obs", 5)["hits"]                      # 观察记忆一并删除
    assert call(srv, "delete_entities", entityNames=["B"])["structuredContent"]["message"] == "Entities deleted successfully"


def test_search_and_open_nodes_relations_with_one_endpoint(srv):
    call(srv, "create_entities", entities=[
        {"name": "Alice", "entityType": "person", "observations": ["Loves Jazz"]},
        {"name": "Bob", "entityType": "person", "observations": ["plays chess"]},
        {"name": "Acme", "entityType": "Company", "observations": []}])
    call(srv, "create_relations", relations=[{"from": "Alice", "to": "Acme", "relationType": "works_at"},
                                             {"from": "Bob", "to": "Acme", "relationType": "works_at"}])
    s = call(srv, "search_nodes", query="jazz")["structuredContent"]          # 观察子串、大小写不敏感
    assert [e["name"] for e in s["entities"]] == ["Alice"]
    assert s["relations"] == [{"from": "Alice", "to": "Acme", "relationType": "works_at"}]   # 至少一端在结果集内
    assert [e["name"] for e in call(srv, "search_nodes", query="company")["structuredContent"]["entities"]] == ["Acme"]
    assert [e["name"] for e in call(srv, "search_nodes", query="BO")["structuredContent"]["entities"]] == ["Bob"]
    o = call(srv, "open_nodes", names=["Bob", "Nobody"])["structuredContent"]
    assert [e["name"] for e in o["entities"]] == ["Bob"] and o["relations"] == [
        {"from": "Bob", "to": "Acme", "relationType": "works_at"}]
    long_q = call(srv, "search_nodes", query="x" * 2049)
    assert long_q["isError"] is True


def test_recall_search_extension(engine):
    srv = KnowledgeGraphServer(KnowledgeGraph(engine=engine, recall_search=True))
    call(srv, "create_entities", entities=[{"name": "Alice", "entityType": "person",
                                            "observations": ["favourite genre is jazz music"]}])
    assert call(srv, "search_nodes", query="jazz genre favourite")["structuredContent"]["entities"][0]["name"] == "Alice"
    plain = KnowledgeGraphServer(KnowledgeGraph(engine=engine))
    assert call(plain, "search_nodes", query="jazz genre favourite")["structuredContent"]["entities"] == []


def test_core_tools_share_engine_and_resource(srv):
    call(srv, "create_entities", entities=[{"name": "Kim", "entityType": "person", "observations": ["allergic to peanuts"]}])
    rec = call(srv, "lingshu_recall", query="peanuts")["structuredContent"]
    assert rec["hits"] and rec["hits"][0]["content"] == "allergic to peanuts"
    lst = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})["result"]["resources"]
    assert lst[0]["uri"] == RESOURCE_URI and lst[0]["mimeType"] == "application/json"
    rd = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": RESOURCE_URI}})["result"]
    assert json.loads(rd["contents"][0]["text"])["entities"][0]["name"] == "Kim"
    assert srv.handle({"jsonrpc": "2.0", "id": 4, "method": "resources/subscribe", "params": {"uri": RESOURCE_URI}})["result"] == {}
    bad = srv.handle({"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "memory://x"}})
    assert bad["error"]["code"] == -32602
    assert srv.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                       "params": {"name": "no_such_tool", "arguments": {}}})["error"]["code"] == -32602
    assert call(srv, "create_entities", entities="oops")["isError"] is True


def test_import_official_jsonl(tmp_path, engine):
    p = tmp_path / "memory.jsonl"
    p.write_text("\n".join([
        json.dumps({"type": "entity", "name": "A", "entityType": "t", "observations": ["x"]}),
        json.dumps({"type": "entity", "name": "B", "entityType": "t", "observations": []}),
        json.dumps({"type": "relation", "from": "A", "to": "B", "relationType": "r"}),
        "not json", json.dumps({"type": "weird"})]) + "\n", encoding="utf-8")
    g = KnowledgeGraph(engine=engine)
    assert g.import_jsonl(str(p)) == {"entities": 2, "skipped_entities": 0, "relations": 1, "bad_lines": 2}
    assert g.read_graph()["relations"] == [{"from": "A", "to": "B", "relationType": "r"}]


def test_stdio_subprocess_roundtrip(tmp_path):
    db = str(tmp_path / "mcp.sqlite")
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "create_entities", "arguments": {
                "entities": [{"name": "Z", "entityType": "t", "observations": ["persisted obs"]}]}}}]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([REPO, SRC, os.environ.get("PYTHONPATH", "")]))
    cmd = [sys.executable, "-m", "lingshu_ng_adapters.mcp_memory", "--db", db]
    out = subprocess.run(cmd, input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True,
                         env=env, timeout=120)
    lines = [json.loads(x) for x in out.stdout.splitlines()]
    assert [x["id"] for x in lines] == [1, 2] and lines[1]["result"]["isError"] is False
    out2 = subprocess.run(cmd, input=json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                                 "params": {"name": "read_graph", "arguments": {}}}) + "\n",
                          capture_output=True, text=True, env=env, timeout=120)
    g = json.loads(out2.stdout)["result"]["structuredContent"]
    assert g["entities"] == [{"name": "Z", "entityType": "t", "observations": ["persisted obs"]}]   # 跨进程持久
