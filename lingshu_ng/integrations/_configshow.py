"""config --show：列出 LINGSHU_NG_* 环境变量及生效值（敏感项脱敏）。仅标准库。"""
import os
import re

_SECRET = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD)", re.I)
_PATHLIKE_OK = ("TOKEN_FILE", "TOKEN_CACHE")  # 文件路径不是密钥


def _mask(name: str, val: str) -> str:
    if _SECRET.search(name) and not name.endswith(_PATHLIKE_OK):
        return "***" if val else ""
    return val


def show(environ=None) -> dict:
    env = os.environ if environ is None else environ
    vals = {k: _mask(k, v) for k, v in sorted(env.items()) if k.startswith("LINGSHU_NG_")}
    return {"env": vals, "count": len(vals)}


_INT_SUFFIX = ("_PORT", "_MAX", "_LIMIT", "_TOPN", "_CONCURRENCY", "_BYTES")
_NUM_SUFFIX = ("_TIMEOUT", "_SECONDS", "_TTL", "_RATE")


def check(environ=None) -> dict:
    """按后缀校验取值：*_PORT 为 1-65535；整数类/数值类须可解析且非负。返回 {ok, problems}。"""
    env = os.environ if environ is None else environ
    bad = []
    for k, v in sorted(env.items()):
        if not k.startswith("LINGSHU_NG_") or v == "":
            continue
        try:
            if k.endswith("_PORT"):
                if not 1 <= int(v) <= 65535:
                    raise ValueError
            elif k.endswith(_INT_SUFFIX):
                if int(v) < 0:
                    raise ValueError
            elif k.endswith(_NUM_SUFFIX):
                if float(v) < 0:
                    raise ValueError
        except ValueError:
            bad.append({"name": k, "value": _mask(k, v), "error": "取值非法"})
    return {"ok": not bad, "problems": bad}
