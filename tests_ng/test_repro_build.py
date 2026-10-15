import importlib.util, pathlib, pytest
p = pathlib.Path(__file__).resolve().parents[1] / "tools/release/repro_check.py"
spec = importlib.util.spec_from_file_location("repro_check", p)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_two_builds_identical():
    pytest.importorskip("build"); pytest.importorskip("setuptools")
    a, b = m.check()
    assert a and any(k.endswith(".whl") for k in a) and any(k.endswith(".tar.gz") for k in a)
    assert a == b
