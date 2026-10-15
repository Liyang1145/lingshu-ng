# -*- coding: utf-8 -*-
"""ent-ui：本机 Web 控制台（lingshu_ng.integrations.console）——路由、安全、各 API 功能、审计日志。"""
import http.client
import json
import logging
import os
import re
import subprocess
import sys
import threading
import tomllib
from importlib import resources

import pytest

from lingshu_ng.integrations import console as lconsole
from lingshu_ng.integrations import http as lhttp
from lingshu_ng.integrations.service import BadRequest, Conflict, NotFound, Service

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = {"X-Lingshu-Console": "1"}
SECRET = "机密正文-Zq7×不应进审计"


def _asset(name):
    return resources.files("lingshu_ng.integrations").joinpath("console_static", name).read_text(encoding="utf-8")


@pytest.fixture
def srv(tmp_path, monkeypatch):
    """srv(token=None, console=True) → 端口；同时可经 srv.last 拿到服务对象。"""
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    monkeypatch.delenv("LINGSHU_NG_TOKEN", raising=False)
    made = []

    def make(token=None, console=True):
        db = str(tmp_path / f"c{len(made)}.db")
        s = lconsole.make_console_server(db, "127.0.0.1", 0, token) if console else \
            lhttp.make_server(db, "127.0.0.1", 0, token)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        made.append(s)
        make.last = s
        return s.server_address[1]
    yield make
    for s in made:
        s.shutdown()
        s.server_close()
        s.service.close()


def _req(port, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False).encode("utf-8")
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    d = r.read()
    hd = {k.lower(): v for k, v in r.getheaders()}
    c.close()
    return r.status, d, hd


def _json(port, method, path, body=None, headers=None):
    st, d, _ = _req(port, method, path, body, {**H, **(headers or {})})
    return st, json.loads(d.decode("utf-8"))


def _put(port, content, **kw):
    st, out = _json(port, "POST", "/v1/perceive", {"content": content, **kw})
    assert st == 200, out
    return out["node_id"]


# ------------------------------------------------------------------ 静态页面 / CSP / XSS
def test_console_page_served_with_csp(srv):
    port = srv()
    for path, ctype in (("/", "text/html"), ("/console", "text/html"), ("/console/app.js", "text/javascript"),
                        ("/console/app.css", "text/css")):
        st, d, hd = _req(port, "GET", path)
        assert st == 200, path
        assert hd["content-type"].startswith(ctype)
        csp = hd["content-security-policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "script-src 'self'" in csp
        assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
        assert hd["x-content-type-options"] == "nosniff" and hd["x-frame-options"] == "DENY"
        assert hd["cache-control"] == "no-store"
    st, d, _ = _req(port, "GET", "/")
    assert b'src="/console/app.js"' in d


def test_api_responses_have_restrictive_csp(srv):
    port = srv()
    st, d, hd = _req(port, "GET", "/v1/status")
    assert st == 200 and hd["content-type"].startswith("application/json")
    assert hd["content-security-policy"].startswith("default-src 'none'")
    assert hd["x-content-type-options"] == "nosniff"


def test_plain_serve_has_no_console_page(srv):
    port = srv(console=False)
    assert _req(port, "GET", "/")[0] == 404
    assert _req(port, "GET", "/console/app.js")[0] == 404


def test_html_has_no_inline_script_or_external_resource():
    html = _asset("index.html")
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, re.S):
        assert 'src="/console/' in m.group(1) and not m.group(2).strip(), "不许内联脚本"
    assert not re.search(r"\son[a-z]+\s*=", html), "不许内联事件处理器"
    assert not re.search(r"\sstyle\s*=", html), "不许内联样式（CSP style-src 'self'）"
    for name in ("index.html", "app.js", "app.css"):
        text = _asset(name)
        assert not re.search(r"(https?:)?//[a-z0-9.-]+\.[a-z]{2,}", text, re.I), f"{name} 引用了外部资源"
        assert "@import" not in text and "url(" not in text.replace("createObjectURL(", "").replace("revokeObjectURL(", "")


