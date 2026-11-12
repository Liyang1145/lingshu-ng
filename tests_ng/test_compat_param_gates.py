"""对照上游 8001322：兼容门面读/触达入口的参数类型闸（非 str/空白 id、非整数 keep → fail-loud，不再静默 None/[]）。"""
import pytest
from lingshu_ng.compat import SpacetimeMemoryEngine

BAD = [123, None, "", "  "]


@pytest.mark.parametrize("name", ["get_edge", "get_outgoing_edges", "get_incoming_edges", "traverse", "increment_access"])
@pytest.mark.parametrize("bad", BAD)
def test_id_gates(name, bad):
    e = SpacetimeMemoryEngine(":memory:")
    try:
        with pytest.raises(TypeError):
            getattr(e.store, name)(bad)
    finally:
        e.close()


@pytest.mark.parametrize("bad", ["x", 1.5, None, True])
def test_prune_keep_type(bad):
    e = SpacetimeMemoryEngine(":memory:")
    try:
        with pytest.raises(TypeError):
            e.store.prune_self_snapshots(bad)
    finally:
        e.close()


def test_prune_negative_and_ok():
    e = SpacetimeMemoryEngine(":memory:")
    try:
        with pytest.raises(ValueError):
            e.store.prune_self_snapshots(-1)
        assert e.store.prune_self_snapshots(5) >= 0
        assert e.store.get_edge("nope") is None
    finally:
        e.close()
