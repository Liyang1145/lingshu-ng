# -*- coding: utf-8 -*-
"""sec-r2：sec-r1 遗留项 O2（导入覆盖可见）、O3（标签/实体条数上限）、O5（LLM 抽取拒非 https 外发、缓存 0600）。"""
import json
import os
import sys

import pytest

from lingshu_ng import inputs
from lingshu_ng.engine import MemoryEngine


@pytest.fixture
def eng(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    e = MemoryEngine(str(tmp_path / "m.db"))
    yield e
    e.close()


def test_tag_count_and_length_capped(eng):
    with pytest.raises(ValueError):
        eng.perceive("x", tags=[f"t{i}" for i in range(inputs.MAX_LIST_ITEMS + 1)])
    with pytest.raises(ValueError):
        eng.perceive("x", tags=["a" * (inputs.MAX_ITEM_CHARS + 1)])
    assert eng.store.nodes.count() == 0
    eng.perceive("ok", tags=[f"t{i}" for i in range(inputs.MAX_LIST_ITEMS)])
    assert eng.store.nodes.count() == 1


def test_import_overwrite_is_reported(eng, tmp_path):
    nid = eng.perceive("原始内容", skip_dedup=True).node_id
    p = tmp_path / "bk.json"
    p.write_text(json.dumps({"nodes": [{"id": nid, "content": "被导入覆盖", "layer": "knowledge"},
                                       {"id": "fresh", "content": "新节点", "layer": "knowledge"}]},
                            ensure_ascii=False), encoding="utf-8")
    r = eng.import_all(str(p))
    assert r["overwritten"] == {"nodes": 1} and r["imported"]["nodes"] == 2


def test_llm_url_policy(monkeypatch):
    from lingshu_ng.chain import llm_extract as le
    assert le._url_ok("https://api.example.com/v1")
    assert le._url_ok("http://127.0.0.1:8000/v1") and le._url_ok("http://localhost/v1")
    assert not le._url_ok("http://api.example.com/v1") and not le._url_ok("ftp://x")


def test_bearer_scheme_case_insensitive(tmp_path, monkeypatch):
    import http.client, threading
    from lingshu_ng.integrations import http as lhttp
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    s = lhttp.make_server(str(tmp_path / "b.db"), "127.0.0.1", 0, "tok")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        for hdr, want in (("Bearer tok", 200), ("bearer tok", 200), ("BEARER tok", 200), ("Basic tok", 401), ("bearer bad", 401)):
            c = http.client.HTTPConnection("127.0.0.1", s.server_address[1], timeout=10)
            c.request("GET", "/v1/status", headers={"Authorization": hdr})
            assert c.getresponse().status == want, hdr
            c.close()
    finally:
        s.shutdown(); s.server_close(); s.service.close()
