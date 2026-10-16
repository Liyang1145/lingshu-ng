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
