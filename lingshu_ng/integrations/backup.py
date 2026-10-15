# -*- coding: utf-8 -*-
"""库文件级在线备份 / 恢复（纯标准库 sqlite3）。

与 ``/v1/export``（JSON 逻辑备份，可跨版本迁移）不同，这里做的是**物理快照**：

* ``backup(src, dest)``：用 SQLite 在线备份 API 拷贝整库（服务在跑、WAL 模式下也安全，
  不需要停机），随后对快照跑 ``PRAGMA integrity_check``，计算 SHA-256，写旁车清单
  ``<dest>.manifest.json``（版本、表行数、校验和）。
* ``restore(src, dest)``：先校验快照（integrity_check、灵枢表结构、清单校验和若存在），
  再拷到 ``dest`` 同目录的临时文件并 ``os.replace`` 原子替换。``dest`` 已存在时须 ``force=True``，
  且旧库先被另存为 ``<dest>.pre-restore-<时间戳>``，恢复本身可回退。

恢复时目标库**不得**被服务进程占用（先停服务）：旧库连同 ``-wal`` 里未合并的内容会先经备份 API
完整另存，再删除旧的 ``-wal`` / ``-shm`` 并替换主文件。
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Dict, Optional

MANIFEST_SUFFIX = ".manifest.json"
_REQUIRED_TABLES = ("nodes", "edges", "engine_meta")


class BackupError(RuntimeError):
    """备份或恢复无法安全完成。"""


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _check(path: str) -> Dict[str, int]:
    """只读打开 ``path``：integrity_check 须为 ok、须含灵枢核心表；返回核心表行数。"""
    if not os.path.isfile(path):
        raise BackupError(f"文件不存在：{path}")
    uri = "file:" + os.path.abspath(path).replace("?", "%3f").replace("#", "%23") + "?mode=ro"
    try:
        c = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as e:
        raise BackupError(f"无法打开 {path}：{e}") from e
    try:
        try:
            res = [r[0] for r in c.execute("PRAGMA integrity_check").fetchall()]
        except sqlite3.DatabaseError as e:
            raise BackupError(f"{path} 不是有效的 SQLite 库：{e}") from e
        if res != ["ok"]:
            raise BackupError(f"{path} 完整性检查失败：{'; '.join(res[:5])}")
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in _REQUIRED_TABLES if t not in names]
        if missing:
            raise BackupError(f"{path} 不是灵枢库（缺表：{', '.join(missing)}）")
        return {t: int(c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in ("nodes", "edges")}
    finally:
        c.close()


def _copy(src: str, dest: str) -> None:
    """SQLite 在线备份 API：src（可正被别的连接写）→ dest（新文件，回卷日志模式，单文件自包含）。"""
    s = sqlite3.connect(src)
    try:
        d = sqlite3.connect(dest)
        try:
            s.backup(d, pages=1024)
            d.execute("PRAGMA journal_mode=DELETE")
            d.commit()
        finally:
            d.close()
    finally:
        s.close()


def backup(src: str, dest: str, *, force: bool = False) -> Dict[str, object]:
    """在线快照 ``src`` → ``dest``，校验并写清单；返回清单内容。"""
    _check(src)
    if os.path.abspath(src) == os.path.abspath(dest):
        raise BackupError("备份目标不能是源库本身")
    if os.path.exists(dest) and not force:
        raise BackupError(f"目标已存在：{dest}（覆盖须 --force）")
    tmp = f"{dest}.tmp-{os.getpid()}"
    try:
        _copy(src, tmp)
        counts = _check(tmp)
        os.replace(tmp, dest)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    from .. import __version__
    man = {"format": "lingshu-ng-sqlite-snapshot/1", "lingshu_ng_version": __version__,
           "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sha256": _sha256(dest), "bytes": os.path.getsize(dest), "counts": counts,
           "integrity_check": "ok"}
    with open(dest + MANIFEST_SUFFIX, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    return {"backup": dest, **man}


def restore(src: str, dest: str, *, force: bool = False) -> Dict[str, object]:
    """校验快照 ``src`` 后原子替换 ``dest``；旧库另存为 ``<dest>.pre-restore-<时间戳>``。"""
    counts = _check(src)
    mpath = src + MANIFEST_SUFFIX
    verified_sha = False
    if os.path.isfile(mpath):
        with open(mpath, encoding="utf-8") as f:
            man = json.load(f)
        if man.get("sha256") != _sha256(src):
            raise BackupError(f"快照校验和与清单不符（{mpath}）：文件被改动或损坏")
        verified_sha = True
    if os.path.abspath(src) == os.path.abspath(dest):
        raise BackupError("恢复源不能是目标库本身")
    previous: Optional[str] = None
    if os.path.exists(dest):
        if not force:
            raise BackupError(f"目标库已存在：{dest}（先停服务，再用 --force 覆盖；旧库会自动另存）")
        previous = f"{dest}.pre-restore-{time.strftime('%Y%m%d-%H%M%S')}"
        _copy(dest, previous)
    tmp = f"{dest}.tmp-{os.getpid()}"
    try:
        _copy(src, tmp)
        _check(tmp)
        for side in ("-wal", "-shm"):
            if os.path.exists(dest + side):
                os.remove(dest + side)
        os.replace(tmp, dest)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return {"restored": dest, "from": src, "counts": counts, "sha256_verified": verified_sha,
            "previous_saved_as": previous}
