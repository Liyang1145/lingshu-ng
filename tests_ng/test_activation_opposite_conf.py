# -*- coding: utf-8 -*-
"""opposite 抑制按边置信缩放并双向（对照上游 64e9020/d265fab）。"""
from lingshu_ng.activation import ActivationEngine, _GraphView


def _prop(arcs, seed):
    pos, fh = {seed: 1.0}, {seed: 0}
    view = _GraphView.build((0, 0), {n: ("x", True) for n in "ab"}, arcs)
    neg = ActivationEngine._propagate_frontier(pos, view.out, 1, fh)
    return neg


def test_low_confidence_opposite_scales_suppression():
    full = _prop([("a", "b", "opposite", 1.0)], "a")["b"]
    low = _prop([("a", "b", "opposite", 0.3)], "a")["b"]
    assert abs(low - full * 0.3) < 1e-9


def test_opposite_is_symmetric():
    assert "a" in _prop([("a", "b", "opposite", 1.0)], "b")


def test_bad_confidence_clamped():
    nan = float("nan")
    assert _prop([("a", "b", "opposite", nan)], "a")["b"] <= _prop([("a", "b", "opposite", 1.0)], "a")["b"]


def test_reference_propagate_agrees():
    arcs = [("a", "b", "opposite", 0.4)]
    pos, fh = {"a": 1.0}, {"a": 0}
    neg = ActivationEngine._propagate(pos, arcs, 1, fh)
    assert abs(neg["b"] - _prop(arcs, "a")["b"]) < 1e-12
