# -*- coding: utf-8 -*-
"""lingshu-ng doctor：一键自检（只读，纯标准库）。每项返回 ok/warn/fail，任一 fail → 退出码 1。"""
from __future__ import annotations

import os
import logging
import shutil
import sqlite3
import sys
from typing import Dict, List, Optional

MIN_FREE_BYTES = 256 * 1024 * 1024


def _chk(name: str, status: str, detail: str) -> Dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def run_doctor(db: Optional[str], env: Optional[Dict[str, str]] = None) -> Dict:
    env = os.environ if env is None else env
    checks: List[Dict[str, str]] = []
    checks.append(_chk("python", "ok" if sys.version_info >= (3, 9) else "fail", sys.version.split()[0]))
    if not db or db == ":memory:":
        checks.append(_chk("db", "fail", "未指定库文件（--db 或 LINGSHU_NG_DB）"))
    elif not os.path.exists(db):
        checks.append(_chk("db", "fail", "库文件不存在"))
    else:
        try:
            c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                r = c.execute("PRAGMA integrity_check").fetchone()[0]
                checks.append(_chk("integrity", "ok" if r == "ok" else "fail", str(r)[:200]))
                tabs = {x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                miss = [t for t in ("nodes", "edges", "engine_meta") if t not in tabs]
                checks.append(_chk("tables", "fail" if miss else "ok", ("缺表 " + ",".join(miss)) if miss else "nodes/edges/engine_meta 齐全"))
                if "engine_meta" in tabs:
                    row = c.execute("SELECT value FROM engine_meta WHERE key='schema_version'").fetchone()
                    checks.append(_chk("schema", "ok" if row else "warn", f"schema_version={row[0]}" if row else "未记录 schema_version"))
            finally:
                c.close()
        except sqlite3.Error as e:
            checks.append(_chk("integrity", "fail", f"无法打开：{type(e).__name__}"))
        try:
            free = shutil.disk_usage(os.path.dirname(os.path.abspath(db))).free
            checks.append(_chk("disk", "ok" if free >= MIN_FREE_BYTES else "warn", f"余量 {free // (1 << 20)} MiB"))
        except OSError:
            checks.append(_chk("disk", "warn", "无法读取磁盘余量"))
    token = env.get("LINGSHU_NG_TOKEN", "")
    tfile = env.get("LINGSHU_NG_TOKEN_FILE", "")
    host = env.get("LINGSHU_NG_HOST", "127.0.0.1")
    loop = host in ("127.0.0.1", "localhost", "::1")
    if not loop and not (token or tfile):
        checks.append(_chk("auth", "fail", "绑定非回环地址但未配置令牌"))
    elif token and len(token) < 16:
        checks.append(_chk("auth", "warn", "令牌短于 16 字符"))
    else:
        checks.append(_chk("auth", "ok", "回环绑定或已配置令牌"))
    if tfile:
        try:
            m = os.stat(tfile).st_mode & 0o077
            checks.append(_chk("token_file", "warn" if (m and os.name == "posix") else "ok", "权限过宽" if (m and os.name == "posix") else "可读"))
        except OSError:
            checks.append(_chk("token_file", "fail", "令牌文件不可读"))
    try:
        from ..capabilities import capabilities
        caps = capabilities()
        checks.append(_chk("optional", "ok", ",".join(sorted(map(str, caps)))[:200] if hasattr(caps, "__iter__") else "已加载"))
    except Exception as e:  # 可选件缺失不算故障
        logging.getLogger(__name__).warning("doctor: 能力探测失败 %s", type(e).__name__)
        checks.append(_chk("optional", "warn", f"能力探测失败：{type(e).__name__}"))
    bad = [c for c in checks if c["status"] == "fail"]
    return {"ok": not bad, "checks": checks}
