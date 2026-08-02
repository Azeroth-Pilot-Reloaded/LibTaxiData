#!/usr/bin/env python3
"""Hash generated taxi content while ignoring build-provenance-only lines."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def generated_paths() -> list[Path]:
    return sorted((ROOT / "Data").glob("*.lua")) + sorted((ROOT / "Locale").glob("*.lua"))


def semantic_content(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("-- Source:") and "(build " in line:
            continue
        if path.name == "TaxiNodes.lua" and line.lstrip().startswith("build = "):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def fingerprint() -> str:
    digest = hashlib.sha256()
    for path in generated_paths():
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(semantic_content(path).encode())
        digest.update(b"\0")

    # A new Retail interface must still create a release even when the DB2 rows
    # themselves are unchanged.
    toc = ROOT / "LibTaxiData.toc"
    interface = next(
        line for line in toc.read_text(encoding="utf-8-sig").splitlines()
        if line.startswith("## Interface:")
    )
    digest.update(interface.encode())
    return digest.hexdigest()


if __name__ == "__main__":
    print(fingerprint())
