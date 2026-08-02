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

from tools.generate import load_profiles, profile_content_fingerprint  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive_dir", type=Path)
    args = parser.parse_args()
    archive_dir = args.archive_dir.resolve()
    releases = json.loads((archive_dir / "manifest.json").read_text(encoding="utf-8"))
    profiles = [profile for profile in load_profiles() if profile.get("build")]
    expected_profiles = {str(profile["id"]) for profile in profiles}
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
        embedded_profiles = set(re.findall(r'profile = "([^"]+)"', manifest))
        assert embedded_profiles == set(release["profile_list"])
        assert toc.count("\\TaxiNodes.lua") == 1
        assert "## X-Curse-Project-ID: 1636228" in toc
        assert "## X-Wago-ID: jK8gl56y" in toc
        packaged_profiles.update(embedded_profiles)

    assert packaged_profiles == expected_profiles
    print(f"Validated {len(releases)} minimal release archives.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
