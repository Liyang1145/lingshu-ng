import pytest
from lingshu_ng.compat_store import *  # noqa
import lingshu_ng.compat_store as cs


def _store():
    for name in dir(cs):
        o = getattr(cs, name)
        if isinstance(o, type) and hasattr(o, "tag_node"):
            return o
    raise RuntimeError


def test_tag_node_rejects_non_str_and_empty():
    cls = _store()
    obj = cls.__new__(cls)
    for bad in (["a", "b"], "", "  ", None, 5):
        with pytest.raises((TypeError, ValueError)):
            obj.tag_node("x", bad)
