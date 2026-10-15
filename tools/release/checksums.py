#!/usr/bin/env python3
"""发布产物 SHA256 校验和（纯标准库，E6-1）。

  python tools/release/checksums.py dist/*            # 打印 SHA256SUMS 格式
  python tools/release/checksums.py --markdown dist/* # 打印 Release 说明用的 Markdown 表
  python tools/release/checksums.py --check SHA256SUMS # 校验（与 sha256sum -c 同格式），不一致返回 1
"""
import argparse
import hashlib
import pathlib
import sys


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compute(paths):
    return [(pathlib.Path(p).name, _sha256(p), pathlib.Path(p).stat().st_size)
            for p in paths if pathlib.Path(p).is_file()]


def sha256sums(rows):
    return "".join(f"{h}  {n}\n" for n, h, _ in rows)


def markdown(rows):
    lines = ["| 文件 | 大小（字节） | SHA256 |", "|---|---:|---|"]
    lines += [f"| `{n}` | {s} | `{h}` |" for n, h, s in rows]
    return "\n".join(lines) + "\n"


def verify(sums_file):
    sums_file = pathlib.Path(sums_file)
    bad = 0
    for line in sums_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        h, _, name = line.partition("  ")
        p = sums_file.parent / name.lstrip("*")
        ok = p.is_file() and _sha256(p) == h.strip().lower()
        print(f"{name}: {'OK' if ok else 'FAILED'}")
        bad += not ok
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--check", metavar="SHA256SUMS")
    a = ap.parse_args(argv)
    if a.check:
        return verify(a.check)
    rows = compute(sorted(a.files))
    sys.stdout.write(markdown(rows) if a.markdown else sha256sums(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
