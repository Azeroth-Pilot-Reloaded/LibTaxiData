#!/usr/bin/env python3
"""Return the current Retail build published by Blizzard's version service."""

from __future__ import annotations

import argparse
import re
import urllib.request


VERSION_URL = "https://us.version.battle.net/wow/versions"
BUILD_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def get_live_build(region: str = "eu") -> str:
    request = urllib.request.Request(
        VERSION_URL,
        headers={"User-Agent": "LibTaxiData build monitor"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8-sig")

    for line in payload.splitlines():
        if not line or line.startswith("#") or line.startswith("Region!"):
            continue
        columns = line.split("|")
        if len(columns) >= 6 and columns[0].lower() == region.lower():
            build = columns[5].strip()
            if BUILD_PATTERN.fullmatch(build):
                return build
            break
    raise RuntimeError(f"No valid Retail build found for region {region!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="eu", help="Retail region (default: eu)")
    args = parser.parse_args()
    print(get_live_build(args.region))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
