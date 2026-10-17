import io, json, contextlib
from lingshu_ng.integrations import cli
from lingshu_ng.integrations._configshow import show


def test_masks_secrets_keeps_others():
    r = show({"LINGSHU_NG_TOKEN": "abc", "LINGSHU_NG_LLM_KEY": "k", "LINGSHU_NG_TOKEN_FILE": "/t", "LINGSHU_NG_DB": "x.db", "OTHER": "1"})
    assert r["env"] == {"LINGSHU_NG_DB": "x.db", "LINGSHU_NG_LLM_KEY": "***", "LINGSHU_NG_TOKEN": "***", "LINGSHU_NG_TOKEN_FILE": "/t"}


def test_cli_config_show(monkeypatch):
    monkeypatch.setenv("LINGSHU_NG_TOKEN", "sekret")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert cli.main(["config", "--show"]) == 0
    assert "sekret" not in buf.getvalue()
    assert json.loads(buf.getvalue())["env"]["LINGSHU_NG_TOKEN"] == "***"


def test_masks_suffix_wildcards():
    r = show({"LINGSHU_NG_DB_PASSWORD": "p", "LINGSHU_NG_X_SECRET": "s", "LINGSHU_NG_API_KEY": "k", "LINGSHU_NG_EMPTY_KEY": ""})
    assert r["env"] == {"LINGSHU_NG_DB_PASSWORD": "***", "LINGSHU_NG_X_SECRET": "***", "LINGSHU_NG_API_KEY": "***", "LINGSHU_NG_EMPTY_KEY": ""}


def test_config_check():
    from lingshu_ng.integrations._configshow import check
    assert check({"LINGSHU_NG_HTTP_PORT": "8080", "LINGSHU_NG_X_TIMEOUT": "1.5"})["ok"]
    r = check({"LINGSHU_NG_HTTP_PORT": "99999", "LINGSHU_NG_X_MAX": "abc"})
    assert not r["ok"] and len(r["problems"]) == 2


def test_config_check_db_dir_and_token_file_perms(tmp_path):
    import os, sys
    from lingshu_ng.integrations._configshow import check
    r = check({"LINGSHU_NG_DB": str(tmp_path / "no" / "x.db")})
    assert not r["ok"] and r["problems"][0]["name"] == "LINGSHU_NG_DB"
    assert check({"LINGSHU_NG_DB": str(tmp_path / "x.db")})["ok"]
    tf = tmp_path / "tok"
    tf.write_text("a\n")
    if sys.platform != "win32":
        os.chmod(tf, 0o644)
        r = check({"LINGSHU_NG_TOKEN_FILE": str(tf)})
        assert not r["ok"] and "0600" in r["problems"][0]["error"]
        os.chmod(tf, 0o600)
        assert check({"LINGSHU_NG_TOKEN_FILE": str(tf)})["ok"]
    r = check({"LINGSHU_NG_TOKEN_FILE": str(tmp_path / "missing")})
    assert not r["ok"]
