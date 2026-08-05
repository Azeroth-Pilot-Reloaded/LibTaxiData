#!/usr/bin/env python3
"""Build or prepare minimal per-data-set LibTaxiData release archives."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

try:
    from profile_catalog import (
        active_profiles,
        build_components,
        build_number,
        generate_client_profiles,
        load_profiles,
        release_type_for_profile,
        update_toc,
    )
except ModuleNotFoundError:  # Imported as tools.package by tests.
    from tools.profile_catalog import (
        active_profiles,
        build_components,
        build_number,
        generate_client_profiles,
        load_profiles,
        release_type_for_profile,
        update_toc,
    )


ROOT = Path(__file__).resolve().parents[1]
COMMON_FILES = (
    "API.lua",
    "Client.lua",
    "Commands.lua",
    "Compatibility.lua",
    "Conditions.lua",
    "Coordinates.lua",
    "LibTaxiData.lua",
    "LibTaxiData.toc",
    "LibTaxiData.xml",
    "LICENSE",
)
COMMON_DIRECTORIES = ("assets",)


def game_version(build: str) -> str:
    return ".".join(build.split(".")[:3])


def release_bundles(
    root: Path, profiles: list[dict[str, object]]
) -> list[dict[str, object]]:
    enabled = active_profiles(root, profiles)
    by_id = {str(profile["id"]): profile for profile in profiles}
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for profile in enabled:
        release_type = release_type_for_profile(profile, by_id)
        if release_type is None:
            continue
        data_set = str(profile.get("dataSet", profile["id"]))
        grouped.setdefault((data_set, release_type), []).append(profile)

    bundles = []
    for (data_set, release_type), compatible in grouped.items():
        newest = max(
            compatible,
            key=lambda profile: (
                build_components(str(profile["build"])),
                str(profile["id"]),
            ),
        )
        versions = []
        for profile in compatible:
            version = game_version(str(profile["build"]))
            if version not in versions:
                versions.append(version)
        bundles.append(
            {
                "data_set": data_set,
                "build": str(newest["build"]),
                "build_number": build_number(str(newest["build"])),
                "game_type": str(newest["gameType"]),
                "game_versions": ",".join(versions),
                "profiles": " ".join(str(profile["id"]) for profile in compatible),
                "profile_list": [str(profile["id"]) for profile in compatible],
                "release_type": release_type,
            }
        )
    release_order = {"release": 0, "beta": 1, "alpha": 2}
    return sorted(
        bundles,
        key=lambda bundle: (
            build_components(str(bundle["build"])),
            release_order[str(bundle["release_type"])],
            str(bundle["data_set"]),
        ),
    )


def profiles_for_bundle(
    profiles: list[dict[str, object]], data_set: str, release_type: str
) -> list[dict[str, object]]:
    by_id = {str(profile["id"]): profile for profile in profiles}
    compatible = [
        dict(profile)
        for profile in profiles
        if profile.get("build")
        and str(profile.get("dataSet", profile["id"])) == data_set
        and release_type_for_profile(profile, by_id) == release_type
    ]
    if not compatible:
        raise ValueError(
            f"Unknown, inactive, or unpublished bundle: "
            f"{data_set!r} ({release_type})"
        )
    if not any(profile.get("default") for profile in compatible):
        # A single-data-set archive must remain usable on the next ungenerated
        # client build. Its selected data set is the only safe local fallback.
        compatible[0]["default"] = True
    return compatible


def pkgmeta_text(root: Path, data_set: str) -> str:
    ignored_profiles = sorted(
        path.name
        for path in (root / "Data").iterdir()
        if path.is_dir() and path.name != data_set
    )
    lines = [
        "package-as: LibTaxiData",
        "",
        "wowi-archive-previous: no",
        "",
        "ignore:",
        "  - .github",
        "  - .gitattributes",
        "  - .gitignore",
        "  - .luacheckrc",
        "  - .pkgmeta",
        "  - .pkgmeta.release",
        "  - README.md",
        "  - tests",
        "  - tools",
    ]
    for profile_id in ignored_profiles:
        lines.append(f"  - Data/{profile_id}")
        lines.append(f"  - Locale/{profile_id}")
    return "\n".join(lines) + "\n"


def prepare_root(
    root: Path,
    profiles: list[dict[str, object]],
    data_set: str,
    release_type: str,
) -> None:
    compatible = profiles_for_bundle(profiles, data_set, release_type)
    generate_client_profiles(root, compatible)
    update_toc(root, compatible)
    (root / ".pkgmeta.release").write_text(
        pkgmeta_text(root, data_set), encoding="utf-8", newline="\n"
    )


def stage_bundle(
    root: Path,
    profiles: list[dict[str, object]],
    bundle: dict[str, object],
    output_dir: Path,
) -> dict[str, object]:
    data_set = str(bundle["data_set"])
    release_type = str(bundle["release_type"])
    compatible = profiles_for_bundle(profiles, data_set, release_type)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"LibTaxiData-{data_set}-{bundle['build']}.zip"

    with tempfile.TemporaryDirectory(prefix="libtaxidata-") as temporary:
        addon = Path(temporary) / "LibTaxiData"
        addon.mkdir()
        for relative in COMMON_FILES:
            shutil.copy2(root / relative, addon / relative)
        for relative in COMMON_DIRECTORIES:
            source = root / relative
            if source.is_dir():
                shutil.copytree(source, addon / relative)
        shutil.copytree(root / "Data" / data_set, addon / "Data" / data_set)
        shutil.copytree(root / "Locale" / data_set, addon / "Locale" / data_set)
        generate_client_profiles(addon, compatible)
        update_toc(addon, compatible)
        toc_path = addon / "LibTaxiData.toc"
        toc_path.write_text(
            toc_path.read_text(encoding="utf-8").replace(
                "@project-version@", f"data-{bundle['build']}"
            ),
            encoding="utf-8",
            newline="\n",
        )

        with zipfile.ZipFile(
            archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as package:
            for path in sorted(addon.rglob("*")):
                if path.is_file():
                    package.write(path, path.relative_to(addon.parent).as_posix())

    result = dict(bundle)
    result["archive"] = archive.name
    result["bytes"] = archive.stat().st_size
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--matrix", action="store_true", help="Print the CI bundle matrix")
    operation.add_argument("--prepare", metavar="DATA_SET", help="Prepare this checkout for the packager")
    operation.add_argument("--build", action="store_true", help="Create minimal ZIP archives")
    parser.add_argument("--data-set", help="Build only this data set instead of every bundle")
    parser.add_argument(
        "--release-type",
        choices=("release", "beta", "alpha"),
        help="Select a release channel when preparing a data set",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profiles = load_profiles()
    bundles = release_bundles(ROOT, profiles)
    if args.release_type and not (args.prepare or args.data_set):
        raise ValueError("--release-type requires --prepare or --data-set")
    if args.matrix:
        print(json.dumps({"include": bundles}, separators=(",", ":")))
        return 0
    if args.prepare:
        matching = [
            bundle
            for bundle in bundles
            if bundle["data_set"] == args.prepare
            and (
                args.release_type is None
                or bundle["release_type"] == args.release_type
            )
        ]
        if len(matching) != 1:
            raise ValueError(
                f"Expected exactly one publishable bundle for {args.prepare!r}; "
                "pass --release-type when the data set has multiple channels"
            )
        prepare_root(
            ROOT,
            profiles,
            args.prepare,
            str(matching[0]["release_type"]),
        )
        return 0

    if args.data_set:
        bundles = [
            bundle
            for bundle in bundles
            if bundle["data_set"] == args.data_set
            and (
                args.release_type is None
                or bundle["release_type"] == args.release_type
            )
        ]
        if not bundles:
            raise ValueError(f"Unknown or inactive data set: {args.data_set!r}")
    results = [
        stage_bundle(ROOT, profiles, bundle, args.output_dir.resolve())
        for bundle in bundles
    ]
    manifest = args.output_dir.resolve() / "manifest.json"
    manifest.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for result in results:
        print(
            f"{result['archive']}: {result['bytes']} bytes "
            f"({result['profiles']}, {result['release_type']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
