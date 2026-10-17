import pathlib
def test_upgrade_checklist_present():
    t = (pathlib.Path(__file__).parent.parent / "docs/OPERATIONS.md").read_text(encoding="utf-8")
    assert "## 升级前检查清单与回滚演练" in t
    for k in ("doctor", "config --check", "backup", "restore"):
        assert k in t