def test_js_never_builds_html_from_strings():
    """XSS：前端只用 textContent / createTextNode 放数据，不用任何把字符串当 HTML 解析的 API。"""
    js = _asset("app.js")
    for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function",
                "DOMParser", "createContextualFragment", "srcdoc", "javascript:"):
        assert bad not in js, bad
    assert js.count("textContent") >= 5 and "createTextNode" in js
    # 令牌只在 sessionStorage + Authorization 头，不进 cookie / URL / localStorage
    assert "document.cookie" not in js
    assert "sessionStorage.setItem(TOKEN_KEY" in js and "localStorage.setItem(TOKEN_KEY" not in js
    assert '"Authorization"' in js and "token=" not in js and "?token" not in js
    assert '"X-Lingshu-Console": "1"' in js
    assert 'credentials: "omit"' in js


def test_xss_payload_round_trips_as_json_data(srv):
    port = srv()
    payload = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
    nid = _put(port, payload, tags=["<b>t</b>"])
    st, d, hd = _req(port, "GET", f"/v1/nodes/{nid}")
    assert st == 200 and hd["content-type"].startswith("application/json")
    assert json.loads(d)["content"] == payload           # 原样作为数据返回，渲染由前端 textContent 负责
    st, page, _ = _req(port, "GET", "/")
    assert b"alert(" not in page and b"onerror" not in page    # 页面模板不含任何用户数据


# ------------------------------------------------------------------ Host / Origin / CSRF 头 / 令牌
def test_foreign_host_rejected(srv):
    port = srv()
    for path in ("/", "/console/app.js", "/v1/status", "/v1/nodes", "/v1/export", "/v1/health"):
        assert _req(port, "GET", path, headers={"Host": "attacker.example:8766"})[0] == 403, path
    assert _req(port, "POST", "/v1/perceive", b'{"content":"x"}', {**H, "Host": "evil.test"})[0] == 403
    assert _req(port, "GET", "/", headers={"Host": f"localhost:{port}"})[0] == 200


def test_cross_site_origin_rejected(srv):
    port = srv()
    evil = {"Origin": "http://evil.example"}
    assert _req(port, "GET", "/", headers=evil)[0] == 403
    assert _req(port, "GET", "/v1/export", headers=evil)[0] == 403
    assert _req(port, "POST", "/v1/perceive", b'{"content":"x"}', {**H, **evil})[0] == 403
    assert _req(port, "DELETE", "/v1/nodes/n1", headers={**H, **evil})[0] == 403
    assert _req(port, "POST", "/v1/import", b'{"backup":{},"confirm":true}', {**H, "Origin": "null"})[0] == 403
    assert _req(port, "GET", "/v1/status", headers={"Origin": f"http://127.0.0.1:{port}"})[0] == 200


def test_writes_without_custom_header_rejected(srv, caplog):
    port = srv()
    nid = _put(port, "保留节点")
    for method, path, body in (("POST", "/v1/perceive", {"content": "x"}), ("POST", "/v1/recall", {"query": "x"}),
                               ("DELETE", f"/v1/nodes/{nid}", None),
                               ("POST", "/v1/import", {"backup": {}, "confirm": True})):
        b = json.dumps(body).encode() if body is not None else None
        st, d, _ = _req(port, method, path, b, {"Content-Type": "text/plain"})
        assert st == 403, (method, path)
        assert "X-Lingshu-Console" in json.loads(d)["error"]["message"]
        st, d, _ = _req(port, method, path, b, {"X-Lingshu-Console": "0"})
        assert st == 403
    assert _json(port, "GET", f"/v1/nodes/{nid}")[0] == 200     # 没被删
    assert _json(port, "GET", "/v1/status")[1]["total"] == 1     # 没写入


def test_plain_serve_destructive_routes_need_header_but_perceive_unchanged(srv):
    port = srv(console=False)
    st, d, _ = _req(port, "POST", "/v1/perceive", b'{"content":"no header ok"}')
    assert st == 200                                              # 既有 HTTP API 行为不变
    nid = json.loads(d)["node_id"]
    assert _req(port, "DELETE", f"/v1/nodes/{nid}")[0] == 403
    assert _req(port, "POST", "/v1/import", b'{"backup":{},"confirm":true}')[0] == 403
    assert _req(port, "DELETE", f"/v1/nodes/{nid}", headers=H)[0] == 200


