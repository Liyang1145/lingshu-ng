# -*- coding: utf-8 -*-
"""E8-2：lingshu-ng doctor。"""
import json

from lingshu_ng.engine import MemoryEngine
from lingshu_ng.integrations.cli import main
from lingshu_ng.integrations.doctor import run_doctor


def test_healthy_db(tmp_path, capsys):
    p = tmp_path / "a.db"
    e = MemoryEngine(str(p)); e.perceive("hello doctor"); e.close()
    assert main(["doctor", "--db", str(p)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and {c["name"] for c in out["checks"]} >= {"integrity", "tables", "disk", "auth"}


def test_missing_db_fails(tmp_path, capsys):
    assert main(["doctor", "--db", str(tmp_path / "no.db")]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_corrupt_db_fails(tmp_path):
    p = tmp_path / "bad.db"
    p.write_bytes(b"not a sqlite file" * 100)
    assert run_doctor(str(p), env={})["ok"] is False


def test_nonloopback_without_token_fails(tmp_path):
    p = tmp_path / "a.db"
    e = MemoryEngine(str(p)); e.close()
    r = run_doctor(str(p), env={"LINGSHU_NG_HOST": "0.0.0.0"})
    assert not r["ok"] and any(c["name"] == "auth" and c["status"] == "fail" for c in r["checks"])
    r = run_doctor(str(p), env={"LINGSHU_NG_HOST": "0.0.0.0", "LINGSHU_NG_TOKEN": "x" * 32})
    assert r["ok"]
