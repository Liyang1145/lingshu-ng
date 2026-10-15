# -*- coding: utf-8 -*-
"""sec-r1：插件依赖下沿不得允许已知有漏洞的版本（pip-audit：Pillow 12.2.0 有 13 条 PYSEC-2026-*，修复于 12.3.0）。"""
import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
#: 包名 → 最低安全版本（来源：pip-audit / OSV，2026-10-15）
MIN_SAFE = {"pillow": (12, 3)}


def test_plugin_dependency_floors_exclude_known_vulnerable():
    bad = []
    for pp in sorted((ROOT / "plugins").glob("*/pyproject.toml")):
        for spec in tomllib.loads(pp.read_text(encoding="utf-8"))["project"].get("dependencies", []):
            name = re.split(r"[<>=!~ \[]", spec, 1)[0].lower()
            if name not in MIN_SAFE:
                continue
            m = re.search(r">=\s*(\d+)\.(\d+)", spec)
            if not m or (int(m.group(1)), int(m.group(2))) < MIN_SAFE[name]:
                bad.append(f"{pp.parent.name}: {spec}")
    assert not bad, bad
