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
VERSIONS_PATH = Path(__file__).with_name("versions.json")
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
    "version",
    "channel",
    "product",
    "build",
    "default",
    "localized",
    "dataSet",
    "releaseBase",
}
DERIVED_PROFILE_KEYS = {"gameType", "projectConstant", "apiFamily"}
VERSION_KEYS = {
    "id",
    "name",
    "gameType",
    "projectConstant",
    "apiFamily",
    "apiOverrides",
    "interfaceMajor",
    "minimumInterfaceMajor",
    "tocInterface",
    "tocLabel",
}
API_FAMILIES = {"modern", "legacy"}
API_FEATURES = {
    "questCompleted",
    "questLog",
    "questReady",
    "auras",
    "spellBook",
    "items",
    "currency",
    "reputation",
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


def validate_versions(versions: object) -> list[dict[str, object]]:
    """Validate permanent client families independently from active servers."""
    if not isinstance(versions, list) or not versions:
        raise ValueError("The base-version catalog must be a non-empty list")

    validated: list[dict[str, object]] = []
    ids: set[str] = set()
    game_types: set[str] = set()
    project_constants: set[str] = set()
    exact_interface_majors: set[int] = set()
    minimum_interface_versions = 0
    for index, raw_version in enumerate(versions):
        location = f"base version #{index + 1}"
        if not isinstance(raw_version, dict):
            raise ValueError(f"{location} must be an object")
        unknown = set(raw_version).difference(VERSION_KEYS)
        if unknown:
            raise ValueError(
                f"{location} has unknown fields: {', '.join(sorted(unknown))}"
            )
        version = dict(raw_version)
        for key in ("id", "name", "gameType", "projectConstant", "apiFamily"):
            if not isinstance(version.get(key), str) or not version[key]:
                raise ValueError(f"{location} requires a non-empty {key!r}")

        version_id = str(version["id"])
        game_type = str(version["gameType"])
        project_constant = str(version["projectConstant"])
        if not ID_PATTERN.fullmatch(version_id):
            raise ValueError(f"Invalid base-version id: {version_id!r}")
        if not ID_PATTERN.fullmatch(game_type):
            raise ValueError(f"Invalid game type for {version_id!r}: {game_type!r}")
        if not PROJECT_CONSTANT_PATTERN.fullmatch(project_constant):
            raise ValueError(
                f"Invalid project constant for {version_id!r}: {project_constant!r}"
            )
        if version["apiFamily"] not in API_FAMILIES:
            raise ValueError(
                f"Unsupported API family for {version_id!r}: {version['apiFamily']!r}"
            )
        api_overrides = version.get("apiOverrides", {})
        if not isinstance(api_overrides, dict):
            raise ValueError(f"apiOverrides must be an object for {version_id!r}")
        unknown_features = set(api_overrides).difference(API_FEATURES)
        if unknown_features:
            raise ValueError(
                f"Unknown API overrides for {version_id!r}: "
                + ", ".join(sorted(unknown_features))
            )
        for feature, family in api_overrides.items():
            if family not in API_FAMILIES:
                raise ValueError(
                    f"Invalid API override {feature!r} for {version_id!r}: {family!r}"
                )
        if version_id in ids:
            raise ValueError(f"Duplicate base-version id: {version_id!r}")
        if game_type in game_types:
            raise ValueError(f"Duplicate game type: {game_type!r}")
        if project_constant in project_constants:
            raise ValueError(f"Duplicate project constant: {project_constant!r}")
        ids.add(version_id)
        game_types.add(game_type)
        project_constants.add(project_constant)

        exact_major = version.get("interfaceMajor")
        minimum_major = version.get("minimumInterfaceMajor")
        if exact_major is not None and minimum_major is not None:
            raise ValueError(
                f"Base version {version_id!r} cannot define both interface rules"
            )
        if exact_major is None and minimum_major is None:
            raise ValueError(
                f"Base version {version_id!r} requires an interface detection rule"
            )
        if exact_major is not None:
            if not isinstance(exact_major, int) or exact_major <= 0:
                raise ValueError(f"Invalid interfaceMajor for {version_id!r}")
            if exact_major in exact_interface_majors:
                raise ValueError(f"Duplicate interface major: {exact_major}")
            exact_interface_majors.add(exact_major)
        if minimum_major is not None:
            if not isinstance(minimum_major, int) or minimum_major <= 0:
                raise ValueError(f"Invalid minimumInterfaceMajor for {version_id!r}")
            minimum_interface_versions += 1
        toc_label = version.get("tocLabel")
        if toc_label is not None and (
            not isinstance(toc_label, str) or not re.fullmatch(r"[A-Za-z0-9]+", toc_label)
        ):
            raise ValueError(f"Invalid TOC label for {version_id!r}: {toc_label!r}")
        toc_interface = version.get("tocInterface")
        if not isinstance(toc_interface, int) or toc_interface <= 0:
            raise ValueError(f"Invalid tocInterface for {version_id!r}")
        toc_major = toc_interface // 10000
        if exact_major is not None and toc_major != exact_major:
            raise ValueError(
                f"tocInterface for {version_id!r} does not match interfaceMajor"
            )
        if minimum_major is not None and toc_major < minimum_major:
            raise ValueError(
                f"tocInterface for {version_id!r} is below minimumInterfaceMajor"
            )
        validated.append(version)

    if minimum_interface_versions > 1:
        raise ValueError("Only one open-ended minimum interface rule is supported")
    return validated


def load_versions(path: Path = VERSIONS_PATH) -> list[dict[str, object]]:
    return validate_versions(json.loads(path.read_text(encoding="utf-8")))


def validate_profiles(
    profiles: object, versions: list[dict[str, object]] | None = None
) -> list[dict[str, object]]:
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("The client profile catalog must be a non-empty list")

    versions = versions or load_versions()
    versions_by_id = {str(version["id"]): version for version in versions}
    validated: list[dict[str, object]] = []
    by_id: dict[str, dict[str, object]] = {}
    defaults: dict[str, str] = {}
    builds: dict[tuple[str, str], str] = {}

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
        for key in ("id", "name", "version", "channel"):
            if not isinstance(profile.get(key), str) or not profile[key]:
                raise ValueError(f"{location} requires a non-empty {key!r}")
        for key in ("product", "build"):
            if key not in profile:
                raise ValueError(f"{location} requires the {key!r} field")

        profile_id = str(profile["id"])
        version_id = str(profile["version"])
        if not ID_PATTERN.fullmatch(profile_id):
            raise ValueError(f"Invalid profile id: {profile_id!r}")
        version = versions_by_id.get(version_id)
        if version is None:
            raise ValueError(
                f"Profile {profile_id!r} references unknown base version {version_id!r}"
            )
        game_type = str(version["gameType"])
        if not ID_PATTERN.fullmatch(str(profile["channel"])):
            raise ValueError(
                f"Invalid channel for {profile_id!r}: {profile['channel']!r}"
            )
        if profile["channel"] not in CHANNELS:
            raise ValueError(
                f"Unsupported channel for {profile_id!r}: {profile['channel']!r}"
            )
        if profile_id in by_id:
            raise ValueError(f"Duplicate profile id: {profile_id!r}")
        profile["gameType"] = game_type
        profile["projectConstant"] = str(version["projectConstant"])
        profile["apiFamily"] = str(version["apiFamily"])
        by_id[profile_id] = profile

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
            previous_default = defaults.setdefault(version_id, profile_id)
            if previous_default != profile_id:
                raise ValueError(
                    f"Base version {version_id!r} has multiple defaults: "
                    f"{previous_default!r} and {profile_id!r}"
                )
        if build:
            build_key = version_id, str(build)
            previous_profile = builds.setdefault(build_key, profile_id)
            if previous_profile != profile_id:
                raise ValueError(
                    f"Profiles {previous_profile!r} and {profile_id!r} select the "
                    f"same {version_id} build {build}"
                )
        validated.append(profile)

    active_versions = {
        str(profile["version"]) for profile in validated if profile.get("build")
    }
    missing_defaults = active_versions.difference(defaults)
    if missing_defaults:
        raise ValueError(
            "Active base versions without a default profile: "
            + ", ".join(sorted(missing_defaults))
        )

    for profile in validated:
        data_set = str(profile.get("dataSet", profile["id"]))
        source = by_id.get(data_set)
        if source is None:
            raise ValueError(
                f"Profile {profile['id']!r} references unknown data set {data_set!r}"
            )
        if source.get("version") != profile.get("version"):
            raise ValueError(
                f"Profile {profile['id']!r} and data set {data_set!r} have "
                "different base versions"
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
            if release_base.get("version") != profile.get("version"):
                raise ValueError(
                    f"Profile {profile['id']!r} and release base "
                    f"{release_base_id!r} have different base versions"
                )
    return validated


def load_profiles(
    path: Path = PROFILES_PATH, versions_path: Path | None = None
) -> list[dict[str, object]]:
    versions = load_versions(versions_path or path.with_name("versions.json"))
    return validate_profiles(json.loads(path.read_text(encoding="utf-8")), versions)


def save_profiles(
    profiles: list[dict[str, object]], path: Path = PROFILES_PATH
) -> None:
    for profile in profiles:
        unknown = set(profile).difference(PROFILE_KEYS | DERIVED_PROFILE_KEYS)
        if unknown:
            raise ValueError(
                f"Profile {profile.get('id')!r} has unknown fields: "
                + ", ".join(sorted(unknown))
            )
    serialized = [
        {key: value for key, value in profile.items() if key in PROFILE_KEYS}
        for profile in profiles
    ]
    validate_profiles(serialized, load_versions(path.with_name("versions.json")))
    path.write_text(
        json.dumps(serialized, indent=2, ensure_ascii=False) + "\n",
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
    output: Path,
    profiles: list[dict[str, object]],
    versions: list[dict[str, object]] | None = None,
) -> str:
    versions = versions or load_versions()
    lines = [
        "-- This file is generated. Do not edit it by hand.",
        "local lib = _G.LibTaxiData_Internal",
        "if not lib then return end",
        "",
        "lib.ClientVersions = {",
    ]
    for version in versions:
        values = [
            f"version = {lua_string(str(version['id']))}",
            f"name = {lua_string(str(version['name']))}",
            f"gameType = {lua_string(str(version['gameType']))}",
            f"projectConstant = {lua_string(str(version['projectConstant']))}",
            f"apiFamily = {lua_string(str(version['apiFamily']))}",
        ]
        if version.get("interfaceMajor") is not None:
            values.append(f"interfaceMajor = {int(version['interfaceMajor'])}")
        if version.get("minimumInterfaceMajor") is not None:
            values.append(
                f"minimumInterfaceMajor = {int(version['minimumInterfaceMajor'])}"
            )
        if version.get("tocLabel"):
            values.append(f"tocLabel = {lua_string(str(version['tocLabel']))}")
        if version.get("apiOverrides"):
            overrides = ", ".join(
                f"{feature} = {lua_string(str(family))}"
                for feature, family in sorted(
                    dict(version["apiOverrides"]).items()
                )
            )
            values.append("apiOverrides = { " + overrides + " }")
        lines.append("    { " + ", ".join(values) + " },")
    lines.extend(
        [
            "}",
            "-- Compatibility alias for consumers of the first catalog format.",
            "lib.ClientGameTypes = lib.ClientVersions",
            "",
            "lib.ClientProfiles = {",
        ]
    )
    for profile in active_profiles(output, profiles):
        values = [
            f"profile = {lua_string(str(profile['id']))}",
            f"dataSet = {lua_string(str(profile.get('dataSet', profile['id'])))}",
            f"version = {lua_string(str(profile['version']))}",
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
    output: Path,
    profiles: list[dict[str, object]],
    versions: list[dict[str, object]] | None = None,
) -> None:
    path = output / "Data" / "ClientProfiles.lua"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_client_profiles(output, profiles, versions),
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


def render_toc(
    output: Path,
    profiles: list[dict[str, object]],
    versions: list[dict[str, object]] | None = None,
) -> str | None:
    toc_path = output / "LibTaxiData.toc"
    if not toc_path.exists():
        return None
    enabled = active_profiles(output, profiles)
    by_game_type: dict[str, list[int]] = defaultdict(list)
    for profile in enabled:
        interface = build_to_interface(str(profile["build"]))
        if interface not in by_game_type[str(profile["gameType"])]:
            by_game_type[str(profile["gameType"])].append(interface)

    versions = versions or load_versions()
    for version in versions:
        game_type = str(version["gameType"])
        interface = int(version["tocInterface"])
        if interface not in by_game_type[game_type]:
            by_game_type[game_type].append(interface)

    all_interfaces = [
        interface for values in by_game_type.values() for interface in values
    ]
    interface_lines = ["## Interface: " + ", ".join(map(str, all_interfaces))]
    labels = [
        (str(version["gameType"]), str(version["tocLabel"]))
        for version in versions
        if version.get("tocLabel")
    ]
    for game_type, label in labels:
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


def update_toc(
    output: Path,
    profiles: list[dict[str, object]],
    versions: list[dict[str, object]] | None = None,
) -> None:
    toc = render_toc(output, profiles, versions)
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
    root: Path,
    profiles: list[dict[str, object]],
    versions: list[dict[str, object]] | None = None,
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
    expected_manifest = render_client_profiles(root, profiles, versions)
    if not manifest_path.exists() or manifest_path.read_text(
        encoding="utf-8-sig"
    ) != expected_manifest:
        errors.append("Data/ClientProfiles.lua is not synchronized with the catalog")

    expected_toc = render_toc(root, profiles, versions)
    toc_path = root / "LibTaxiData.toc"
    if expected_toc is not None and toc_path.read_text(
        encoding="utf-8-sig"
    ) != expected_toc:
        errors.append("LibTaxiData.toc is not synchronized with the catalog")
    return errors
