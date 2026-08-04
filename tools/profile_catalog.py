#!/usr/bin/env python3
"""Validate and materialize the LibTaxiData client profile catalog."""

from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = Path(__file__).with_name("profiles.json")
BUILD_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
PROJECT_CONSTANT_PATTERN = re.compile(r"^WOW_PROJECT_[A-Z0-9_]+$")
LOCALES = (
    "enUS",
    "enGB",
    "deDE",
    "esES",
    "esMX",
    "frFR",
    "itIT",
    "koKR",
    "ptBR",
    "ruRU",
    "zhCN",
    "zhTW",
)
PROFILE_KEYS = {
    "id",
    "name",
    "gameType",
    "projectConstant",
    "channel",
    "product",
    "build",
    "default",
    "localized",
    "dataSet",
    "releaseBase",
}
PRERELEASE_TYPES = {
    "ptr": "beta",
    "beta": "alpha",
}
CHANNELS = {"live", "ptr", "beta", "legacy"}


def lua_string(value: str) -> str:
    return (
        '"'
        + value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        + '"'
    )


def build_to_interface(build: str) -> int:
    if not BUILD_PATTERN.fullmatch(build):
        raise ValueError(f"Invalid Blizzard build: {build!r}")
    major, minor, patch, _build_number = map(int, build.split("."))
    return major * 10000 + minor * 100 + patch


def build_number(build: str) -> int:
    if not BUILD_PATTERN.fullmatch(build):
        raise ValueError(f"Invalid Blizzard build: {build!r}")
    return int(build.rsplit(".", 1)[1])


def release_type_for_profile(
    profile: dict[str, object], by_id: dict[str, dict[str, object]]
) -> str | None:
    build = profile.get("build")
    if not build:
        return None
    channel = str(profile["channel"])
    release_type = PRERELEASE_TYPES.get(channel)
    if release_type is None:
        return "release"

    release_base_id = profile.get("releaseBase")
    if not release_base_id:
        return None
    release_base = by_id.get(str(release_base_id))
    if not release_base or not release_base.get("build"):
        return None
    if build_number(str(build)) <= build_number(str(release_base["build"])):
        return None
    return release_type


