# -*- coding: utf-8 -*-
"""E6-2：结构化日志（LINGSHU_NG_LOG_FORMAT=json）与 /metrics（Prometheus 文本格式，需鉴权）。"""
import http.client
import io
import json
import logging
import re
import threading

import pytest

from lingshu_ng.integrations import _logfmt
from lingshu_ng.integrations import http as lhttp


def test_json_formatter_fields_and_exception():
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(_logfmt.JsonFormatter())
    lg = logging.getLogger("lingshu_ng.test_json_fmt")
    lg.handlers[:] = [h]; lg.propagate = False; lg.setLevel(logging.INFO)
    lg.info("你好 %s", "世界")
    try:
        raise ValueError("boom")
    except ValueError:
        lg.exception("出错")
    a, b = [json.loads(x) for x in buf.getvalue().splitlines()]
    assert a["msg"] == "你好 世界" and a["level"] == "INFO" and a["logger"] == "lingshu_ng.test_json_fmt"
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$", a["ts"])
    assert b["level"] == "ERROR" and "ValueError: boom" in b["exc"]


def test_configure_logging_env(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setenv("LINGSHU_NG_LOG_FORMAT", "json")
    monkeypatch.setenv("LINGSHU_NG_LOG", "INFO")
    root = logging.getLogger()
    saved = root.handlers[:], root.level
    try:
        _logfmt.configure_logging(buf, force=True)
        logging.getLogger("lingshu_ng.x").info("hi")
        assert json.loads(buf.getvalue().splitlines()[-1])["msg"] == "hi"
        monkeypatch.setenv("LINGSHU_NG_LOG_FORMAT", "text")
        buf2 = io.StringIO()
        _logfmt.configure_logging(buf2, force=True)
        logging.getLogger("lingshu_ng.x").warning("plain")
        assert "WARNING lingshu_ng.x: plain" in buf2.getvalue()
        monkeypatch.setenv("LINGSHU_NG_LOG_FORMAT", "yaml")
        with pytest.raises(ValueError):
            _logfmt.configure_logging(io.StringIO(), force=True)
    finally:
        root.handlers[:], _ = saved[0], root.setLevel(saved[1])


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    monkeypatch.delenv("LINGSHU_NG_TOKEN", raising=False)
    monkeypatch.delenv("LINGSHU_NG_TOKEN_FILE", raising=False)
    s = lhttp.make_server(str(tmp_path / "m.db"), "127.0.0.1", 0, "tok-m")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown(); s.server_close(); s.service.close()


def _req(port, method, path, hdr=None, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request(method, path, body=body, headers=hdr or {})
    r = c.getresponse(); data = r.read(); c.close()
    return r.status, dict(r.getheaders()), data


def test_metrics_requires_auth_and_is_prometheus_text(srv):
    port = srv.server_address[1]
    assert _req(port, "GET", "/metrics")[0] == 401
    auth = {"Authorization": "Bearer tok-m"}
    assert _req(port, "POST", "/v1/perceive", auth, json.dumps({"content": "指标测试"}))[0] == 200
    _req(port, "GET", "/v1/nosuch", auth)
    st, hd, data = _req(port, "GET", "/metrics", auth)
    assert st == 200 and hd["Content-Type"].startswith("text/plain; version=0.0.4")
    txt = data.decode("utf-8")
    import lingshu_ng
    assert f'lingshu_ng_info{{version="{lingshu_ng.__version__}"}} 1' in txt
    assert re.search(r"^lingshu_ng_uptime_seconds \d+(\.\d+)?$", txt, re.M)
    assert re.search(r'^lingshu_ng_http_responses_total\{code="401"\} [1-9]\d*$', txt, re.M)
    assert re.search(r'^lingshu_ng_http_responses_total\{code="404"\} 1$', txt, re.M)
    assert re.search(r'^lingshu_ng_http_responses_total\{code="200"\} [1-9]\d*$', txt, re.M)
    assert re.search(r"^lingshu_ng_http_requests_total [4-9]\d*$", txt, re.M)
    assert "lingshu_ng_http_rejected_busy_total 0" in txt
    assert f"lingshu_ng_http_max_connections {srv.max_conn}" in txt
    assert re.search(r"^lingshu_ng_memory_nodes \d+$", txt, re.M)
    assert re.search(r'^lingshu_ng_memory_nodes_by_layer\{layer="[a-z_]+"\} \d+$', txt, re.M)
    # 每个指标都有 HELP / TYPE，且无正文泄漏
    names = {l.split()[2] for l in txt.splitlines() if l.startswith("# TYPE")}
    for l in txt.splitlines():
        if l and not l.startswith("#"):
            base = re.split(r"[{ ]", l, 1)[0]
            assert re.sub(r"_(bucket|sum|count)$", "", base) in names or base in names
    assert "指标测试" not in txt
    assert _req(port, "POST", "/metrics", auth, "{}")[0] == 405


def test_latency_histogram_by_route(srv):
    port = srv.server_address[1]
    auth = {"Authorization": "Bearer tok-m"}
    for _ in range(3):
        _req(port, "POST", "/v1/perceive", auth, json.dumps({"content": "时延"}))
    _req(port, "GET", "/v1/whatever-1", auth)
    _req(port, "GET", "/v1/whatever-2", auth)
    txt = _req(port, "GET", "/metrics", auth)[2].decode()
    assert "# TYPE lingshu_ng_http_request_duration_seconds histogram" in txt
    assert re.search(r'_count\{route="/v1/perceive"\} 3$', txt, re.M)
    assert re.search(r'_bucket\{route="/v1/perceive",le="\+Inf"\} 3$', txt, re.M)
    assert re.search(r'_count\{route="other"\} 2$', txt, re.M)   # 未知路径归并，基数固定
    assert "whatever" not in txt
    cum = [int(m) for m in re.findall(r'_bucket\{route="/v1/perceive",le="[^"]+"\} (\d+)', txt)]
    assert cum == sorted(cum)
