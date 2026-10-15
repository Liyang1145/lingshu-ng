# -*- coding: utf-8 -*-
"""可选的本机 HTTP/JSON 服务（标准库 ``http.server``，不引入依赖）。

接口（请求体与返回都是 UTF-8 JSON）::

    GET  /v1/status          库状态（版本、schema 版本、各层条数）
    GET  /v1/capabilities    当前生效档位
    POST /v1/perceive        {"content": "...", 可选 tags/entities/importance/confidence/layer/skip_dedup}
    POST /v1/recall          {"query": "...", "limit": 10}
    GET  /healthz            {"ok": true}（不需鉴权，不碰库）

ent-ui 新增（docs/CONSOLE.md）::

    GET    /v1/health                版本、运行时长、请求计数（需鉴权）
    GET    /v1/nodes?layer=&tag=&offset=&limit=   分页列出节点（最新在前）
    GET    /v1/nodes/<id>            节点详情（全文、标签、实体、关联边）
    DELETE /v1/nodes/<id>            删除节点及其关联边（须带 ``X-Lingshu-Console: 1``）
    GET    /v1/export                全库导出 ``{"report", "backup"}``
    POST   /v1/import                ``{"backup": {...}, "confirm": true}``（须带 ``X-Lingshu-Console: 1``；请求体上限 :data:`MAX_IMPORT_BODY`）
    GET    /  /console/app.js  /console/app.css   控制台页面（仅 ``lingshu-ng console`` 启动时提供）

写操作（perceive / delete / import）各记一行 JSON 审计日志到 logger ``lingshu_ng.audit``（不含正文）。
404 节点不存在、409 层规则 / 保护名单拒绝删除。

错误：400 请求不合法（含 JSON 解析失败、未知字段、类型错）、401 缺 / 错令牌、404 未知路径、405 方法不对、
413 请求体超过 :data:`MAX_BODY` 、500 内部错误（记 logging，返回类型名不回显堆栈）。错误体 ``{"error": {"code", "message"}}``。

安全（详见 docs/INTEGRATION_ng.md §2）：
- 缺省只绑 ``127.0.0.1``。绑非回环地址必须同时给令牌（``--token`` 或环境变量 ``LINGSHU_NG_TOKEN``），否则拒绝启动。
- 设了令牌后，除 ``/healthz`` 外每个请求须带 ``Authorization: Bearer <令牌>``（常数时间比较）。
- 不做 TLS、不做多用户；要对外暴露请放在反向代理（TLS + 访问控制）之后。
- sec-r1：只绑回环时只认回环 ``Host``（挡 DNS 重绑定，403）；无令牌时带非回环 ``Origin`` 的请求一律 403（挡跨站写入）；
  每连接读超时 :data:`REQUEST_TIMEOUT` 秒（挡慢速连接）；``Transfer-Encoding`` 不支持（501，挡请求脱同步）；
  深嵌套 JSON 记 400。
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import logging
import os
import re
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, unquote, urlsplit

from .service import BadRequest, Conflict, NotFound, Service

_log = logging.getLogger("lingshu_ng.integrations.http")
#: 请求体上限（字节）
MAX_BODY = 1 << 20
#: 超限请求体在回 413 之前最多读掉（丢弃）这么多字节，客户端才能读到 413 而不是写到一半被断开（Broken pipe）；更大的直接断开
_DRAIN_CAP = 4 * MAX_BODY
TOKEN_ENV = "LINGSHU_NG_TOKEN"
#: E5-3：令牌文件（每行一个有效令牌，# 开头为注释）；按 mtime 变化自动重读，新旧令牌可并存过渡，轮换无需重启
TOKEN_FILE_ENV = "LINGSHU_NG_TOKEN_FILE"
#: E5-1：同时处理的连接上限（满则直接回 503 + Retry-After，不再开线程）；环境变量 LINGSHU_NG_MAX_CONN 覆盖
MAX_CONN_ENV = "LINGSHU_NG_MAX_CONN"
DEFAULT_MAX_CONN = 64
#: 每连接读超时（秒）：请求行 / 头 / 正文迟迟不到就断开，慢速连接不会无限占住线程（sec-r1）
REQUEST_TIMEOUT = 30.0
_GET = {"/v1/status": "status", "/v1/capabilities": "capabilities", "/v1/nodes": "list_nodes",
        "/v1/export": "export_backup"}
_POST = {"/v1/perceive": "perceive", "/v1/recall": "recall", "/v1/import": "import_backup"}
#: ent-ui：导入请求体上限（字节；整份备份走一次请求，比普通请求宽）
MAX_IMPORT_BODY = 32 << 20
#: ent-ui：额外的 CSRF 防护头。浏览器跨站请求带自定义头必须先过 CORS 预检，本服务不应答预检（501），跨站页面就发不出
CONSOLE_HEADER = "X-Lingshu-Console"
#: 任何模式下都要求 :data:`CONSOLE_HEADER` 的破坏性操作；控制台模式下所有非 GET 请求都要求
_DESTRUCTIVE = {"delete_node", "import_backup"}
#: 记审计日志的写操作
_AUDITED = {"perceive", "delete_node", "import_backup"}
_NODE_PATH = re.compile(r"^/v1/nodes/([^/]+)$")
_INT = re.compile(r"^-?[0-9]{1,12}$")
#: 请求计数的「最近」窗口（秒）
RECENT_WINDOW = 300.0
_audit = logging.getLogger("lingshu_ng.audit")
#: 控制台静态资源：URL → (包内文件, Content-Type)
_STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
           "/console": ("index.html", "text/html; charset=utf-8"),
           "/console/app.js": ("app.js", "text/javascript; charset=utf-8"),
           "/console/app.css": ("app.css", "text/css; charset=utf-8")}
#: 控制台页面的内容安全策略：只许同源脚本 / 样式 / 连接，禁内联脚本、禁被嵌入
CONSOLE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
               "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
#: JSON 响应的内容安全策略（API 响应不该被当页面渲染）
API_CSP = "default-src 'none'; frame-ancestors 'none'"


def _static_bytes(name: str) -> bytes:
    from importlib import resources
    return resources.files("lingshu_ng.integrations").joinpath("console_static", name).read_bytes()


def audit(op: str, remote: str, status: int, **fields) -> None:
    """写一行 JSON 审计日志（logger ``lingshu_ng.audit``，INFO）。调用方保证 ``fields`` 不含记忆正文。"""
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "op": op, "remote": remote, "status": status}
    rec.update(fields)
    _audit.info(json.dumps(rec, ensure_ascii=False, sort_keys=True, default=str))


def _audit_fields(op: str, body, out) -> dict:
    """审计字段：只取 id / 动作 / 计数，绝不取正文。"""
    if op == "perceive":
        f = {"node_id": out.get("node_id"), "action": out.get("action"), "layer": out.get("layer")} if out else {}
        if isinstance(body, dict):
            f["tags_n"] = len(body["tags"]) if isinstance(body.get("tags"), list) else 0
            f["content_chars"] = len(body["content"]) if isinstance(body.get("content"), str) else None
        return f
    if op == "delete_node":
        f = {"node_id": body.get("id") if isinstance(body, dict) and isinstance(body.get("id"), str) else None}
        if out:
            f["edges_removed"] = out.get("edges_removed")
        return f
    if op == "import_backup" and out:
        rej = out.get("rejected_rows") or {}
        return {"imported": out.get("imported"), "overwritten": out.get("overwritten") or {}, "rejected_rows_n": sum(len(v) if isinstance(v, (list, dict)) else int(v or 0)
                                                                         for v in rej.values()),
                "quarantined": {k: (len(v) if isinstance(v, (list, dict)) else v)
                                for k, v in (out.get("quarantined") or {}).items()}}
    return {}


def is_loopback(host: str) -> bool:
    """``host`` 是否回环地址（``localhost`` 视为回环）。"""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _host_of(value: str) -> str:
    """``Host`` 头 / ``Origin`` 里的主机名（去端口、去 IPv6 方括号）；解析不了返回空串。"""
    try:
        return (urlsplit("//" + value.strip()).hostname or "").lower()
    except ValueError:
        return ""


class _Handler(BaseHTTPRequestHandler):
    server_version = "lingshu-ng"
    protocol_version = "HTTP/1.1"
    timeout = REQUEST_TIMEOUT

    def log_message(self, fmt, *args):  # 走 logging，不写 stderr
        _log.debug("%s " + fmt, self.address_string(), *args)

    def _send(self, code: int, obj) -> None:
        data = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._security_headers(API_CSP)
        self.end_headers()
        self.wfile.write(data)

    def _security_headers(self, csp: str) -> None:
        self.send_header("Content-Security-Policy", csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")

    def _static(self, path: str) -> None:
        name, ctype = _STATIC[path]
        try:
            data = _static_bytes(name)
        except (OSError, ModuleNotFoundError):
            _log.exception("控制台资源 %s 缺失", name)
            return self._err(500, "控制台资源缺失（安装包不完整）")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._security_headers(CONSOLE_CSP)
        self.end_headers()
        self.wfile.write(data)

    def _tick(self) -> None:
        tick = getattr(self.server, "_count_request", None)
        if tick is not None:
            tick()

    def _csrf_ok(self, op: str) -> bool:
        """ent-ui：破坏性操作（任何模式）与控制台模式下的所有非 GET 请求须带 ``X-Lingshu-Console: 1``。"""
        need = op in _DESTRUCTIVE or (getattr(self.server, "console", False) and self.command != "GET")
        if need and self.headers.get(CONSOLE_HEADER, "").strip() != "1":
            self._err(403, f"写操作须带请求头 {CONSOLE_HEADER}: 1（CSRF 防护）")
            return False
        return True

    def _health(self) -> None:
        h = getattr(self.server, "_health_info", None)
        return self._send(200, h() if h else {"ok": True})

    def _err(self, code: int, msg: str) -> None:
        self._send(code, {"error": {"code": code, "message": msg}})

    def _authorized(self) -> bool:
        tokens = self.server.valid_tokens()
        if not tokens:
            if self.server.token_file:            # 配了令牌文件却读出空集：失败关闭，不退化为无鉴权
                self._err(401, "令牌文件为空或不可读，拒绝所有请求")
                return False
            return True
        got = self.headers.get("Authorization", "")
        scheme, _, cred = got.partition(" ")   # RFC 7235：认证方案名大小写不敏感（sec-r2 O8）
        c = cred.strip().encode()
        ok = False
        for t in tokens:                       # 逐个常数时间比较，不提前退出
            ok |= hmac.compare_digest(c, t.encode())
        ok = ok and scheme.lower() == "bearer"
        if not ok:
            self._err(401, "缺少或错误的 Authorization: Bearer 令牌")
        return ok

    def _guard(self) -> bool:
        """sec-r1：Host / Origin / Transfer-Encoding 检查；不通过时已回错误，返回 False。"""
        if self.headers.get("Transfer-Encoding"):
            self.close_connection = True
            self._err(501, "不支持 Transfer-Encoding，请用 Content-Length")
            return False
        if self.server.loopback_only and not is_loopback(_host_of(self.headers.get("Host", ""))):
            self._err(403, "Host 不是回环地址（服务只绑本机）")
            return False
        origin = self.headers.get("Origin")
        if origin is not None and not self.server.token:
            o = urlsplit(origin.strip())
            if o.scheme not in ("http", "https") or not is_loopback((o.hostname or "").lower()):
                self._err(403, "拒绝跨站请求（Origin 非本机）；需要跨站访问请设置令牌")
                return False
        return True

    def _body(self, cap: int = MAX_BODY):
        n = int(self.headers.get("Content-Length") or 0)
        if n < 0:
            raise ValueError("Content-Length 为负")
        if n > cap:
            raise OverflowError(n)
        raw = self.rfile.read(n) if n > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _drain(self, n: int) -> None:
        """丢弃超限请求体（split-r3）：服务端不读就回 413 并关连接时，仍在发送的客户端会撞上 Broken pipe、读不到 413。

        只在 ``n <= _DRAIN_CAP`` 时读掉，分块读、不留内容；更大的请求体不读（直接关连接，避免被大包拖住）。"""
        if n > _DRAIN_CAP:
            return
        left = n
        while left > 0:
            chunk = self.rfile.read(min(left, 1 << 16))
            if not chunk:
                break
            left -= len(chunk)

    def _run(self, op: str, body) -> None:
        if not self._csrf_ok(op):
            if op in _AUDITED:
                self._audit(op, body, None, 403, "csrf")
            return None
        try:
            out = getattr(self.server.service, op)(body)
        except NotFound as e:
            code, msg, out = 404, f"{type(e).__name__}: {e}", None
        except Conflict as e:
            code, msg, out = 409, f"{type(e).__name__}: {e}", None
        except (BadRequest, TypeError, ValueError) as e:
            code, msg, out = 400, f"{type(e).__name__}: {e}", None
        except Exception as e:
            _log.exception("请求 %s 内部错误", op)
            code, msg, out = 500, f"内部错误 {type(e).__name__}（详情见服务端日志）", None
        else:
            code, msg = 200, ""
        if op in _AUDITED:
            self._audit(op, body, out, code, msg.split(":", 1)[0] if msg else None)
        if code != 200:
            return self._err(code, msg)
        self._send(200, out)

    def _audit(self, op, body, out, code, error) -> None:
        try:
            f = _audit_fields(op, body, out)
            if error:
                f["error"] = error
            audit(op, self.client_address[0] if self.client_address else "", code, **f)
        except Exception:  # 审计失败不影响请求
            _log.exception("审计日志写入失败")

    def _query(self) -> dict:
        """查询串 → dict（每个参数只许出现一次；纯数字转 int）。"""
        q = self.path.split("?", 1)[1] if "?" in self.path else ""
        try:
            raw = parse_qs(q, keep_blank_values=True, strict_parsing=bool(q), max_num_fields=16)
        except ValueError as e:
            raise BadRequest(f"查询串不合法：{e}") from None
        out = {}
        for k, v in raw.items():
            if len(v) != 1:
                raise BadRequest(f"查询参数 {k} 重复")
            out[k] = int(v[0]) if _INT.match(v[0]) else v[0]
        return out

    def do_GET(self):  # noqa: N802
        """GET 路由。"""
        self._tick()
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            return self._send(200, {"ok": True})
        if getattr(self.server, "console", False) and path in _STATIC:
            if not self._guard():          # 页面本身不含数据，不要求令牌（登录在页面里做），但同样挡外来 Host / Origin
                return None
            return self._static(path)
        if not self._guard() or not self._authorized():
            return None
        if path == "/v1/health":
            return self._health()
        m = _NODE_PATH.match(path)
        if m:
            return self._run("get_node", {"id": unquote(m.group(1))})
        if path in _POST:
            return self._err(405, "该路径只接受 POST")
        if path not in _GET:
            return self._err(404, f"未知路径 {path}")
        if _GET[path] == "list_nodes":
            try:
                return self._run("list_nodes", self._query())
            except BadRequest as e:
                return self._err(400, f"BadRequest: {e}")
        if "?" in self.path:
            return self._err(400, f"{path} 不接受查询参数")
        return self._run(_GET[path], None)

    def do_DELETE(self):  # noqa: N802
        """DELETE 路由（ent-ui）：``DELETE /v1/nodes/<id>``。"""
        self._tick()
        path = self.path.split("?", 1)[0]
        if not self._guard() or not self._authorized():
            return None
        m = _NODE_PATH.match(path)
        if not m:
            return self._err(404 if path not in _GET and path not in _POST else 405, f"路径 {path} 不接受 DELETE")
        try:
            self._body()                 # 读掉（并丢弃）可能附带的请求体，保持连接同步
        except OverflowError as e:
            self.close_connection = True
            self._drain(e.args[0])
            return self._err(413, f"请求体超过 {MAX_BODY} 字节")
        except (ValueError, UnicodeDecodeError, RecursionError):
            pass
        return self._run("delete_node", {"id": unquote(m.group(1))})

    def do_POST(self):  # noqa: N802
        """POST 路由。"""
        self._tick()
        path = self.path.split("?", 1)[0]
        if not self._guard() or not self._authorized():
            return None
        if path in _GET or _NODE_PATH.match(path) or path == "/v1/health":
            return self._err(405, "该路径不接受 POST")
        if path not in _POST:
            return self._err(404, f"未知路径 {path}")
        cap = MAX_IMPORT_BODY if path == "/v1/import" else MAX_BODY
        try:
            body = self._body(cap)
        except OverflowError as e:
            self.close_connection = True
            self._drain(e.args[0])
            return self._err(413, f"请求体超过 {cap} 字节")
        except (ValueError, UnicodeDecodeError) as e:
            return self._err(400, f"JSON 解析失败：{e}")
        except RecursionError:
            return self._err(400, "JSON 解析失败：嵌套过深")
        return self._run(_POST[path], body)


class Server(ThreadingHTTPServer):
    """持有 :class:`Service` 与令牌的 HTTP 服务。"""
    daemon_threads = True

    def __init__(self, service: Service, host: str = "127.0.0.1", port: int = 8765, token: Optional[str] = None):
        self.token_file = os.environ.get(TOKEN_FILE_ENV) or None
        self._tok_lock, self._tok_mtime, self._file_tokens = threading.Lock(), None, ()
        self._explicit_token = token or None
        if self.token_file:
            self._reload_tokens(force=True)
        if not is_loopback(host) and not (token or self._file_tokens):
            raise PermissionError(f"绑定非回环地址 {host} 必须设置令牌（--token、{TOKEN_ENV} 或 {TOKEN_FILE_ENV}）")
        self.service = service
        self.token = token or (self._file_tokens[0] if self._file_tokens else None) or (self.token_file and "<file>")
        try:
            self.max_conn = max(1, int(os.environ.get(MAX_CONN_ENV) or DEFAULT_MAX_CONN))
        except ValueError:
            raise ValueError(f"{MAX_CONN_ENV} 必须是正整数") from None
        self._conn_sem = threading.BoundedSemaphore(self.max_conn)
        self.rejected_busy = 0
        self.loopback_only = is_loopback(host)
        self.request_queue_size = 128   # listen 积压（socketserver 缺省 5，突发并发下被内核 RST；sec-r1）
        # ent-ui：控制台开关与请求计数（实例属性，不扩大公开 API 快照）
        self.console = False
        self.started_at, self._t0 = time.time(), time.monotonic()
        self.requests_total, self._recent, self._stat_lock = 0, deque(maxlen=100_000), threading.Lock()
        super().__init__((host, port), _Handler)

    # ------------------------------------------------------------ E5-3 令牌文件
    def _reload_tokens(self, force: bool = False) -> None:
        try:
            m = os.stat(self.token_file).st_mtime_ns
        except OSError:
            if force:
                raise PermissionError(f"{TOKEN_FILE_ENV}={self.token_file!r} 不可读") from None
            _log.warning("令牌文件 %s 不可读，沿用上次加载的令牌", self.token_file)
            return
        if not force and m == self._tok_mtime:
            return
        try:
            with open(self.token_file, encoding="utf-8") as f:
                toks = tuple(x.strip() for x in f if x.strip() and not x.lstrip().startswith("#"))
        except (OSError, UnicodeDecodeError):
            _log.warning("令牌文件 %s 读取失败，沿用上次加载的令牌", self.token_file, exc_info=True)
            return
        self._file_tokens, self._tok_mtime = toks, m
        _log.info("已加载令牌文件：%d 个有效令牌", len(toks))

    def valid_tokens(self) -> tuple:
        """当前有效令牌：显式令牌（--token / 环境变量）+ 令牌文件里的全部（文件变动即时生效）。"""
        if self.token_file:
            with self._tok_lock:
                self._reload_tokens()
            return tuple(t for t in ((self._explicit_token,) if self._explicit_token else ()) + self._file_tokens)
        return (self.token,) if self.token else ()

    # ------------------------------------------------------------ E5-1 并发连接上限
    def process_request(self, request, client_address):
        """连接数满时不开线程，直接回 503（Retry-After: 1）并关闭。"""
        if not self._conn_sem.acquire(blocking=False):
            self.rejected_busy += 1
            try:
                body = json.dumps({"error": {"code": 503, "message": f"服务繁忙：并发连接已达上限 {self.max_conn}"}},
                                  ensure_ascii=False).encode("utf-8")
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json; charset=utf-8\r\n"
                                b"Retry-After: 1\r\nConnection: close\r\nContent-Length: " + str(len(body)).encode()
                                + b"\r\n\r\n" + body)
            except OSError:
                _log.debug("回 503 时连接已断", exc_info=True)
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._conn_sem.release()
            raise

    def process_request_thread(self, request, client_address):
        """处理完一个连接后释放并发名额。"""
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._conn_sem.release()

    def _count_request(self) -> None:
        """计一次请求（ent-ui 健康页用）。"""
        t = time.monotonic()
        with self._stat_lock:
            self.requests_total += 1
            self._recent.append(t)

    def _health_info(self) -> dict:
        """``/v1/health``：版本、运行时长、请求计数（总数 / 最近 :data:`RECENT_WINDOW` 秒）。"""
        from .. import __version__
        t = time.monotonic()
        with self._stat_lock:
            while self._recent and self._recent[0] < t - RECENT_WINDOW:
                self._recent.popleft()
            recent, total = len(self._recent), self.requests_total
        return {"ok": True, "version": __version__, "started_at": self.started_at,
                "uptime_s": round(t - self._t0, 3), "requests_total": total,
                "requests_recent": recent, "recent_window_s": RECENT_WINDOW, "console": bool(self.console),
                "auth": "token" if self.token else "loopback-only", "max_conn": self.max_conn,
                "rejected_busy": self.rejected_busy}


def make_server(db: str = ":memory:", host: str = "127.0.0.1", port: int = 8765,
                token: Optional[str] = None, service: Optional[Service] = None) -> Server:
    """建服务（不启动）。``token`` 缺省读环境变量 ``LINGSHU_NG_TOKEN``；``port=0`` 由系统分配端口。"""
    if token is None:
        token = os.environ.get(TOKEN_ENV) or None
    return Server(service or Service(db), host, port, token)


def serve(db: str, host: str = "127.0.0.1", port: int = 8765, token: Optional[str] = None) -> None:
    """前台运行直到 Ctrl-C；退出时关闭引擎。"""
    srv = make_server(db, host, port, token)
    h, p = srv.server_address[:2]
    _log.warning("lingshu-ng HTTP 服务：http://%s:%s（鉴权：%s）", h, p, "Bearer 令牌" if srv.token else "无，仅本机")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        _log.info("收到中断，停止服务")
    finally:
        srv.server_close()
        srv.service.close()
