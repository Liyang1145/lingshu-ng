import re, pathlib
R = pathlib.Path(__file__).resolve().parent.parent
def test_plugin_versions_match_core():
    core = re.search(r'^__version__ = "([^"]+)"', (R/"lingshu_ng/__init__.py").read_text(), re.M).group(1)
    for f in (R/"plugins").glob("*/src/*/__init__.py"):
        v = re.search(r'^__version__ = "([^"]+)"', f.read_text(), re.M).group(1)
        assert v.split(".")[:2] == core.split(".")[:2], (f, v, core)
def test_console_status_nowrap():
    p = R/"lingshu_ng/integrations/console_static"
    assert "nowrap" in (p/"app.js").read_text() and "td.nowrap" in (p/"app.css").read_text()
