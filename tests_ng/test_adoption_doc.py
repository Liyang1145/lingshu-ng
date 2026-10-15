import re, pathlib
R = pathlib.Path(__file__).resolve().parents[1]
def test_adoption_refs_exist():
    t = (R/"docs/ADOPTION.md").read_text(encoding="utf-8")
    for p in re.findall(r"(?:docs|tests_ng|\.github)/[\w./-]+\.(?:md|py|yml)", t):
        assert (R/p).exists(), p
    assert "未胜项" in t
