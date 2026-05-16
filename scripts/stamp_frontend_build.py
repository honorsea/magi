#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = ROOT / "frontend" / "src"
TARGETS = [ROOT / "frontend" / "index.html", ROOT / "meta" / "static" / "index.html"]
META_TAG_START = '<meta name="magi-build-hash" content="'


def compute_src_hash() -> str:
    h = hashlib.sha256()
    for path in sorted(FRONTEND_SRC.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix().encode("utf-8")
        h.update(rel)
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:12]


def stamp_file(path: Path, build_hash: str) -> None:
    html = path.read_text(encoding="utf-8")
    if META_TAG_START in html:
        before, rest = html.split(META_TAG_START, 1)
        _, after = rest.split('"', 1)
        html = f"{before}{META_TAG_START}{build_hash}\"{after}"
    else:
        html = html.replace("</head>", f'    <meta name="magi-build-hash" content="{build_hash}" />\n  </head>')
    path.write_text(html, encoding="utf-8")


def main() -> None:
    build_hash = compute_src_hash()
    for target in TARGETS:
        stamp_file(target, build_hash)
    print(build_hash)


if __name__ == "__main__":
    main()
