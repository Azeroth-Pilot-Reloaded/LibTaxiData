#!/usr/bin/env python3
"""Hash generated taxi content while ignoring build-provenance-only lines."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def generated_paths(profile: str | None = None, root: Path = ROOT) -> list[Path]:
    data_root = root / "Data" / profile if profile else root / "Data"
    locale_root = root / "Locale" / profile if profile else root / "Locale"
    paths = sorted(data_root.rglob("*.lua")) + sorted(locale_root.rglob("*.lua"))
    return [path for path in paths if path.name != "ClientProfiles.lua"]


def semantic_content(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("-- Source:") and "(build " in line:
            continue
        if path.name == "TaxiNodes.lua" and line.lstrip().startswith("build = "):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def fingerprint(profile: str | None = None, root: Path = ROOT) -> str:
    digest = hashlib.sha256()
    paths = generated_paths(profile, root)
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(semantic_content(path).encode())
        digest.update(b"\0")

    # The full build is part of runtime profile selection, so even a build-only
    # update must publish a new manifest when DB2 rows are otherwise identical.
    for path in paths:
        if path.name != "TaxiNodes.lua":
            continue
        match = re.search(
            r'^\s*build = "(\d+\.\d+\.\d+\.\d+)"',
            path.read_text(encoding="utf-8-sig"),
            flags=re.MULTILINE,
        )
        if match:
            digest.update(match.group(1).encode())
    return digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Fingerprint only one generated profile")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root to fingerprint (defaults to the current checkout)",
    )
    args = parser.parse_args()
    print(fingerprint(args.profile, args.root.resolve()))
