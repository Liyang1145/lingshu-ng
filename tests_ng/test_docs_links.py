import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')

def test_relative_doc_links_exist():
    files = list((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
    bad = []
    for f in files:
        if not f.exists():
            continue
        for t in LINK.findall(f.read_text(encoding="utf-8")):
            if t.startswith(("http", "mailto:", "#")):
                continue
            p = t.split("#")[0]
            if p and not (f.parent / p).exists():
                bad.append((f.name, t))
    assert not bad, bad
