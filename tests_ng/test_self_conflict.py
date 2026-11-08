"""对照上游 7931505：register_conflict 拒绝自冲突，不给节点打永久 conflict 标签。"""
import pytest
from lingshu_ng.engine import MemoryEngine


def test_self_conflict_rejected():
    e = MemoryEngine(":memory:")
    a = e.add_context("alpha fact").node_id
    with pytest.raises(ValueError):
        e.register_conflict(a, a)
    assert "conflict" not in e.store.nodes.get(a).tags


def test_compat_self_conflict_rejected():
    from lingshu_ng.compat_engine import SpacetimeMemoryEngine as S
    s = S(":memory:")
    a = s.ng.add_context("alpha fact").node_id
    with pytest.raises(ValueError):
        s.store.register_conflict(a, a)
    assert "conflict" not in s.ng.store.nodes.get(a).tags