def test_token_required(srv):
    port = srv(token="s3cret-tok")
    assert _req(port, "GET", "/")[0] == 200                       # 登录页本身不含数据
    assert _req(port, "GET", "/console/app.js")[0] == 200
    assert _req(port, "GET", "/healthz")[0] == 200
    for path in ("/v1/status", "/v1/nodes", "/v1/nodes/x", "/v1/export", "/v1/health", "/v1/capabilities"):
        assert _req(port, "GET", path)[0] == 401, path
        assert _req(port, "GET", path, headers={"Authorization": "Bearer wrong"})[0] == 401, path
    assert _req(port, "POST", "/v1/perceive", b'{"content":"x"}', H)[0] == 401
    assert _req(port, "DELETE", "/v1/nodes/x", headers=H)[0] == 401
    assert _req(port, "GET", "/v1/status?token=s3cret-tok")[0] in (400, 401)   # 令牌不经 URL
    ok = {"Authorization": "Bearer s3cret-tok"}
    assert _json(port, "GET", "/v1/status", headers=ok)[0] == 200
    assert _json(port, "POST", "/v1/perceive", {"content": "有令牌"}, ok)[0] == 200
    st, d, hd = _req(port, "GET", "/v1/status", headers=ok)
    assert "set-cookie" not in hd


def test_non_loopback_without_token_refuses(tmp_path, monkeypatch):
    monkeypatch.delenv("LINGSHU_NG_TOKEN", raising=False)
    db = tmp_path / "never.db"
    with pytest.raises(PermissionError):
        lconsole.make_console_server(str(db), "0.0.0.0", 0)
    assert not db.exists()
    from lingshu_ng.integrations.cli import main
    assert main(["console", "--db", str(db), "--host", "0.0.0.0", "--port", "0"]) == 2
    assert lconsole.main(["--db", str(db), "--host", "192.168.1.5", "--port", "0"]) == 2


def test_transfer_encoding_and_body_limits_inherited(srv, monkeypatch):
    port = srv()
    st, _, _ = _req(port, "POST", "/v1/perceive", b"", {**H, "Transfer-Encoding": "chunked"})
    assert st == 501
    monkeypatch.setattr(lhttp, "MAX_IMPORT_BODY", 4096)
    big = json.dumps({"backup": {"nodes": [], "pad": "x" * 10000}, "confirm": True}).encode()
    assert _req(port, "POST", "/v1/import", big, H)[0] == 413
    assert _req(port, "POST", "/v1/perceive", b"{" + b" " * (lhttp.MAX_BODY + 10) + b"}", H)[0] == 413


def test_import_accepts_body_larger_than_normal_cap(srv):
    port = srv()
    nodes = [{"id": f"imp{i}", "content": "长" * 2000 + str(i), "layer": "knowledge", "importance": 0.5}
             for i in range(300)]
    body = json.dumps({"backup": {"meta": {"version": "ng-1"}, "nodes": nodes}, "confirm": True}).encode()
    assert len(body) > lhttp.MAX_BODY
    st, d, _ = _req(port, "POST", "/v1/import", body, H)
    assert st == 200, d[:300]
    assert json.loads(d)["imported"]["nodes"] == 300


def test_unknown_and_wrong_method(srv):
    port = srv()
    assert _req(port, "GET", "/v1/nope")[0] == 404
    assert _req(port, "POST", "/v1/nodes", b"{}", H)[0] == 405
    assert _req(port, "POST", "/v1/health", b"{}", H)[0] == 405
    assert _req(port, "DELETE", "/v1/status", headers=H)[0] == 405
    assert _req(port, "DELETE", "/v1/zzz", headers=H)[0] == 404
    assert _req(port, "GET", "/v1/import")[0] == 405
    assert _req(port, "GET", "/v1/export?x=1")[0] == 400


# ------------------------------------------------------------------ 各 API 功能
def test_overview_status_and_capabilities(srv):
    port = srv()
    _put(port, "概览一条")
    st, s = _json(port, "GET", "/v1/status")
    assert st == 200 and s["total"] == 1 and s["counts"]["knowledge"] == 1 and "schema_version" in s
    assert s["db"].endswith(".db")
    st, c = _json(port, "GET", "/v1/capabilities")
    assert st == 200 and "plugins" in c and "semantic_tier" in c


