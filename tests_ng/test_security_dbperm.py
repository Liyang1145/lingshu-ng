# -*- coding: utf-8 -*-
"""sec-r1：新建库文件（及 -wal / -shm）仅属主可读写；已有库文件的权限不被改动。"""
import os
import stat
import sys

import pytest

from lingshu_ng.engine import MemoryEngine

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX 权限位")


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def test_new_db_is_owner_only(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    old = os.umask(0o022)
    try:
        p = str(tmp_path / "new.db")
        e = MemoryEngine(p)
        e.perceive("私密记忆", skip_dedup=True)
        assert _mode(p) == 0o600
        for suf in ("-wal", "-shm"):
            if os.path.exists(p + suf):
                assert _mode(p + suf) & 0o077 == 0, suf
        e.close()
    finally:
        os.umask(old)


def test_existing_db_mode_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_SEM", "off")
    p = str(tmp_path / "shared.db")
    MemoryEngine(p).close()
    os.chmod(p, 0o640)
    MemoryEngine(p).close()
    assert _mode(p) == 0o640
