# -*- coding: utf-8 -*-
"""E22：对照上游 8e0a12d（add_perception 入参）/ 67a2c0f（导出剥 BiDi）。"""
import json

import pytest

from lingshu_ng.compat import SpacetimeMemoryEngine


@pytest.mark.parametrize("kw,exc", [({"entities": [1]}, TypeError), ({"tags": ["ok", 123]}, TypeError),
                                    ({"tags": [""]}, ValueError), ({"modality": 5}, TypeError),
                                    ({"modality": None}, TypeError), ({"modality": ""}, ValueError)])
def test_perception_params_fail_loud_no_side_effect(kw, exc):
    e = SpacetimeMemoryEngine(":memory:")
    with pytest.raises(exc):
        e.add_perception("某事件", **kw)
    assert e.store.count_layer(__import__("lingshu_ng.types", fromlist=["x"]).MemoryLayer.KNOWLEDGE) == 0


def test_none_tag_items_skipped():
    e = SpacetimeMemoryEngine(":memory:")
    n = e.add_perception("某事件", tags=["a", None])
    assert "a" in n.tags and None not in n.tags


def test_export_strips_bidi(tmp_path):
    e = SpacetimeMemoryEngine(":memory:")
    e.add_perception("file\u202etxt 与\u200b零宽，العربية 与中文")
    p = str(tmp_path / "x.json")
    e.export_all(p)
    t = open(p, encoding="utf-8").read()
    assert "\u202e" not in t and "\u200b" not in t and "العربية" in t and "中文" in t
