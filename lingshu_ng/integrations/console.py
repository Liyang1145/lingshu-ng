# -*- coding: utf-8 -*-
"""ent-ui：本机 Web 控制台（纯标准库，零外部依赖）。

启动::

    lingshu-ng console --db PATH [--host 127.0.0.1] [--port 8766] [--token T] [--audit-log FILE]
    python -m lingshu_ng.integrations.console --db PATH ...

控制台就是 :mod:`lingshu_ng.integrations.http` 的同一个服务，只是额外打开 ``/``、``/console/app.js``、
``/console/app.css`` 三个静态资源（包内 ``console_static/``，经 :mod:`importlib.resources` 读取）。
因此 Host 白名单、Origin 校验、Bearer 令牌、读超时、listen 积压、拒绝 Transfer-Encoding、请求体上限全部原样继承；
另外控制台模式下**所有非 GET 请求**都须带 ``X-Lingshu-Console: 1``（跨站页面带不上自定义头，额外的 CSRF 防护）。
绑非回环地址必须给令牌，否则拒绝启动。安全模型与 API 列表见 ``docs/CONSOLE.md``。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List, Optional

from .http import TOKEN_ENV, TOKEN_FILE_ENV, Server
from .service import Service

_log = logging.getLogger("lingshu_ng.integrations.console")
DEFAULT_PORT = 8766
DB_ENV = "LINGSHU_NG_DB"


class ConsoleServer(Server):
    """打开了控制台页面的 :class:`~lingshu_ng.integrations.http.Server`。"""

    def __init__(self, service: Service, host: str = "127.0.0.1", port: int = DEFAULT_PORT,
                 token: Optional[str] = None):
        super().__init__(service, host, port, token)
        self.console = True


def make_console_server(db: str = ":memory:", host: str = "127.0.0.1", port: int = DEFAULT_PORT,
                        token: Optional[str] = None, service: Optional[Service] = None) -> ConsoleServer:
    """建控制台服务（不启动）。``token`` 缺省读 ``LINGSHU_NG_TOKEN``；``port=0`` 由系统分配端口。"""
    if token is None:
        token = os.environ.get(TOKEN_ENV) or None
    if not token and not os.environ.get(TOKEN_FILE_ENV) and not _loopback(host):
        # 先于打开库拒绝，避免为一次失败的启动建库文件
        raise PermissionError(f"绑定非回环地址 {host} 必须设置令牌（--token 或 {TOKEN_ENV}）")
    return ConsoleServer(service or Service(db), host, port, token)


def _loopback(host: str) -> bool:
    from .http import is_loopback
    return is_loopback(host)


def enable_audit_log(path: Optional[str] = None) -> None:
    """让 ``lingshu_ng.audit`` 的 INFO 行可见：给了 ``path`` 则追加写入该文件（0600 新建），否则走根 logger（stderr）。"""
    lg = logging.getLogger("lingshu_ng.audit")
    lg.setLevel(logging.INFO)
    if path:
        if not os.path.exists(path):
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        h = logging.FileHandler(path, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(message)s"))
        lg.addHandler(h)


def serve_console(db: str, host: str = "127.0.0.1", port: int = DEFAULT_PORT, token: Optional[str] = None) -> None:
    """前台运行控制台直到 Ctrl-C；退出时关闭引擎。"""
    srv = make_console_server(db, host, port, token)
    h, p = srv.server_address[:2]
    shown = f"[{h}]" if ":" in str(h) else h
    sys.stderr.write(f"lingshu-ng 控制台：http://{shown}:{p}/ （鉴权：{'Bearer 令牌，页面内登录' if srv.token else '无，仅本机'}）\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        _log.info("收到中断，停止控制台")
    finally:
        srv.server_close()
        srv.service.close()


def add_arguments(p: argparse.ArgumentParser, with_db: bool = True) -> None:
    """控制台的命令行参数（``lingshu-ng console`` 与 ``python -m lingshu_ng.integrations.console`` 共用）。"""
    if with_db:
        p.add_argument("--db", default=os.environ.get(DB_ENV), help=f"SQLite 库文件（缺省读 {DB_ENV}）")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--token", default=None, help=f"Bearer 令牌（缺省读 {TOKEN_ENV}）；绑非回环地址时必需")
    p.add_argument("--audit-log", default=None, help="审计日志文件（JSON 行；缺省写 stderr）")


def run(a: argparse.Namespace) -> int:
    """按解析好的参数启动；返回退出码（0 正常退出，2 参数 / 安全检查不过）。"""
    if not a.db:
        sys.stderr.write(f"需要 --db 或环境变量 {DB_ENV}\n")
        return 2
    enable_audit_log(a.audit_log)
    try:
        serve_console(a.db, a.host, a.port, a.token)
    except PermissionError as e:
        sys.stderr.write(f"{e}\n")
        return 2
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """``python -m lingshu_ng.integrations.console`` 入口。"""
    ap = argparse.ArgumentParser(prog="lingshu-ng console", description="灵枢 lingshu_ng 本机 Web 控制台")
    add_arguments(ap)
    a = ap.parse_args(argv)
    from ._logfmt import configure_logging
    try:
        configure_logging(sys.stderr)
    except ValueError as e:
        sys.stderr.write(f"lingshu-ng: {e}\n")
        return 2
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
