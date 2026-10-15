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
