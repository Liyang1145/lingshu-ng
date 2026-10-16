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
