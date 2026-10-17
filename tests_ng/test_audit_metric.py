from lingshu_ng.integrations import http


def test_audit_counter_increments():
    n = http._AUDIT_LINES[0]
    http.audit("perceive", "127.0.0.1", 200)
    assert http._AUDIT_LINES[0] == n + 1
