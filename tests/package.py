#!/usr/bin/env python3
"""Validate minimal release archives and data-set compatibility aliases."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.generate import classify_taxi, profile_content_fingerprint  # noqa: E402
from tools.package import build_components, build_number, release_bundles  # noqa: E402
from tools.profile_catalog import (  # noqa: E402
    load_profiles,
    load_versions,
    release_type_for_profile,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_dir", type=Path)
    args = parser.parse_args()

    versions = load_versions()
    version_ids = {str(version["id"]) for version in versions}
    assert {
        "retail",
        "classic",
        "anniversary",
        "wrath",
        "cataclysm",
        "mists",
    } <= version_ids
    assert {str(profile["version"]) for profile in load_profiles()} <= version_ids

    assert classify_taxi(
        {"ID": "1", "ContinentID": "0", "Name_lang": "[HIDDEN] Network Hub"},
        set(),
    ) == "hidden-node"
    assert classify_taxi(
        {"ID": "2", "ContinentID": "0", "Name_lang": "TEMPAREA1, Argus"},
        set(),
    ) == "temporary-node"
    assert classify_taxi(
        {"ID": "3", "ContinentID": "0", "Name_lang": "Temple of Akunda"},
        set(),
    ) is None
    assert classify_taxi(
        {"ID": "4", "ContinentID": "0", "Name_lang": "Temporal Conflux"},
        set(),
    ) is None
    assert classify_taxi(
        {"ID": "5", "ContinentID": "0", "Name_lang": "Quest Path 42: Route"},
        set(),
    ) == "quest-path-node"
    assert classify_taxi(
        {"ID": "6", "ContinentID": "0", "Name_lang": "Transport - Start"},
        set(),
    ) == "script-endpoint"
    assert classify_taxi(
        {"ID": "7", "ContinentID": "0", "Name_lang": ""},
        set(),
    ) == "unnamed-node"
    assert classify_taxi(
        {"ID": "8", "ContinentID": "0", "Name_lang": "Old Gate, Revendreth"},
        set(),
    ) is None

    normal = {
        "id": "normal",
        "gameType": "mainline",
        "channel": "live",
        "build": "1.2.3.100",
    }
    newer_ptr = {
        "id": "newer_ptr",
        "gameType": "mainline",
        "channel": "ptr",
        "build": "1.3.0.99",
        "releaseBase": "normal",
    }
    newer_beta = {
        "id": "newer_beta",
        "gameType": "mainline",
        "channel": "beta",
        "build": "1.3.0.102",
        "releaseBase": "normal",
    }
    older_ptr = {
        "id": "older_ptr",
        "gameType": "mainline",
        "channel": "ptr",
        "build": "1.2.3.99",
        "releaseBase": "normal",
    }
    standalone_ptr = {
        "id": "standalone_ptr",
        "gameType": "tbc",
        "channel": "ptr",
        "build": "2.5.6.90",
    }
    synthetic = {
        str(profile["id"]): profile
        for profile in (normal, newer_ptr, newer_beta, older_ptr, standalone_ptr)
    }
    assert release_type_for_profile(normal, synthetic) == "release"
    assert release_type_for_profile(newer_ptr, synthetic) == "beta"
    assert release_type_for_profile(newer_beta, synthetic) == "alpha"
    assert release_type_for_profile(older_ptr, synthetic) is None
    assert release_type_for_profile(standalone_ptr, synthetic) == "beta"
    assert build_number("99.0.0.99") == 99
    assert build_components("12.1.0.68914") > build_components("12.0.7.68974")

    archive_dir = args.archive_dir.resolve()
    releases = json.loads((archive_dir / "manifest.json").read_text(encoding="utf-8"))
    profiles = [profile for profile in load_profiles() if profile.get("build")]
    bundles = release_bundles(ROOT, load_profiles())
    assert {
        (bundle["data_set"], bundle["release_type"])
        for bundle in bundles
    } == {
        ("classic", "release"),
        ("mists", "release"),
        ("retail", "release"),
        ("retail_ptr", "beta"),
        ("tbc", "beta"),
    }
    expected_profiles = {
        profile_id
        for bundle in bundles
        for profile_id in bundle["profile_list"]
    }
    assert [build_components(release["build"]) for release in releases] == sorted(
        build_components(release["build"]) for release in releases
    )
    assert [
        (release["data_set"], release["release_type"])
        for release in releases
    ] == [
        (bundle["data_set"], bundle["release_type"])
        for bundle in bundles
    ]
    packaged_profiles: set[str] = set()

    for profile in profiles:
        data_set = str(profile.get("dataSet", profile["id"]))
        if data_set != profile["id"]:
            assert profile_content_fingerprint(ROOT, str(profile["id"])) == \
                profile_content_fingerprint(ROOT, data_set)

    for release in releases:
        archive = archive_dir / release["archive"]
        assert archive.stat().st_size < 2 * 1024 * 1024, archive
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            manifest = package.read("LibTaxiData/Data/ClientProfiles.lua").decode()
            toc = package.read("LibTaxiData/LibTaxiData.toc").decode()

        data_sets = {
            parts[2]
            for name in names
            if len(parts := PurePosixPath(name).parts) > 3
            and parts[:2] == ("LibTaxiData", "Data")
            and parts[2] != "ClientProfiles.lua"
        }
        locale_sets = {
            parts[2]
            for name in names
            if len(parts := PurePosixPath(name).parts) > 3
            and parts[:2] == ("LibTaxiData", "Locale")
        }
        assert data_sets == {release["data_set"]}
        assert locale_sets == {release["data_set"]}
        assert "LibTaxiData/Compatibility.lua" in names
        assert 'version = "wrath"' in manifest
        assert 'version = "cataclysm"' in manifest
        embedded_profiles = set(re.findall(r'profile = "([^"]+)"', manifest))
        assert embedded_profiles == set(release["profile_list"])
        assert toc.count("\\TaxiNodes.lua") == 1
        assert "## X-Curse-Project-ID: 1636228" in toc
        assert "## X-WoWI-ID: 27178" in toc
        assert "## X-Wago-ID: jK8gl56y" in toc
        assert "## Interface-Wrath: 30403" in toc
        assert "## Interface-Cata: 40402" in toc
        packaged_profiles.update(embedded_profiles)

    assert packaged_profiles == expected_profiles
    print(f"Validated {len(releases)} minimal release archives.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
