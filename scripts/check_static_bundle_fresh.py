#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from stamp_frontend_build import compute_src_hash

ROOT = Path(__file__).resolve().parent.parent
STATIC_INDEX = ROOT / "meta" / "static" / "index.html"
PATTERN = re.compile(r'<meta\s+name="magi-build-hash"\s+content="([^"]+)"')


def main() -> int:
    expected = compute_src_hash()
    html = STATIC_INDEX.read_text(encoding="utf-8")
    match = PATTERN.search(html)
    if not match:
        print("ERROR: meta/static/index.html has no magi-build-hash stamp")
        return 1
    actual = match.group(1)
    if actual != expected:
        print(f"ERROR: stale static bundle hash {actual}; expected {expected}")
        print("Run: python scripts/stamp_frontend_build.py && cd frontend && npm run build")
        return 1
    print(f"OK: static bundle matches frontend/src hash {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
