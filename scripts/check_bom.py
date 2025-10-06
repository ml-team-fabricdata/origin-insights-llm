#!/usr/bin/env python3
"""Utility to detect UTF-8 byte-order marks in text files."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Iterable

BOM = "\ufeff"


def iter_targets(paths: list[str]) -> Iterable[Path]:
    if not paths:
        yield Path("requirements.txt")
        return

    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            yield from (candidate for candidate in path.rglob("*") if candidate.is_file())
        else:
            yield path


def scan_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"[error] {path}: could not decode as UTF-8 ({exc})", file=sys.stderr)
        return True

    if BOM in text:
        print(f"[fail] {path}: contains BOM characters")
        return True

    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files or directories to scan. Defaults to requirements.txt")
    args = parser.parse_args(argv)

    failures = 0
    seen: set[Path] = set()
    for target in iter_targets(args.paths):
        if target in seen:
            continue
        seen.add(target)
        failures = scan_file(target)

    if failures:
        print(f"[summary] {failures} file(s) contained BOM characters.")
        return 1

    print("[summary] No BOM characters detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
 
EOF
)