def validate_profiles(profiles: object) -> list[dict[str, object]]:
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("The client profile catalog must be a non-empty list")

    validated: list[dict[str, object]] = []
    by_id: dict[str, dict[str, object]] = {}
    defaults: dict[str, str] = {}
    builds: dict[tuple[str, str], str] = {}
    projects: dict[str, str] = {}
    game_type_projects: dict[str, str] = {}

    for index, raw_profile in enumerate(profiles):
        location = f"profile #{index + 1}"
        if not isinstance(raw_profile, dict):
            raise ValueError(f"{location} must be an object")
        unknown = set(raw_profile).difference(PROFILE_KEYS)
        if unknown:
            raise ValueError(
                f"{location} has unknown fields: {', '.join(sorted(unknown))}"
            )
        profile = dict(raw_profile)
        for key in ("id", "name", "gameType", "projectConstant", "channel"):
            if not isinstance(profile.get(key), str) or not profile[key]:
                raise ValueError(f"{location} requires a non-empty {key!r}")
        for key in ("product", "build"):
            if key not in profile:
                raise ValueError(f"{location} requires the {key!r} field")

        profile_id = str(profile["id"])
        game_type = str(profile["gameType"])
        project_constant = str(profile["projectConstant"])
        if not ID_PATTERN.fullmatch(profile_id):
            raise ValueError(f"Invalid profile id: {profile_id!r}")
        if not ID_PATTERN.fullmatch(game_type):
            raise ValueError(f"Invalid game type for {profile_id!r}: {game_type!r}")
        if not ID_PATTERN.fullmatch(str(profile["channel"])):
            raise ValueError(
                f"Invalid channel for {profile_id!r}: {profile['channel']!r}"
            )
        if profile["channel"] not in CHANNELS:
            raise ValueError(
                f"Unsupported channel for {profile_id!r}: {profile['channel']!r}"
            )
        if not PROJECT_CONSTANT_PATTERN.fullmatch(project_constant):
            raise ValueError(
                f"Invalid project constant for {profile_id!r}: {project_constant!r}"
            )
        if profile_id in by_id:
            raise ValueError(f"Duplicate profile id: {profile_id!r}")
        by_id[profile_id] = profile

        previous_game_type = projects.setdefault(project_constant, game_type)
        if previous_game_type != game_type:
            raise ValueError(
                f"{project_constant} is assigned to both {previous_game_type!r} "
                f"and {game_type!r}"
            )
        previous_project = game_type_projects.setdefault(game_type, project_constant)
        if previous_project != project_constant:
            raise ValueError(
                f"Game type {game_type!r} uses both {previous_project} "
                f"and {project_constant}"
            )

        product = profile.get("product")
        if product is not None and (
            not isinstance(product, str) or not ID_PATTERN.fullmatch(product)
        ):
            raise ValueError(f"Invalid Blizzard product for {profile_id!r}: {product!r}")
        build = profile.get("build")
        if build is not None and (
            not isinstance(build, str) or not BUILD_PATTERN.fullmatch(build)
        ):
            raise ValueError(f"Invalid build for {profile_id!r}: {build!r}")
        for key in ("default", "localized"):
            if key in profile and not isinstance(profile[key], bool):
                raise ValueError(f"{key!r} must be boolean for {profile_id!r}")
        data_set = profile.get("dataSet")
        if data_set is not None and (
            not isinstance(data_set, str) or not ID_PATTERN.fullmatch(data_set)
        ):
            raise ValueError(f"Invalid data set for {profile_id!r}: {data_set!r}")
        release_base = profile.get("releaseBase")
        if release_base is not None and (
            not isinstance(release_base, str) or not ID_PATTERN.fullmatch(release_base)
        ):
            raise ValueError(
                f"Invalid release base for {profile_id!r}: {release_base!r}"
            )

        if profile.get("default"):
            previous_default = defaults.setdefault(game_type, profile_id)
            if previous_default != profile_id:
                raise ValueError(
                    f"Game type {game_type!r} has multiple defaults: "
                    f"{previous_default!r} and {profile_id!r}"
                )
        if build:
            build_key = game_type, str(build)
            previous_profile = builds.setdefault(build_key, profile_id)
            if previous_profile != profile_id:
                raise ValueError(
                    f"Profiles {previous_profile!r} and {profile_id!r} select the "
                    f"same {game_type} build {build}"
                )
        validated.append(profile)

    active_game_types = {
        str(profile["gameType"]) for profile in validated if profile.get("build")
    }
    missing_defaults = active_game_types.difference(defaults)
    if missing_defaults:
        raise ValueError(
            "Active game types without a default profile: "
            + ", ".join(sorted(missing_defaults))
        )

    for profile in validated:
        data_set = str(profile.get("dataSet", profile["id"]))
        source = by_id.get(data_set)
        if source is None:
            raise ValueError(
                f"Profile {profile['id']!r} references unknown data set {data_set!r}"
            )
        if source.get("gameType") != profile.get("gameType"):
            raise ValueError(
                f"Profile {profile['id']!r} and data set {data_set!r} have "
                "different game types"
            )
        if profile.get("build") and not source.get("build"):
            raise ValueError(
                f"Active profile {profile['id']!r} references inactive data set "
                f"{data_set!r}"
            )

        release_base_id = profile.get("releaseBase")
        if release_base_id:
            release_base = by_id.get(str(release_base_id))
            if release_base is None:
                raise ValueError(
                    f"Profile {profile['id']!r} references unknown release base "
                    f"{release_base_id!r}"
                )
            if profile.get("channel") not in PRERELEASE_TYPES:
                raise ValueError(
                    f"Only PTR/Beta profiles can define releaseBase: "
                    f"{profile['id']!r}"
                )
            if release_base.get("channel") in PRERELEASE_TYPES:
                raise ValueError(
                    f"Release base {release_base_id!r} must be a normal profile"
                )
            if release_base.get("gameType") != profile.get("gameType"):
                raise ValueError(
                    f"Profile {profile['id']!r} and release base "
                    f"{release_base_id!r} have different game types"
                )
    return validated


