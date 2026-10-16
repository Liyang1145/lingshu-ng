import importlib, os
import lingshu_ng.integrations.http as h
def test_env_body_cap(monkeypatch):
    f = h._env_body_cap
    monkeypatch.delenv("LINGSHU_NG_MAX_BODY", raising=False)
    assert f() == 1 << 20
    monkeypatch.setenv("LINGSHU_NG_MAX_BODY", "2048"); assert f() == 2048
    for bad in ("abc", "10", str(1 << 40), "-5"):
        monkeypatch.setenv("LINGSHU_NG_MAX_BODY", bad); assert f() == 1 << 20
def test_documented():
    d = open(os.path.join(os.path.dirname(__file__), "..", "docs", "OPERATIONS.md"), encoding="utf-8").read()
    assert "LINGSHU_NG_MAX_BODY" in d
