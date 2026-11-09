"""E22-3 对照上游 e6724bc/533de41：insight_* 输入类型闸（fail-loud）。"""
import pytest
from lingshu_ng.compat_store import LayeredStore


@pytest.fixture
def s(tmp_path):
    return LayeredStore(str(tmp_path / "a.db"))


@pytest.mark.parametrize("bad", [None, 5, ""])
def test_record_content_must_be_nonempty_str(s, bad):
    with pytest.raises(ValueError):
        s.insight_record(bad)


def test_record_conditions_must_be_mapping(s):
    with pytest.raises(ValueError):
        s.insight_record("x", [1])


def test_window_conditions_must_be_mapping(s):
    with pytest.raises(ValueError):
        s.insight_window([1])
    assert s.insight_window(None)["window_open"] in (True, False)
