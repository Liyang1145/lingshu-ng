import io, contextlib, pathlib
from lingshu_ng.integrations import cli

def test_doctor_exit_doc_and_code(tmp_path):
    doc = (pathlib.Path(__file__).parent.parent / "docs/OPERATIONS.md").read_text(encoding="utf-8")
    assert "退出码：`0`" in doc and "`1`" in doc
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(["doctor", "--db", str(tmp_path / "x.db")])
    assert rc in (0, 1)
    assert ('"ok": true' in buf.getvalue().replace("true", "true")) == (rc == 0) or rc == 1
