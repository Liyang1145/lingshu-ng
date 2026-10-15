"""可复现构建校验：同一 SOURCE_DATE_EPOCH 下构建两次，比较 wheel/sdist 的 SHA256。仅标准库（调用 python -m build）。"""
import hashlib, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def normalize_sdist(path, epoch):
    """重打 sdist：成员排序、mtime=epoch、uid/gid=0、gzip 头 mtime=0，使字节稳定。"""
    import gzip, io, tarfile
    path = Path(path)
    with tarfile.open(path, "r:gz") as t:
        items = [(m, t.extractfile(m).read() if m.isfile() else None) for m in t.getmembers()]
    items.sort(key=lambda x: x[0].name)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as t:
        for m, data in items:
            m.mtime, m.uid, m.gid, m.uname, m.gname = epoch, 0, 0, "", ""
            m.mode = 0o755 if m.isdir() else (0o755 if m.mode & 0o100 else 0o644)
            m.pax_headers = {}
            t.addfile(m, io.BytesIO(data) if data is not None else None)
    with open(path, "wb") as f:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0, compresslevel=9) as g:
            g.write(raw.getvalue())


def _build(out, epoch):
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    src = Path(tempfile.mkdtemp()) / "src"
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns(
        ".git", "build", "dist", "*.egg-info", "__pycache__", "*.pyc", ".pytest_cache"))
    subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), str(src)],
                   check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for p in Path(out).glob("*.tar.gz"):
        normalize_sdist(p, epoch)
    return {p.name: _sha(p) for p in sorted(Path(out).iterdir())}


def check(epoch=1700000000):
    a = _build(tempfile.mkdtemp(), epoch)
    b = _build(tempfile.mkdtemp(), epoch)
    return a, b


def main():
    a, b = check()
    for k in sorted(a):
        print(("OK  " if a[k] == b.get(k) else "DIFF"), k, a[k])
    return 0 if a == b and a else 1


if __name__ == "__main__":
    sys.exit(main())
