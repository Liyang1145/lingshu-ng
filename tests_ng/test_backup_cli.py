# -*- coding: utf-8 -*-
"""E6-3：lingshu-ng backup / restore（在线快照、完整性、校验和清单、原子恢复与回退）。"""
import json
import logging
import os
import sqlite3

import pytest

from lingshu_ng.engine import MemoryEngine
from lingshu_ng.integrations import backup as bk
from lingshu_ng.integrations.cli import main


def _seed(path, n=5):
    e = MemoryEngine(str(path))
    for i in range(n):
        e.perceive(f"第{i}条备份测试记忆 alpha{i}")
    e.close()


def _count(path):
    c = sqlite3.connect(str(path))
    try:
        return c.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    finally:
        c.close()


def test_backup_while_engine_open(tmp_path, capsys):
    src, dst = tmp_path / "a.db", tmp_path / "snap.db"
    _seed(src)
    live = MemoryEngine(str(src))  # 在线：另一连接持有库并继续写
    live.perceive("备份前最后写入的一条 omega")
    assert main(["backup", "--db", str(src), str(dst)]) == 0
    live.close()
    out = json.loads(capsys.readouterr().out)
    assert out["integrity_check"] == "ok" and out["counts"]["nodes"] == _count(dst) == 6
    man = json.load(open(str(dst) + bk.MANIFEST_SUFFIX, encoding="utf-8"))
    assert man["sha256"] == bk._sha256(str(dst)) and len(man["sha256"]) == 64
    assert not os.path.exists(str(dst) + "-wal")  # 快照为单文件自包含


def test_backup_refuses_overwrite_and_self(tmp_path):
    src, dst = tmp_path / "a.db", tmp_path / "snap.db"
    _seed(src)
    assert main(["backup", "--db", str(src), str(dst)]) == 0
    assert main(["backup", "--db", str(src), str(dst)]) == 1
    assert main(["backup", "--db", str(src), str(dst), "--force"]) == 0
    with pytest.raises(bk.BackupError):
        bk.backup(str(src), str(src), force=True)


def test_backup_rejects_non_lingshu(tmp_path):
    other = tmp_path / "other.db"
    c = sqlite3.connect(str(other)); c.execute("CREATE TABLE t(x)"); c.commit(); c.close()
    with pytest.raises(bk.BackupError, match="不是灵枢库"):
        bk.backup(str(other), str(tmp_path / "s.db"))
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"not a database at all" * 100)
    with pytest.raises(bk.BackupError):
        bk.backup(str(junk), str(tmp_path / "s2.db"))
    assert not os.path.exists(tmp_path / "s.db") and not os.path.exists(tmp_path / "s2.db")


def test_restore_roundtrip_keeps_previous(tmp_path, capsys):
    src, snap = tmp_path / "a.db", tmp_path / "snap.db"
    _seed(src, 3)
    assert main(["backup", "--db", str(src), str(snap)]) == 0
    e = MemoryEngine(str(src)); e.perceive("快照之后的新写入 later"); e.close()
    assert _count(src) == 4
    assert main(["restore", "--db", str(src), str(snap)]) == 1  # 目标存在须 --force
    capsys.readouterr()
    assert main(["restore", "--db", str(src), str(snap), "--force"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sha256_verified"] is True and _count(src) == 3
    assert out["previous_saved_as"] and _count(out["previous_saved_as"]) == 4
    e = MemoryEngine(str(src))  # 恢复后的库可正常打开并召回
    assert e.recall("alpha1", 3)["hits"]
    e.close()


def test_restore_into_fresh_path(tmp_path):
    src, snap, fresh = tmp_path / "a.db", tmp_path / "snap.db", tmp_path / "new" / "b.db"
    _seed(src)
    bk.backup(str(src), str(snap))
    fresh.parent.mkdir()
    out = bk.restore(str(snap), str(fresh))
    assert out["previous_saved_as"] is None and _count(fresh) == 5


def test_restore_detects_tamper(tmp_path):
    src, snap, dst = tmp_path / "a.db", tmp_path / "snap.db", tmp_path / "b.db"
    _seed(src)
    bk.backup(str(src), str(snap))
    c = sqlite3.connect(str(snap)); c.execute("UPDATE nodes SET content = content || 'x'"); c.commit(); c.close()
    with pytest.raises(bk.BackupError, match="校验和"):
        bk.restore(str(snap), str(dst))
    assert not os.path.exists(dst)


def test_backup_restore_audited(tmp_path, caplog):
    src, snap = tmp_path / "a.db", tmp_path / "snap.db"
    _seed(src)
    with caplog.at_level(logging.INFO, logger="lingshu_ng.audit"):
        main(["backup", "--db", str(src), str(snap)])
        main(["backup", "--db", str(src), str(snap)])  # 失败（已存在）
    recs = [json.loads(r.getMessage()) for r in caplog.records if r.name == "lingshu_ng.audit"]
    assert [(r["op"], r["remote"], r["status"]) for r in recs] == [("backup", "cli", 200), ("backup", "cli", 400)]
    assert all("alpha" not in json.dumps(r, ensure_ascii=False) for r in recs)
