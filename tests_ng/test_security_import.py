# -*- coding: utf-8 -*-
"""sec-r1：导入面类型混淆回归——坏备份不得毒化库（导入后召回照常）、不得以非 ValueError 崩溃。"""
import json

import pytest

from lingshu_ng.engine import MemoryEngine


@pytest.fixture
def eng(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    monkeypatch.delenv("AEIS_DESIGNER_KEY", raising=False)
    e = MemoryEngine(str(tmp_path / "m.db"))
    e.perceive("基线记忆一条", skip_dedup=True)
    yield e
    e.close()


def _dump(tmp_path, obj, raw=False):
    p = tmp_path / "bk.json"
    p.write_text(obj if raw else json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(p)


@pytest.mark.parametrize("obj", [[1, 2], "abc", {"nodes": 5}, "[" * 100000 + "]" * 100000], ids=["list", "str", "nodes_int", "deep"])
def test_malformed_backup_raises_valueerror(eng, tmp_path, obj):
    with pytest.raises(ValueError):
        eng.import_all(_dump(tmp_path, obj, raw=isinstance(obj, str) and obj.startswith("[")))


def test_type_confused_rows_rejected_not_poisoning(eng, tmp_path):
    rows = [{"id": "n_imp", "content": "imp-str 记忆", "importance": "high", "layer": "knowledge"},
            {"id": "n_int", "content": 12345, "layer": "knowledge"},
            {"id": None, "content": "无 id", "layer": "knowledge"},
            {"id": "n_dict", "content": {"a": 1}, "layer": "knowledge"},
            {"id": "n_ok", "content": "合法 导入 记忆", "importance": "0.7", "layer": "knowledge"}]
    r = eng.import_all(_dump(tmp_path, {"nodes": rows}))
    assert r["imported"]["nodes"] == 1 and r["rejected_rows"]["nodes"] == 4
    assert eng.recall("imp-str 记忆", 5)["hits"] == [] or all(n.id != "n_imp" for n, _ in eng.recall("imp-str 记忆", 5)["hits"])
    assert [n.id for n, _ in eng.recall("合法 导入 记忆", 5)["hits"]][:1] == ["n_ok"]
    assert eng.recall("基线记忆一条", 5)["hits"]
