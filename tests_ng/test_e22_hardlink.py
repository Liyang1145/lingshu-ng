# -*- coding: utf-8 -*-
"""E22-8 导出写路径拒硬链接 nlink>1（对照上游 139ffde/bb29a04）。"""
import os
import pytest
from lingshu_ng.compat import SpacetimeMemoryEngine


def _linked(tmp_path):
    victim = tmp_path / "victim.md"
    victim.write_text("PROTECTED", encoding="utf-8")
    link = tmp_path / "out.json"
    try:
        os.link(victim, link)
    except OSError:
        pytest.skip("no hardlink")
    return victim, link


@pytest.mark.parametrize("fn", ["export_all", "export_trajectory"])
def test_export_refuses_hardlink(tmp_path, fn):
    victim, link = _linked(tmp_path)
    e = SpacetimeMemoryEngine(":memory:")
    with pytest.raises(ValueError):
        e.export_all(str(link)) if fn == "export_all" else e.export_trajectory(None, str(link))
    assert victim.read_text(encoding="utf-8") == "PROTECTED"


def test_export_plain_file_ok(tmp_path):
    e = SpacetimeMemoryEngine(":memory:")
    p = tmp_path / "ok.json"
    e.export_all(str(p))
    e.export_all(str(p))
    assert p.exists()
