"""E22-7 对照上游 e3087f7(#1359-#1361)：update_node_importance/confidence delta、get_skill_by_name name 类型闸。"""
import pytest
from lingshu_ng.compat_store import LayeredStore as E


@pytest.mark.parametrize("m", ["update_node_importance", "update_node_confidence"])
@pytest.mark.parametrize("d", [None, "1", float("nan"), float("inf"), True])
def test_delta_gate(tmp_path, m, d):
    e = E(str(tmp_path / "a.db"))
    with pytest.raises(TypeError):
        getattr(e, m)("x", d)


@pytest.mark.parametrize("n", [None, 5])
def test_skill_name_gate(tmp_path, n):
    e = E(str(tmp_path / "a.db"))
    with pytest.raises(TypeError):
        e.get_skill_by_name(n)
