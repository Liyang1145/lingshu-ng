#!/usr/bin/env python3
"""生成 CycloneDX 1.5 JSON SBOM（纯标准库，E6-1）。

覆盖核心包 lingshu-ng 与 plugins/ 下各插件包，以及插件声明的第三方运行依赖（版本区间记在
property ``lingshu:requirement``；具体解析版本取决于安装环境，SBOM 不臆造）。

用法：python tools/release/sbom.py [-o sbom.cdx.json] [--timestamp 2026-01-01T00:00:00Z]
同一源码树与时间戳下输出逐字节相同（serialNumber 由内容派生的 uuid5）。
"""
import argparse
import datetime as _dt
import json
import pathlib
import re
import sys
import tomllib
import uuid

_REQ = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*?)\s*(?:;.*)?$")
_VER = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.M)


def _norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _version_of(pkg_dir: pathlib.Path) -> str:
    m = _VER.search((pkg_dir / "__init__.py").read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"找不到 __version__：{pkg_dir}")
    return m.group(1)


def _project(pyproject: pathlib.Path):
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    proj = data["project"]
    attr = data.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("version", {}).get("attr", "")
    mod = attr.rsplit(".", 1)[0]
    base = pyproject.parent
    where = data.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {}).get("where", ["."])
    pkg_dir = base / where[0] / mod.replace(".", "/")
    return proj, _version_of(pkg_dir)


def _comp(name, version, desc=None, lic=None):
    c = {"type": "library", "bom-ref": f"pkg:pypi/{_norm(name)}@{version}", "name": name,
         "version": version, "purl": f"pkg:pypi/{_norm(name)}@{version}"}
    if desc:
        c["description"] = desc
    if lic:
        c["licenses"] = [{"license": {"id": lic}}]
    return c


def build_sbom(root, timestamp=None):
    root = pathlib.Path(root)
    if timestamp is None:
        timestamp = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    core_proj, core_ver = _project(root / "pyproject.toml")
    core = _comp(core_proj["name"], core_ver, core_proj.get("description"), core_proj.get("license"))
    core["type"] = "application"
    first_party = {_norm(core_proj["name"]): core["bom-ref"]}
    plugins = []
    for pp in sorted((root / "plugins").glob("*/pyproject.toml")):
        proj, ver = _project(pp)
        c = _comp(proj["name"], ver, proj.get("description"), proj.get("license") if isinstance(proj.get("license"), str) else None)
        first_party[_norm(proj["name"])] = c["bom-ref"]
        plugins.append((c, proj.get("dependencies", [])))
    third = {}
    deps = {core["bom-ref"]: [first_party.get(_norm(_REQ.match(r).group(1))) or f"pkg:pypi/{_norm(_REQ.match(r).group(1))}"
                              for r in core_proj.get("dependencies", [])]}
    for c, reqs in plugins:
        out = []
        for r in reqs:
            m = _REQ.match(r)
            n = _norm(m.group(1))
            if n in first_party:
                out.append(first_party[n])
                continue
            ref = f"pkg:pypi/{n}"
            t = third.setdefault(ref, {"type": "library", "bom-ref": ref, "name": n, "purl": ref,
                                       "properties": []})
            prop = {"name": "lingshu:requirement", "value": f"{n}{m.group(2)} (by {c['name']})"}
            if prop not in t["properties"]:
                t["properties"].append(prop)
            out.append(ref)
        deps[c["bom-ref"]] = sorted(set(out))
    for ref in third:
        deps.setdefault(ref, [])
    components = [c for c, _ in plugins] + [third[k] for k in sorted(third)]
    dependencies = [{"ref": r, "dependsOn": deps[r]} for r in sorted(deps)]
    body = {"metadata": {"timestamp": timestamp, "component": core,
                         "tools": {"components": [{"type": "application", "name": "lingshu-ng tools/release/sbom.py"}]}},
            "components": components, "dependencies": dependencies}
    serial = uuid.uuid5(uuid.NAMESPACE_URL, "lingshu-ng-sbom:" + json.dumps(body, sort_keys=True, ensure_ascii=False))
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}", "version": 1, **body}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", default="-")
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[2]))
    ap.add_argument("--timestamp", default=None)
    a = ap.parse_args(argv)
    txt = json.dumps(build_sbom(a.root, a.timestamp), ensure_ascii=False, indent=2) + "\n"
    if a.output == "-":
        sys.stdout.write(txt)
    else:
        pathlib.Path(a.output).write_text(txt, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
