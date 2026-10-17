import re
from pathlib import Path
R = Path(__file__).resolve().parents[1]

def test_documented_metrics_exist_in_code():
    doc = (R / "docs/OPERATIONS.md").read_text(encoding="utf-8")
    src = (R / "lingshu_ng/integrations/http.py").read_text(encoding="utf-8")
    names = set(re.findall(r"`(lingshu_ng_[a-z_]+)`", doc))
    assert len(names) >= 8
    for n in names:
        assert n in src, n
