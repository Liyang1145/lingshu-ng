# -*- coding: utf-8 -*-
"""E5-1 并发连接上限（满则 503）、E5-3 令牌文件免重启轮换。"""
import http.client
import os
import socket
import threading
import time

import pytest

from lingshu_ng.integrations import http as lhttp


@pytest.fixture
def mk(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    monkeypatch.delenv("LINGSHU_NG_TOKEN", raising=False)
    made = []

    def make(token=None, host="127.0.0.1"):
        s = lhttp.make_server(str(tmp_path / f"s{len(made)}.db"), host, 0, token)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        made.append(s)
        return s
    yield make
    for s in made:
        s.shutdown(); s.server_close(); s.service.close()


def _status(port, hdr=None, path="/v1/status"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path, headers=hdr or {})
    r = c.getresponse(); r.read(); c.close()
    return r.status, dict(r.getheaders())


def test_connection_cap_returns_503(mk, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_MAX_CONN", "2")
    s = mk()
    port = s.server_address[1]
    idle = [socket.create_connection(("127.0.0.1", port)) for _ in range(2)]   # 占满两个名额（慢客户端）
    time.sleep(0.3)
    st, hd = _status(port)
    assert st == 503 and hd.get("Retry-After") == "1"
    for c in idle:
        c.close()
    for _ in range(50):
        time.sleep(0.1)
        if _status(port)[0] == 200:
            break
    assert _status(port)[0] == 200                 # 名额释放后恢复
    assert s.rejected_busy >= 1 and s.max_conn == 2


def test_bad_max_conn_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_MAX_CONN", "lots")
    with pytest.raises(ValueError):
        lhttp.make_server(str(tmp_path / "x.db"), "127.0.0.1", 0)


def test_token_file_rotation_without_restart(mk, tmp_path, monkeypatch):
    f = tmp_path / "tokens"
    f.write_text("# 注释\nold-tok\n", encoding="utf-8")
    monkeypatch.setenv("LINGSHU_NG_TOKEN_FILE", str(f))
    s = mk(host="0.0.0.0")                          # 只有令牌文件也允许绑非回环
    port = s.server_address[1]
    B = lambda t: {"Authorization": f"Bearer {t}"}
    assert _status(port)[0] == 401
    assert _status(port, B("old-tok"))[0] == 200
    assert _status(port, B("new-tok"))[0] == 401
    time.sleep(0.02)
    f.write_text("old-tok\nnew-tok\n", encoding="utf-8")   # 过渡期：新旧并存
    os.utime(f, ns=(time.time_ns(), time.time_ns() + 10 ** 9))
    assert _status(port, B("new-tok"))[0] == 200 and _status(port, B("old-tok"))[0] == 200
    f.write_text("new-tok\n", encoding="utf-8")            # 吊销旧令牌
    os.utime(f, ns=(time.time_ns(), time.time_ns() + 2 * 10 ** 9))
    assert _status(port, B("old-tok"))[0] == 401 and _status(port, B("new-tok"))[0] == 200
    f.write_text("# 全部吊销\n", encoding="utf-8")         # 空集：失败关闭
    os.utime(f, ns=(time.time_ns(), time.time_ns() + 3 * 10 ** 9))
    assert _status(port, B("new-tok"))[0] == 401 and _status(port)[0] == 401


def test_token_file_missing_refuses_start(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_TOKEN_FILE", str(tmp_path / "nope"))
    with pytest.raises(PermissionError):
        lhttp.make_server(str(tmp_path / "x.db"), "127.0.0.1", 0)


def test_explicit_token_plus_file(mk, tmp_path, monkeypatch):
    f = tmp_path / "t"
    f.write_text("file-tok\n", encoding="utf-8")
    monkeypatch.setenv("LINGSHU_NG_TOKEN_FILE", str(f))
    s = mk(token="cli-tok")
    port = s.server_address[1]
    for t, want in (("cli-tok", 200), ("file-tok", 200), ("x", 401)):
        assert _status(port, {"Authorization": f"Bearer {t}"})[0] == want


def test_export_streams_valid_json_without_full_parse(mk, monkeypatch):
    import json
    from lingshu_ng.integrations import service as svc_mod
    s = mk()
    port = s.server_address[1]
    for i in range(200):
        s.service.perceive({"content": f"流式导出第{i}条 " + "字" * 300, "skip_dedup": True})
    monkeypatch.setattr(lhttp, "EXPORT_CHUNK", 4096)
    called = []
    monkeypatch.setattr(svc_mod.Service, "export_backup", lambda self, b=None: called.append(1) or {})   # HTTP 不再走整份解析
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    c.request("GET", "/v1/export")
    r = c.getresponse()
    raw = r.read()
    c.close()
    assert r.status == 200 and int(r.getheader("Content-Length")) == len(raw) > 60000
    d = json.loads(raw)
    assert d["report"]["exported_nodes"] == 200 and len(d["backup"]["nodes"]) == 200 and "path" not in d["report"]
    assert not called


def test_mcp_and_cli_writes_are_audited(tmp_path, monkeypatch, caplog):
    import json, logging
    from lingshu_ng.integrations.mcp import McpServer
    from lingshu_ng.integrations.service import Service
    from lingshu_ng.integrations.cli import main
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    caplog.set_level(logging.INFO, logger="lingshu_ng.audit")
    secret = "审计不应含此正文-K9"
    svc = Service(str(tmp_path / "m.db"))
    try:
        m = McpServer(svc)
        m.dispatch("tools/call", {"name": "lingshu_perceive", "arguments": {"content": secret}})
        m.dispatch("tools/call", {"name": "lingshu_perceive", "arguments": {"content": 5}})
        m.dispatch("tools/call", {"name": "lingshu_recall", "arguments": {"query": secret}})
    finally:
        svc.close()
    assert main(["perceive", "--db", str(tmp_path / "c.db"), secret + "cli"]) == 0
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "lingshu_ng.audit"]
    assert [(x["op"], x["remote"], x["status"]) for x in lines] == [
        ("perceive", "mcp", 200), ("perceive", "mcp", 400), ("perceive", "cli", 200)]
    assert all(secret not in r.getMessage() for r in caplog.records if r.name == "lingshu_ng.audit")
