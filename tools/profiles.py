#!/usr/bin/env python3
"""List, validate, or synchronize LibTaxiData client profiles."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from profile_catalog import (
        ROOT,
        catalog_errors,
        generate_client_profiles,
        load_profiles,
        load_versions,
        prune_profile_directories,
        release_type_for_profile,
        update_toc,
    )
except ModuleNotFoundError:  # Imported as tools.profiles by tests.
    from tools.profile_catalog import (
        ROOT,
        catalog_errors,
        generate_client_profiles,
        load_profiles,
        load_versions,
        prune_profile_directories,
        release_type_for_profile,
        update_toc,
    )


def print_versions(
    versions: list[dict[str, object]], profiles: list[dict[str, object]]
) -> None:
    profile_ids: dict[str, list[str]] = {}
    for profile in profiles:
        profile_ids.setdefault(str(profile["version"]), []).append(str(profile["id"]))
    rows = []
    for version in versions:
        interface_rule = version.get("interfaceMajor")
        if interface_rule is None:
            interface_rule = f">={version['minimumInterfaceMajor']}"
        rows.append(
            {
                "id": str(version["id"]),
                "name": str(version["name"]),
                "gameType": str(version["gameType"]),
                "projectConstant": str(version["projectConstant"]),
                "apiFamily": str(version["apiFamily"]),
                "interface": str(interface_rule),
                "tocInterface": str(version["tocInterface"]),
                "profiles": ",".join(profile_ids.get(str(version["id"]), [])) or "-",
            }
        )
    columns = (
        "id",
        "name",
        "gameType",
        "apiFamily",
        "interface",
        "tocInterface",
        "profiles",
        "projectConstant",
    )
    headers = {
        "id": "BASE",
        "name": "BASE VERSION",
        "gameType": "GAME TYPE",
        "apiFamily": "API",
        "interface": "INTERFACE",
        "tocInterface": "TOC",
        "profiles": "SERVER PROFILES",
        "projectConstant": "PROJECT CONSTANT",
    }
    widths = {
        column: max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in columns
    }
    print("  ".join(headers[column].ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print("  ".join(row[column].ljust(widths[column]) for column in columns))


def print_profiles(profiles: list[dict[str, object]]) -> None:
    columns = (
        "id",
        "name",
        "version",
        "gameType",
        "channel",
        "product",
        "build",
        "releaseBase",
        "dataSet",
        "publishAs",
    )
    by_id = {str(profile["id"]): profile for profile in profiles}
    rows = [
        {
            **{column: str(profile.get(column) or "-") for column in columns},
            "publishAs": release_type_for_profile(profile, by_id) or "-",
            "default": "yes" if profile.get("default") else "",
        }
        for profile in profiles
    ]
    headers = {
        "id": "PROFILE",
        "name": "VERSION",
        "version": "BASE",
        "gameType": "GAME TYPE",
        "channel": "CHANNEL",
        "product": "PRODUCT",
        "build": "BUILD",
        "releaseBase": "RELEASE BASE",
        "dataSet": "DATA SET",
        "publishAs": "PUBLISH AS",
        "default": "DEFAULT",
    }
    order = (*columns, "default")
    widths = {
        column: max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in order
    }
    print("  ".join(headers[column].ljust(widths[column]) for column in order))
    print("  ".join("-" * widths[column] for column in order))
    for row in rows:
        print("  ".join(row[column].ljust(widths[column]) for column in order))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root (defaults to the parent of tools/)",
    )
    operations = parser.add_subparsers(dest="operation", required=True)
    operations.add_parser(
        "list", help="List base versions and configured server profiles"
    )
    operations.add_parser("check", help="Check catalog and generated files")
    sync = operations.add_parser(
        "sync", help="Regenerate the runtime manifest and TOC"
    )
    sync.add_argument(
        "--prune",
        action="store_true",
        help="Delete Data/Locale directories absent from the catalog",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    versions = load_versions(root / "tools" / "versions.json")
    profiles = load_profiles(
        root / "tools" / "profiles.json",
        root / "tools" / "versions.json",
    )
    if args.operation == "list":
        print_versions(versions, profiles)
        print()
        print_profiles(profiles)
        return 0
    if args.operation == "check":
        errors = catalog_errors(root, profiles, versions)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print(
            f"Catalog is synchronized ({len(versions)} base versions, "
            f"{len(profiles)} server profiles)."
        )
        return 0

    if args.prune:
        for path in prune_profile_directories(root, profiles):
            print(f"Removed {path.relative_to(root)}")
    generate_client_profiles(root, profiles, versions)
    update_toc(root, profiles, versions)
    errors = catalog_errors(root, profiles, versions)
    if errors:
        raise RuntimeError("\n".join(errors))
    print("Synchronized Data/ClientProfiles.lua and LibTaxiData.toc.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
