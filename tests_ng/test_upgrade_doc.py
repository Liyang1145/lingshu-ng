import re, pathlib
from lingshu_ng.store import schema

def test_upgrade_doc_schema_matches_code():
    t = (pathlib.Path(__file__).parent.parent / "docs" / "UPGRADE.md").read_text(encoding="utf-8")
    m = re.search(r"当前 schema 版本：\*\*(\d+)\*\*", t)
    assert m and int(m.group(1)) == schema.SCHEMA_VERSION
