import pathlib, re
R = pathlib.Path(__file__).parent.parent

def test_alert_metrics_exist_in_code():
    doc = (R / "docs/OPERATIONS.md").read_text(encoding="utf-8")
    sec = doc.split("## Prometheus 告警规则示例", 1)[1]
    code = (R / "lingshu_ng/integrations/http.py").read_text(encoding="utf-8")
    names = set(re.findall(r"lingshu_ng_[a-z_]+", sec))
    assert names
    for n in names:
        base = re.sub(r"_bucket$", "", n)
        assert base in code, n