def test_recall_hits(srv):
    port = srv()
    _put(port, "量子纠缠实验在合肥完成", tags=["物理"])
    st, r = _json(port, "POST", "/v1/recall", {"query": "量子纠缠实验", "limit": 5})
    assert st == 200 and r["hits"], r
    h = r["hits"][0]
    assert {"id", "content", "score", "layer", "tags", "created_at"} <= set(h)
    assert h["tags"] == ["物理"]


def test_list_nodes_pagination_and_filters(srv):
    port = srv()
    ids = [_put(port, f"分页测试第{i}条内容不同{i * 7}", tags=["even" if i % 2 == 0 else "odd"], skip_dedup=True)
           for i in range(5)]
    st, r = _json(port, "GET", "/v1/nodes?limit=2")
    assert st == 200 and r["total"] == 5 and [n["id"] for n in r["nodes"]] == ids[::-1][:2]
    st, r = _json(port, "GET", "/v1/nodes?limit=2&offset=4")
    assert [n["id"] for n in r["nodes"]] == [ids[0]] and r["offset"] == 4
    st, r = _json(port, "GET", "/v1/nodes?tag=even")
    assert r["total"] == 3 and all("even" in n["tags"] for n in r["nodes"])
    st, r = _json(port, "GET", "/v1/nodes?layer=knowledge&tag=odd&limit=200")
    assert r["total"] == 2
    st, r = _json(port, "GET", "/v1/nodes?layer=context")
    assert r["total"] == 0 and r["nodes"] == []
    for bad in ("limit=0", "limit=201", "offset=-1", "layer=bogus", "limit=abc", "x=1", "limit=1&limit=2", "limit=1.5"):
        assert _json(port, "GET", f"/v1/nodes?{bad}")[0] == 400, bad


def test_list_truncates_long_content(srv):
    port = srv()
    nid = _put(port, "长" * 1000)
    n = _json(port, "GET", "/v1/nodes")[1]["nodes"][0]
    assert n["truncated"] is True and len(n["content"]) == 300
    assert len(_json(port, "GET", f"/v1/nodes/{nid}")[1]["content"]) == 1000


def test_node_detail_with_edges_and_entities(srv):
    port = srv()
    a = _put(port, "苹果公司发布新手机", tags=["科技"], entities=["苹果"], importance=0.8)
    b = _put(port, "新手机销量创纪录", skip_dedup=True)
    srv.last.service.engine.link(a, b)
    st, n = _json(port, "GET", f"/v1/nodes/{a}")
    assert st == 200
    assert n["content"] == "苹果公司发布新手机" and n["tags"] == ["科技"] and n["entities"] == ["苹果"]
    assert n["importance"] == pytest.approx(0.8) and n["layer"] == "knowledge" and n["deletable"] is True
    out = n["edges"]["outgoing"]
    assert n["edges"]["outgoing_total"] == 1 and out[0]["target_id"] == b and out[0]["relation"] == "causal"
    assert out[0]["peer"]["content"] == "新手机销量创纪录"
    st, nb = _json(port, "GET", f"/v1/nodes/{b}")
    assert nb["edges"]["incoming"][0]["source_id"] == a
    assert _json(port, "GET", "/v1/nodes/does-not-exist")[0] == 404
    assert _json(port, "GET", "/v1/nodes/" + "x" * 600)[0] == 400
    assert _json(port, "GET", "/v1/nodes/%E4%B8%AD%E6%96%87id")[0] == 404     # 百分号编码的 id 正确解码


def test_delete_node_removes_edges(srv):
    port = srv()
    a = _put(port, "要删除的节点甲")
    b = _put(port, "保留的节点乙", skip_dedup=True)
    srv.last.service.engine.link(a, b)
    st, r = _json(port, "DELETE", f"/v1/nodes/{a}")
    assert st == 200 and r == {"deleted": True, "id": a, "layer": "knowledge", "edges_removed": 1}
    assert _json(port, "GET", f"/v1/nodes/{a}")[0] == 404
    assert _json(port, "GET", f"/v1/nodes/{b}")[1]["edges"]["incoming_total"] == 0
    assert _json(port, "DELETE", f"/v1/nodes/{a}")[0] == 404
    hits = _json(port, "POST", "/v1/recall", {"query": "要删除的节点甲"})[1]["hits"]
    assert a not in [h["id"] for h in hits]


