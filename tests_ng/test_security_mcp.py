# -*- coding: utf-8 -*-
"""sec-r1：MCP stdio 安全回归（深嵌套不致进程退出 / 超长行有上限 / 空批量 / 非字符串工具名）。"""
import io
import json

from lingshu_ng.integrations import mcp
from lingshu_ng.integrations.service import Service

PING = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"})


def _run(text, monkeypatch=None, cap=None):
    if cap is not None:
        monkeypatch.setattr(mcp, "MAX_LINE", cap)
    out = io.StringIO()
    mcp.run_stdio(":memory:", stdin=io.StringIO(text), stdout=out, service=Service(":memory:"))
    return [json.loads(x) for x in out.getvalue().splitlines() if x.strip()]


def test_deep_nested_line_does_not_kill_server():
    r = _run("[" * 100000 + "]" * 100000 + "\n" + PING + "\n")
    assert r[0]["error"]["code"] == -32700
    assert r[-1] == {"jsonrpc": "2.0", "id": 99, "result": {}}


def test_oversized_line_rejected_and_stream_continues(monkeypatch):
    assert mcp.MAX_LINE >= 1 << 20
    big = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "pad": "x" * 5000})
    r = _run(big + "\n" + PING + "\n", monkeypatch, cap=1000)
    assert r[0]["error"]["code"] == -32600 and r[0]["id"] is None
    assert r[-1]["id"] == 99 and len(r) == 2


def test_empty_batch_is_invalid_request():
    r = _run("[]\n" + PING + "\n")
    assert r[0]["error"]["code"] == -32600 and r[-1]["id"] == 99


def test_unhashable_tool_name_is_invalid_params():
    r = _run(json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": ["a"]}}) + "\n")
    assert r[0]["error"]["code"] == -32602
