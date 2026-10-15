# -*- coding: utf-8 -*-
"""命令行入口：``python -m lingshu_ng <子命令>`` 或安装后的 ``lingshu-ng <子命令>``。

子命令::

    serve         --db PATH [--host 127.0.0.1] [--port 8765] [--token T]   本机 HTTP/JSON 服务
    console       --db PATH [--host 127.0.0.1] [--port 8766] [--token T]   本机 Web 控制台（docs/CONSOLE.md）
    mcp           --db PATH                                                MCP stdio 适配器
    perceive      --db PATH TEXT [--tag T ...]                             写入一条，打印 JSON 回执
    recall        --db PATH QUERY [--limit 10]                             召回，打印 JSON
    status        --db PATH                                                库状态
    capabilities  [--db PATH]                                              当前生效档位
    doctor        [--db PATH]                                              只读自检，失败退出码 1
    backup        --db PATH DEST [--force]                                 在线快照 + integrity_check + SHA-256 清单
    restore       --db PATH SNAPSHOT [--force]                             校验快照后原子替换库（先停服务；旧库自动另存）
    version                                                                打印版本号

``--db`` 缺省读环境变量 ``LINGSHU_NG_DB``，都没有时 ``serve`` / ``mcp`` 拒绝启动（避免把数据写进进程内存后丢失），
其余子命令报错。退出码：0 成功，2 参数错误，1 运行错误。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

DB_ENV = "LINGSHU_NG_DB"


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="lingshu-ng", description="灵枢记忆引擎 lingshu_ng 命令行")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, help_, db=True):
        p = sub.add_parser(name, help=help_)
        if db:
            p.add_argument("--db", default=os.environ.get(DB_ENV), help=f"SQLite 库文件（缺省读 {DB_ENV}）")
        return p
    p = add("serve", "本机 HTTP/JSON 服务")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--token", default=None, help="Bearer 令牌（缺省读 LINGSHU_NG_TOKEN）；绑非回环地址时必需")
    from .console import add_arguments as _console_args
    _console_args(add("console", "本机 Web 控制台（企业级本地 UI）"), with_db=False)
    add("mcp", "MCP stdio 适配器")
    p = add("perceive", "写入一条")
    p.add_argument("text")
    p.add_argument("--tag", action="append", default=None)
    p = add("recall", "召回")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    add("status", "库状态")
    add("capabilities", "当前生效档位")
    p = add("backup", "在线快照整库（SQLite 备份 API，不停机）")
    p.add_argument("dest")
    p.add_argument("--force", action="store_true", help="覆盖已存在的目标")
    p = add("restore", "从快照恢复（先停服务）")
    p.add_argument("snapshot")
    p.add_argument("--force", action="store_true", help="目标库已存在时覆盖（旧库自动另存为 .pre-restore-时间戳）")
    add("doctor", "只读自检（完整性/schema/磁盘/令牌配置/可选件），失败退出码 1")
    add("version", "版本号", db=False)
    return ap


def _print(obj) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1, default=str) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    """解析参数并执行子命令，返回退出码。"""
    a = _parser().parse_args(argv)
    from ._logfmt import configure_logging
    try:
        configure_logging(sys.stderr)
    except ValueError as e:
        sys.stderr.write(f"lingshu-ng: {e}\n")
        return 2
    if a.cmd == "version":
        from .. import __version__
        _print({"version": __version__})
        return 0
    db = a.db or (":memory:" if a.cmd == "capabilities" else None)
    if not db and a.cmd != "doctor":
        sys.stderr.write(f"需要 --db 或环境变量 {DB_ENV}\n")
        return 2
    if a.cmd == "serve":
        from .http import serve
        try:
            serve(db, a.host, a.port, a.token)
        except PermissionError as e:
            sys.stderr.write(f"{e}\n")
            return 2
        return 0
    if a.cmd == "console":
        from .console import run as run_console
        return run_console(a)
    if a.cmd == "mcp":
        from .mcp import run_stdio
        run_stdio(db)
        return 0
    if a.cmd == "doctor":
        from .doctor import run_doctor
        rep = run_doctor(a.db)
        _print(rep)
        return 0 if rep["ok"] else 1
    if a.cmd in ("backup", "restore"):
        from . import backup as bk
        from .http import audit
        try:
            out = bk.backup(db, a.dest, force=a.force) if a.cmd == "backup" else bk.restore(a.snapshot, db, force=a.force)
        except bk.BackupError as e:
            audit(a.cmd, "cli", 400, error="BackupError")
            sys.stderr.write(f"{e}\n")
            return 1
        audit(a.cmd, "cli", 200, nodes=out["counts"]["nodes"])
        _print(out)
        return 0
    from .service import BadRequest, Service
    svc = Service(db)
    try:
        if a.cmd == "perceive":
            body = {"content": a.text, **({"tags": a.tag} if a.tag else {})}
            out = svc.perceive(body)
            from .mcp import _audit_write
            _audit_write("perceive", "cli", body, out, 200, None)
            _print(out)
        elif a.cmd == "recall":
            _print(svc.recall({"query": a.query, "limit": a.limit}))
        else:
            _print(getattr(svc, a.cmd)(None))
    except (BadRequest, TypeError, ValueError) as e:
        sys.stderr.write(f"{type(e).__name__}: {e}\n")
        return 2
    finally:
        svc.close()
    return 0
