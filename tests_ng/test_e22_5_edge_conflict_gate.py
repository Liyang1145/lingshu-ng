"""E22-5 对照上游 e6724bc：add_edge condition_space / register_conflict 端点 类型闸。"""
import pytest
from lingshu_ng.compat_engine import SpacetimeMemoryEngine as E


@pytest.fixture()
def eng(tmp_path):
    e = E(str(tmp_path / "a.db"))
    return e


def _ids(e):
    a = e.add_perception("alpha one", "text")
    b = e.add_perception("beta two", "text")
    return a.id, b.id


@pytest.mark.parametrize("bad", ["bad", 3, {"x": 1}, [1]])
def test_add_edge_condition_space_type(eng, bad):
    a, b = _ids(eng)
    with pytest.raises(TypeError, match="condition_space"):
        eng.add_edge(a, b, condition_space=bad)


@pytest.mark.parametrize("bad", [(1, 2), (None, "x"), ("x", None), (b"a", "b")])
def test_register_conflict_id_type(eng, bad):
    with pytest.raises(TypeError, match="node id|a_id|b_id"):
        eng.register_conflict(*bad)
