"""E22-6 对照上游 d56ab2b：protect_node 参数类型闸。"""
import pytest
from lingshu_ng.compat_engine import SpacetimeMemoryEngine as E


@pytest.mark.parametrize("nid,reason", [(None, "r"), (5, "r"), ("x", None), ("x", 3)])
def test_protect_type_gate(tmp_path, nid, reason):
    e = E(str(tmp_path / "a.db"))
    with pytest.raises(TypeError):
        e.protect_node(nid, reason)