def load_profiles(path: Path = PROFILES_PATH) -> list[dict[str, object]]:
    return validate_profiles(json.loads(path.read_text(encoding="utf-8")))


def save_profiles(
    profiles: list[dict[str, object]], path: Path = PROFILES_PATH
) -> None:
    validated = validate_profiles(profiles)
    path.write_text(
        json.dumps(validated, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def required_data_paths(output: Path, data_set: str) -> list[Path]:
    return [
        output / "Data" / data_set / "TaxiNodes.lua",
        output / "Locale" / data_set / "enUS.lua",
    ]


def active_profiles(
    output: Path, profiles: list[dict[str, object]]
) -> list[dict[str, object]]:
    return [
        profile
        for profile in profiles
        if profile.get("build")
        and all(
            path.exists()
            for path in required_data_paths(
                output, str(profile.get("dataSet", profile["id"]))
            )
        )
    ]


def render_client_profiles(
    output: Path, profiles: list[dict[str, object]]
) -> str:
    lines = [
        "-- This file is generated. Do not edit it by hand.",
        "local lib = _G.LibTaxiData_Internal",
        "if not lib then return end",
        "",
        "lib.ClientGameTypes = {",
    ]
    written_game_types: set[str] = set()
    for profile in profiles:
        game_type = str(profile["gameType"])
        if game_type in written_game_types:
            continue
        written_game_types.add(game_type)
        lines.append(
            "    { gameType = "
            + lua_string(game_type)
            + ", projectConstant = "
            + lua_string(str(profile["projectConstant"]))
            + " },"
        )
    lines.extend(["}", "", "lib.ClientProfiles = {"])
    for profile in active_profiles(output, profiles):
        values = [
            f"profile = {lua_string(str(profile['id']))}",
            f"dataSet = {lua_string(str(profile.get('dataSet', profile['id'])))}",
            f"gameType = {lua_string(str(profile['gameType']))}",
            f"channel = {lua_string(str(profile['channel']))}",
            f"build = {lua_string(str(profile['build']))}",
            f"interface = {build_to_interface(str(profile['build']))}",
        ]
        if profile.get("product"):
            values.append(f"product = {lua_string(str(profile['product']))}")
        if profile.get("default"):
            values.append("default = true")
        lines.append("    { " + ", ".join(values) + " },")
    lines.append("}")
    return "\n".join(lines) + "\n"


def generate_client_profiles(
    output: Path, profiles: list[dict[str, object]]
) -> None:
    path = output / "Data" / "ClientProfiles.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_client_profiles(output, profiles),
        encoding="utf-8",
        newline="\n",
    )


def replace_generated_block(text: str, name: str, lines: list[str]) -> str:
    begin = f"## X-Generated-{name}-Begin: true"
    end = f"## X-Generated-{name}-End: true"
    replacement = "\n".join([begin, *lines, end])
    result, replacements = re.subn(
        rf"^{re.escape(begin)}$.*?^{re.escape(end)}$",
        lambda _match: replacement,
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    if replacements != 1:
        raise RuntimeError(f"Generated {name.lower()} markers not found in LibTaxiData.toc")
    return result


def render_toc(output: Path, profiles: list[dict[str, object]]) -> str | None:
    toc_path = output / "LibTaxiData.toc"
    if not toc_path.exists():
        return None
    enabled = active_profiles(output, profiles)
    by_game_type: dict[str, list[int]] = defaultdict(list)
    for profile in enabled:
        interface = build_to_interface(str(profile["build"]))
        if interface not in by_game_type[str(profile["gameType"])]:
            by_game_type[str(profile["gameType"])].append(interface)

    all_interfaces = [
        interface for values in by_game_type.values() for interface in values
    ]
    interface_lines = ["## Interface: " + ", ".join(map(str, all_interfaces))]
    labels = {
        "classic": "Classic",
        "tbc": "TBC",
        "wrath": "Wrath",
        "cata": "Cata",
        "mists": "Mists",
    }
    for game_type, label in labels.items():
        if by_game_type.get(game_type):
            interface_lines.append(
                f"## Interface-{label}: "
                + ", ".join(map(str, by_game_type[game_type]))
            )

    file_lines = []
    data_names = (
        "TaxiNodes.lua",
        "PlayerConditions.lua",
        "ModifierTrees.lua",
        "SupportingData.lua",
    )
    written_data_sets = set()
    for profile in enabled:
        data_set = str(profile.get("dataSet", profile["id"]))
        if data_set in written_data_sets:
            continue
        written_data_sets.add(data_set)
        game_type = str(profile["gameType"])
        for name in data_names:
            file_lines.append(
                f"Data\\{data_set}\\{name} [AllowLoadGameType {game_type}]"
            )
        for locale in LOCALES:
            file_lines.append(
                f"Locale\\{data_set}\\{locale}.lua [AllowLoadGameType {game_type}]"
            )
        file_lines.append("")
    if file_lines and not file_lines[-1]:
        file_lines.pop()

    toc = toc_path.read_text(encoding="utf-8-sig")
    toc = replace_generated_block(toc, "Interfaces", interface_lines)
    return replace_generated_block(toc, "Profiles", file_lines)


def update_toc(output: Path, profiles: list[dict[str, object]]) -> None:
    toc = render_toc(output, profiles)
    if toc is not None:
        (output / "LibTaxiData.toc").write_text(
            toc, encoding="utf-8", newline="\n"
        )


def generated_profile_directories(root: Path) -> set[str]:
    result: set[str] = set()
    for parent_name in ("Data", "Locale"):
        parent = root / parent_name
        if parent.exists():
            result.update(path.name for path in parent.iterdir() if path.is_dir())
    return result


def orphan_profile_directories(
    root: Path, profiles: list[dict[str, object]]
) -> list[Path]:
    known = {str(profile["id"]) for profile in profiles}
    orphans = generated_profile_directories(root).difference(known)
    return [
        parent / profile_id
        for profile_id in sorted(orphans)
        for parent in (root / "Data", root / "Locale")
        if (parent / profile_id).is_dir()
    ]


def prune_profile_directories(
    root: Path, profiles: list[dict[str, object]]
) -> list[Path]:
    removed = orphan_profile_directories(root, profiles)
    allowed_parents = {(root / "Data").resolve(), (root / "Locale").resolve()}
    for path in removed:
        resolved = path.resolve()
        if resolved.parent not in allowed_parents:
            raise RuntimeError(f"Refusing to prune path outside generated roots: {path}")
        shutil.rmtree(resolved)
    return removed


def missing_generated_paths(
    root: Path, profiles: list[dict[str, object]]
) -> list[Path]:
    missing: set[Path] = set()
    for profile in profiles:
        if not profile.get("build"):
            continue
        data_set = str(profile.get("dataSet", profile["id"]))
        missing.update(
            path for path in required_data_paths(root, data_set) if not path.exists()
        )
    return sorted(missing)


def catalog_errors(
    root: Path, profiles: list[dict[str, object]]
) -> list[str]:
    errors = [
        f"Missing generated file: {path.relative_to(root)}"
        for path in missing_generated_paths(root, profiles)
    ]
    errors.extend(
        f"Generated directory is not in tools/profiles.json: {path.relative_to(root)}"
        for path in orphan_profile_directories(root, profiles)
    )

    manifest_path = root / "Data" / "ClientProfiles.lua"
    expected_manifest = render_client_profiles(root, profiles)
    if not manifest_path.exists() or manifest_path.read_text(
        encoding="utf-8-sig"
    ) != expected_manifest:
        errors.append("Data/ClientProfiles.lua is not synchronized with the catalog")

    expected_toc = render_toc(root, profiles)
    toc_path = root / "LibTaxiData.toc"
    if expected_toc is not None and toc_path.read_text(
        encoding="utf-8-sig"
    ) != expected_toc:
        errors.append("LibTaxiData.toc is not synchronized with the catalog")
    return errors
