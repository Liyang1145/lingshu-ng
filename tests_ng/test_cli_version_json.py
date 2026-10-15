import json
from lingshu_ng.integrations import cli


def test_version_json(capsys):
    assert cli.main(["version"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert {"version", "schema", "python", "optional"} <= set(d)
    assert isinstance(d["optional"]["numpy"], bool)
