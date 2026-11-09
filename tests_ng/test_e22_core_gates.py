"""E22-4 对照上游 d56ab2b：decay_cycle 阈值/add_blindspot/protect_node/insight_verify level 的 fail-loud 闸。"""
import math
import pytest
from lingshu_ng.compat_store import LayeredStore


@pytest.fixture
def s(tmp_path):
    return LayeredStore(str(tmp_path / "a.db"))


@pytest.mark.parametrize("bad", [5, -0.1, float("nan"), float("inf")])
def test_decay_min_confidence_range(s, bad):
    with pytest.raises(ValueError):
        s.decay_cycle(min_confidence=bad)


def test_decay_min_confidence_type(s):
    with pytest.raises(TypeError):
        s.decay_cycle(min_confidence="x")


@pytest.mark.parametrize("c,d", [("", "d"), ("c", ""), ("  ", "d"), (None, "d"), ("c", None)])
def test_blindspot_nonempty(s, c, d):
    with pytest.raises(ValueError):
        s.add_blindspot(c, d)


@pytest.mark.parametrize("bad", ["", "  ", None, 5])
def test_protect_reason_nonempty(s, bad):
    with pytest.raises(ValueError):
        s.protect_node("n1", bad)


@pytest.mark.parametrize("bad", [5, [1]])
def test_insight_verify_level_type(s, bad):
    with pytest.raises(TypeError):
        s.insight_verify("i1", bad)
