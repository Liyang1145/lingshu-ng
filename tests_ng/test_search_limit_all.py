"""对照上游 b36fa67：search_content 的 limit=None/-1 = 全量（此前 None 抛 TypeError）。"""
from lingshu_ng.compat_store import LayeredStore


def _s():
    s = LayeredStore(":memory:")
    for i in range(25):
        s.add_skill("apple%d" % i, "apple pie", "p")
    return s


def test_none_and_minus_one_mean_all():
    s = _s()
    assert len(s.search_content("apple", None, None)) == len(s.search_content("apple", None, -1))
    assert len(s.search_content("apple", None, None)) >= len(s.search_content("apple", None, 5))


def test_zero_returns_empty():
    assert _s().search_content("apple", None, 0) == []
