#!/usr/bin/env python3
"""Return a current WoW product build from Blizzard's version service."""

from __future__ import annotations

import argparse
import re
import urllib.request


VERSION_URL = "https://us.version.battle.net/{product}/versions"
BUILD_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
PRODUCT_PATTERN = re.compile(r"^[a-z0-9_]+$")


def get_product_build(product: str = "wow", region: str = "eu") -> str:
    if not PRODUCT_PATTERN.fullmatch(product):
        raise ValueError(f"Invalid Blizzard product: {product!r}")
    request = urllib.request.Request(
        VERSION_URL.format(product=product),
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
    raise RuntimeError(
        f"No valid build found for Blizzard product {product!r} in region {region!r}"
    )


def get_live_build(region: str = "eu") -> str:
    """Backward-compatible alias for the Retail live product."""
    return get_product_build("wow", region)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", default="wow", help="Blizzard product code (default: wow)")
    parser.add_argument("--region", default="eu", help="Blizzard region (default: eu)")
    args = parser.parse_args()
    print(get_product_build(args.product, args.region))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
