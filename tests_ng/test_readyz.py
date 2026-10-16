import json, threading, http.client
from lingshu_ng.integrations import http as lhttp


def test_readyz(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    db = str(tmp_path / "r.db")
    s = lhttp.make_server(db, "127.0.0.1", 0, "tok")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    port = s.server_address[1]

    def get(p):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", p)
        r = c.getresponse()
        return r.status, json.loads(r.read())
    try:
        assert get("/readyz") == (200, {"ready": True})
        assert get("/healthz") == (200, {"ok": True})
        s.service.path = str(tmp_path / "no" / "x.db")
        st, b = get("/readyz")
        assert st == 503 and b["ready"] is False
    finally:
        s.shutdown(); s.server_close(); s.service.close()