def test_delete_protected_node_conflict(srv):
    port = srv()
    a = _put(port, "受保护的节点")
    srv.last.service.engine.protect(a, "测试")
    st, r = _json(port, "DELETE", f"/v1/nodes/{a}")
    assert st == 409, r
    assert _json(port, "GET", f"/v1/nodes/{a}")[1]["protected"] is True


def test_delete_shared_layer_conflict(srv):
    port = srv()
    from lingshu_ng.types import MemoryLayer
    w = srv.last.service.engine.add_shared(MemoryLayer.ANCHOR, "锚点不可删", 0.9)
    st, r = _json(port, "DELETE", f"/v1/nodes/{w.node_id}")
    assert st == 409 and "anchor" in r["error"]["message"]
    assert _json(port, "GET", f"/v1/nodes/{w.node_id}")[1]["deletable"] is False


def test_export_import_round_trip(srv):
    port = srv()
    a = _put(port, "导出测试一", tags=["x"])
    b = _put(port, "导出测试二", skip_dedup=True)
    srv.last.service.engine.link(a, b)
    st, e = _json(port, "GET", "/v1/export")
    assert st == 200 and e["report"]["exported_nodes"] == 2 and "path" not in e["report"]
    backup = e["backup"]
    assert backup["meta"]["version"] == "ng-1" and len(backup["nodes"]) == 2
    port2 = srv()
    assert _json(port2, "POST", "/v1/import", {"backup": backup})[0] == 400              # 缺 confirm
    assert _json(port2, "POST", "/v1/import", {"backup": backup, "confirm": "yes"})[0] == 400
    assert _json(port2, "POST", "/v1/import", {"backup": [], "confirm": True})[0] == 400
    assert _json(port2, "POST", "/v1/import", {"backup": {"nodes": "abc"}, "confirm": True})[0] == 400
    st, rep = _json(port2, "POST", "/v1/import", {"backup": backup, "confirm": True})
    assert st == 200 and rep["imported"]["nodes"] == 2 and rep["imported"]["edges"] == 1 and rep["integrity_ok"]
    assert _json(port2, "GET", "/v1/status")[1]["total"] == 2
    assert _json(port2, "GET", f"/v1/nodes/{a}")[1]["edges"]["outgoing_total"] == 1
    st, rep2 = _json(port2, "POST", "/v1/import", {"backup": backup, "confirm": True})   # 再导一次：全部是覆盖
    assert st == 200 and rep2.get("overwritten", {}).get("nodes") == 2, rep2


def test_import_report_includes_rejected_rows(srv):
    port = srv()
    backup = {"meta": {"version": "ng-1"}, "nodes": [
        {"id": "ok1", "content": "正常行", "layer": "knowledge", "importance": 0.4},
        {"id": "bad1", "content": "坏行", "layer": "knowledge", "importance": "high"},
        {"id": "bad2", "content": 12345, "layer": "knowledge"}]}
    st, rep = _json(port, "POST", "/v1/import", {"backup": backup, "confirm": True})
    assert st == 200 and rep["imported"]["nodes"] == 1
    assert rep["rejected_rows"].get("nodes"), rep
    assert _json(port, "GET", "/v1/nodes/ok1")[0] == 200 and _json(port, "GET", "/v1/nodes/bad1")[0] == 404


def test_health_endpoint(srv):
    port = srv()
    before = _json(port, "GET", "/v1/health")[1]
    _req(port, "GET", "/healthz")
    after = _json(port, "GET", "/v1/health")[1]
    assert after["ok"] is True and after["console"] is True and after["auth"] == "loopback-only"
    assert after["requests_total"] >= before["requests_total"] + 2
    assert after["requests_recent"] <= after["requests_total"] and after["uptime_s"] >= 0
    from lingshu_ng import __version__
    assert after["version"] == __version__
    assert _req(port, "GET", "/healthz")[1] == b'{"ok": true}'                   # /healthz 形状不变


