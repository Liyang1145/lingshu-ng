import pathlib
def test_ops_doc_has_probes():
    d = (pathlib.Path(__file__).parent.parent / "docs/OPERATIONS.md").read_text(encoding="utf-8")
    assert "/readyz" in d and "/healthz" in d and "readinessProbe" in d and "livenessProbe" in d
