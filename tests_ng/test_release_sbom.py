"""E6-1：SBOM（CycloneDX 1.5 JSON）与发布产物 SHA256 校验和脚本（tools/release/）。"""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name):
    p = ROOT / "tools" / "release" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_rel_{name}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_sbom_structure_and_core_zero_deps():
    sbom = _load("sbom").build_sbom(ROOT, timestamp="2026-01-01T00:00:00Z")
    assert sbom["bomFormat"] == "CycloneDX" and sbom["specVersion"] == "1.5"
    assert sbom["serialNumber"].startswith("urn:uuid:")
    core = sbom["metadata"]["component"]
    import lingshu_ng
    assert core["name"] == "lingshu-ng" and core["version"] == lingshu_ng.__version__
    assert core["purl"] == f"pkg:pypi/lingshu-ng@{lingshu_ng.__version__}"
    deps = {d["ref"]: d.get("dependsOn", []) for d in sbom["dependencies"]}
    assert deps[core["bom-ref"]] == []          # 核心零第三方依赖
    names = {c["name"] for c in sbom["components"]}
    for p in ("lingshu-ng-embed", "lingshu-ng-world", "lingshu-ng-nn", "lingshu-ng-gen", "lingshu-ng-adapters"):
        assert p in names
    assert "numpy" in names and "onnxruntime" in names
    embed = next(c for c in sbom["components"] if c["name"] == "lingshu-ng-embed")
    assert core["bom-ref"] in deps[embed["bom-ref"]]
    for c in sbom["components"]:
        assert c["type"] == "library" and c["bom-ref"]
    refs = {core["bom-ref"]} | {c["bom-ref"] for c in sbom["components"]}
    for r, ds in deps.items():
        assert r in refs and set(ds) <= refs


def test_sbom_deterministic_with_fixed_timestamp():
    m = _load("sbom")
    a = m.build_sbom(ROOT, timestamp="2026-01-01T00:00:00Z")
    b = m.build_sbom(ROOT, timestamp="2026-01-01T00:00:00Z")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_sbom_cli_writes_file(tmp_path):
    out = tmp_path / "sbom.cdx.json"
    r = subprocess.run([sys.executable, str(ROOT / "tools/release/sbom.py"), "-o", str(out)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["bomFormat"] == "CycloneDX"


def test_checksums_markdown_and_sha256sums(tmp_path):
    m = _load("checksums")
    (tmp_path / "a.whl").write_bytes(b"hello")
    (tmp_path / "b.tar.gz").write_bytes(b"world!")
    rows = m.compute(sorted(tmp_path.iterdir()))
    assert rows[0] == ("a.whl", hashlib.sha256(b"hello").hexdigest(), 5)
    txt = m.sha256sums(rows)
    assert txt.splitlines()[1] == f"{hashlib.sha256(b'world!').hexdigest()}  b.tar.gz"
    md = m.markdown(rows)
    assert "| 文件 |" in md and hashlib.sha256(b"hello").hexdigest() in md
    # 校验模式：一致时返回 0，篡改后返回 1
    sums = tmp_path / "SHA256SUMS"
    sums.write_text(txt, encoding="utf-8")
    assert m.verify(sums) == 0
    (tmp_path / "a.whl").write_bytes(b"tampered")
    assert m.verify(sums) == 1


def test_release_tools_stdlib_only():
    import ast
    std = set(sys.stdlib_module_names)
    for p in (ROOT / "tools/release").glob("*.py"):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                   [n.module] if isinstance(n, ast.ImportFrom) and n.module and n.level == 0 else []
            for mod in mods:
                assert mod.split(".")[0] in std, (p.name, mod)