# ------------------------------------------------------------------ 审计
def test_audit_log_has_no_content(srv, caplog):
    port = srv()
    caplog.set_level(logging.INFO, logger="lingshu_ng.audit")
    nid = _put(port, SECRET, tags=["审计"])
    _json(port, "POST", "/v1/perceive", {"content": SECRET + "-2"}, {"X-Lingshu-Console": "0"})   # 403 也记
    backup = _json(port, "GET", "/v1/export")[1]["backup"]
    _json(port, "DELETE", f"/v1/nodes/{nid}")
    _json(port, "POST", "/v1/import", {"backup": backup, "confirm": True})
    _json(port, "POST", "/v1/recall", {"query": SECRET})                                       # 读操作不记
    recs = [r for r in caplog.records if r.name == "lingshu_ng.audit"]
    lines = [json.loads(r.getMessage()) for r in recs]
    ops = [(x["op"], x["status"]) for x in lines]
    assert ("perceive", 200) in ops and ("perceive", 403) in ops and ("delete_node", 200) in ops \
        and ("import_backup", 200) in ops
    assert not any(op == "recall" for op, _ in ops)
    for x in lines:
        assert {"ts", "op", "remote", "status"} <= set(x) and x["remote"] == "127.0.0.1"
        assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", x["ts"])
    assert [x["node_id"] for x in lines if x["op"] == "delete_node"] == [nid]
    assert [x["node_id"] for x in lines if x["op"] == "perceive" and x["status"] == 200] == [nid]
    imp = [x for x in lines if x["op"] == "import_backup"][0]
    assert imp["imported"]["nodes"] == 1 and "overwritten" in imp
    for r in recs:
        assert SECRET not in r.getMessage() and "审计" not in r.getMessage()


def test_audit_log_file(tmp_path):
    p = tmp_path / "audit.jsonl"
    lg = logging.getLogger("lingshu_ng.audit")
    before = list(lg.handlers)
    try:
        lconsole.enable_audit_log(str(p))
        lhttp.audit("perceive", "127.0.0.1", 200, node_id="n1")
        for h in lg.handlers:
            h.flush()
        rec = json.loads(p.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert rec["op"] == "perceive" and rec["node_id"] == "n1"
        assert (os.stat(p).st_mode & 0o777) == 0o600
    finally:
        for h in lg.handlers[:]:
            if h not in before:
                lg.removeHandler(h)
                h.close()


# ------------------------------------------------------------------ Service 层校验 / 入口 / 打包
def test_service_validation(monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    s = Service(":memory:")
    try:
        with pytest.raises(TypeError):          # 与 inputs.limit 同口径（HTTP 映射 400）
            s.list_nodes({"limit": True})
        with pytest.raises((BadRequest, TypeError)):
            s.list_nodes({"offset": "1"})
        with pytest.raises(BadRequest):
            s.list_nodes({"tag": ["a"]})
        with pytest.raises(BadRequest):
            s.get_node({"id": 5})
        with pytest.raises(BadRequest):
            s.get_node({"id": ""})
        with pytest.raises(ValueError):
            s.get_node({"id": "\ud800"})
        with pytest.raises(NotFound):
            s.delete_node({"id": "nope"})
        with pytest.raises(BadRequest):
            s.delete_node({"id": "a", "force": True})
        with pytest.raises(BadRequest):
            s.export_backup({"x": 1})
        assert issubclass(NotFound, BadRequest) and issubclass(Conflict, BadRequest)
    finally:
        s.close()


def test_entry_points(monkeypatch):
    from lingshu_ng.integrations.cli import _parser
    a = _parser().parse_args(["console", "--db", "/tmp/x.db", "--port", "9999", "--token", "t"])
    assert (a.cmd, a.db, a.host, a.port, a.token) == ("console", "/tmp/x.db", "127.0.0.1", 9999, "t")
    assert _parser().parse_args(["console", "--db", "x"]).port == lconsole.DEFAULT_PORT == 8766
    env = {**os.environ, "PYTHONPATH": ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")}
    r = subprocess.run([sys.executable, "-m", "lingshu_ng.integrations.console", "--help"], capture_output=True,
                       text=True, env=env, cwd=ROOT, timeout=60)
    assert r.returncode == 0 and "--token" in r.stdout and "--audit-log" in r.stdout


def test_console_assets_declared_as_package_data():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        cfg = tomllib.load(f)
    pats = cfg["tool"]["setuptools"]["package-data"]["lingshu_ng.integrations"]
    import fnmatch
    for name in ("index.html", "app.js", "app.css"):
        assert any(fnmatch.fnmatch(f"console_static/{name}", p) for p in pats), name
        assert _asset(name)
