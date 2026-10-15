# -*- coding: utf-8 -*-
"""sec-r1：HTTP 集成面安全回归（DNS 重绑定 / 跨站写入 / 慢速连接 / 突发并发 / 深嵌套 JSON / Transfer-Encoding）。"""
import http.client
import json
import socket
import threading
import time

import pytest

from lingshu_ng.integrations import http as lhttp


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    monkeypatch.delenv("LINGSHU_NG_TOKEN", raising=False)
    made = []

    def make(token=None):
        s = lhttp.make_server(str(tmp_path / f"s{len(made)}.db"), "127.0.0.1", 0, token)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        made.append(s)
        return s.server_address[1]
    yield make
    for s in made:
        s.shutdown()
        s.server_close()
        s.service.close()


def _req(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    d = r.read()
    c.close()
    return r.status, d


def _drain(s):
    out = b""
    while True:
        b = s.recv(4096)
        if not b:
            return out
        out += b


def test_foreign_host_rejected_on_loopback(srv):
    """DNS 重绑定：只绑回环的服务只认回环 Host。"""
    port = srv()
    assert _req(port, "GET", "/v1/status", headers={"Host": "attacker.example:8765"})[0] == 403
    assert _req(port, "POST", "/v1/recall", json.dumps({"query": "x"}), {"Host": "attacker.example"})[0] == 403
    for h in (f"127.0.0.1:{port}", f"localhost:{port}", "localhost", f"[::1]:{port}"):
        assert _req(port, "GET", "/v1/status", headers={"Host": h})[0] == 200, h


def test_cross_origin_write_rejected_without_token(srv):
    """跨站「简单请求」（text/plain、带外站 Origin）不得写入。"""
    port = srv()
    body = json.dumps({"content": "csrf 写入"})
    assert _req(port, "POST", "/v1/perceive", body, {"Content-Type": "text/plain", "Origin": "http://evil.example"})[0] == 403
    st, d = _req(port, "POST", "/v1/recall", json.dumps({"query": "csrf 写入"}))
    assert st == 200 and json.loads(d)["hits"] == []
    assert _req(port, "POST", "/v1/perceive", body, {"Origin": "null"})[0] == 403
    assert _req(port, "POST", "/v1/perceive", body, {"Origin": f"http://127.0.0.1:{port}"})[0] == 200
    assert _req(port, "POST", "/v1/perceive", body, {"Origin": "http://localhost:3000"})[0] == 200


def test_slow_client_is_dropped(srv, monkeypatch):
    """声明了 Content-Length 却不发正文的连接，超时后被服务端关闭（不无限占线程）。"""
    assert lhttp._Handler.timeout is not None and lhttp._Handler.timeout <= 60
    monkeypatch.setattr(lhttp._Handler, "timeout", 1.0)
    port = srv()
    s = socket.create_connection(("127.0.0.1", port))
    s.sendall(b"POST /v1/recall HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 100\r\n\r\n")
    s.settimeout(10)
    t = time.time()
    _drain(s)
    s.close()
    assert time.time() - t < 9


def test_burst_connections_not_reset(srv):
    port = srv()
    errs, ok = [], []
    bar = threading.Barrier(64)

    def w(i):
        bar.wait()
        try:
            ok.append(_req(port, "POST", "/v1/perceive", json.dumps({"content": f"并发 {i}"}))[0])
        except OSError as e:
            errs.append(type(e).__name__)
    ts = [threading.Thread(target=w, args=(i,)) for i in range(64)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs and ok.count(200) == 64


def test_deep_nested_json_is_400(srv):
    port = srv()
    assert _req(port, "POST", "/v1/recall", b"[" * 200000 + b"]" * 200000)[0] == 400
    assert _req(port, "GET", "/v1/status")[0] == 200


def test_transfer_encoding_rejected(srv):
    port = srv()
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(b"POST /v1/recall HTTP/1.1\r\nHost: 127.0.0.1\r\nTransfer-Encoding: chunked\r\n\r\n"
              b"12\r\n{\"query\": \"abc\"}\r\n0\r\n\r\n")
    out = _drain(s)
    s.close()
    assert out.startswith(b"HTTP/1.1 501") and out.count(b"HTTP/1.1 ") == 1
