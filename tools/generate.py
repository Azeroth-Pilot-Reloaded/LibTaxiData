#!/usr/bin/env python3
"""Generate one or every LibTaxiData client profile from Wago Tools DB2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

try:
    from live_build import BUILD_PATTERN, get_product_build
except ModuleNotFoundError:  # Imported as tools.generate by tests or maintenance scripts.
    from tools.live_build import BUILD_PATTERN, get_product_build


WAGO_CSV_URL = "https://wago.tools/db2/{table}/csv?build={build}&locale={locale}"
PROFILES_PATH = Path(__file__).with_name("profiles.json")
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

NODE_FIELDS = (
    ("continentID", "ContinentID"),
    ("x", "Pos_0"),
    ("y", "Pos_1"),
    ("z", "Pos_2"),
    ("mapOffsetX", "MapOffset_0"),
    ("mapOffsetY", "MapOffset_1"),
    ("flightMapOffsetX", "FlightMapOffset_0"),
    ("flightMapOffsetY", "FlightMapOffset_1"),
    ("conditionID", "ConditionID"),
    ("characterBitNumber", "CharacterBitNumber"),
    ("flags", "Flags"),
    ("uiTextureKitID", "UiTextureKitID"),
    ("minimapAtlasMemberID", "MinimapAtlasMemberID"),
    ("facing", "Facing"),
    ("specialIconConditionID", "SpecialIconConditionID"),
    ("visibilityConditionID", "VisibilityConditionID"),
    ("hordeMountCreatureID", "MountCreatureID_0"),
    ("allianceMountCreatureID", "MountCreatureID_1"),
)

TAXI_DEV_RULES = (
    ("programmer-isle", re.compile(r"^Programmer Isle$", re.IGNORECASE)),
    ("generic-world-target", re.compile(r"^Generic, World Target", re.IGNORECASE)),
    ("test-node", re.compile(r"\btest\b", re.IGNORECASE)),
    ("development-land", re.compile(r"\bDevelopment Land\b", re.IGNORECASE)),
    ("developer-test", re.compile(r"devtest", re.IGNORECASE)),
    ("unused-node", re.compile(r"\[(?:unused|disabled)\b|\bzzz?unused\b", re.IGNORECASE)),
)

MAP_DEV_RULE = re.compile(
    r"\b(?:test|testing|qa|development|developer|programmer|placeholder)\b|"
    r"\bzzz?unused\b|\[unused\]",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    profiles = load_profiles()
    profile_group = parser.add_mutually_exclusive_group()
    profile_group.add_argument(
        "--profile",
        choices=[profile["id"] for profile in profiles],
        help="Client profile to generate (default: retail)",
    )
    profile_group.add_argument(
        "--all",
        action="store_true",
        help="Generate every profile backed by an active Blizzard product",
    )
    parser.add_argument(
        "--build",
        help="Exact Wago/Blizzard build (only valid for one profile)",
    )
    parser.add_argument(
        "--product",
        help="Override the profile's Blizzard product code when resolving its build",
    )
    parser.add_argument(
        "--region",
        default="eu",
        help="Blizzard region used for automatic build detection (default: eu)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="LibTaxiData directory (defaults to the parent of tools/)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Optional directory in which downloaded CSV files are reused",
    )
    return parser.parse_args()


def load_profiles() -> list[dict[str, object]]:
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    if not isinstance(profiles, list):
        raise ValueError(f"Expected a profile list in {PROFILES_PATH}")
    return profiles


def save_profiles(profiles: list[dict[str, object]]) -> None:
    PROFILES_PATH.write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def download_csv(
    table: str,
    build: str,
    locale: str,
    cache_dir: Path | None,
    *,
    attempts: int = 3,
    timeout: int = 120,
) -> list[dict[str, str]]:
    cache_path = None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{table}-{build}-{locale}.csv"

    payload = cache_path.read_bytes() if cache_path and cache_path.exists() else b""
    if not payload.strip():
        url = WAGO_CSV_URL.format(
            table=urllib.parse.quote(table),
            build=urllib.parse.quote(build),
            locale=urllib.parse.quote(locale),
        )
        request = urllib.request.Request(url, headers={"User-Agent": "LibTaxiData generator"})
        print(f"Downloading {table} ({locale}, {build})...", file=sys.stderr)
        for attempt in range(1, attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    payload = response.read()
                if not payload.strip():
                    raise ValueError(f"Empty CSV response from {url}")
                break
            except (OSError, TimeoutError):
                if attempt == attempts:
                    raise
                delay = 2 ** attempt
                print(
                    f"Download failed; retrying {table} ({locale}, {build}) "
                    f"in {delay}s ({attempt}/{attempts})...",
                    file=sys.stderr,
                )
                time.sleep(delay)

    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = list(reader)
    if not reader.fieldnames or not rows:
        raise ValueError(f"Empty or invalid CSV for {table} ({locale}, {build})")
    if cache_path:
        cache_path.write_bytes(payload)
    return rows


def numeric(value: str) -> str:
    value = (value or "0").strip()
    if not re.fullmatch(r"-?(?:\d+(?:\.\d*)?|\.\d+)", value):
        raise ValueError(f"Not a DB2 number: {value!r}")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def integer(value: str) -> int:
    return int(value or 0)


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


def generated_header(table: str, build: str, profile: str) -> list[str]:
    return [
        "-- This file is generated. Do not edit it by hand.",
        f"-- Source: https://wago.tools/db2/{table} (build {build})",
        "local lib = _G.LibTaxiData_Internal",
        "if not lib then return end",
        f"if not lib.Client or lib.Client.dataSet ~= {lua_string(profile)} then return end",
        "",
    ]


def write_lua(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_to_interface(build: str) -> int:
    version_parts = build.split(".")
    if len(version_parts) != 4 or not all(part.isdigit() for part in version_parts):
        raise ValueError(f"Invalid Blizzard build: {build!r}")
    major, minor, patch = map(int, version_parts[:3])
    return major * 10000 + minor * 100 + patch


def active_profiles(output: Path, profiles: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        profile
        for profile in profiles
        if profile.get("build")
        and (
            output
            / "Data"
            / str(profile.get("dataSet", profile["id"]))
            / "TaxiNodes.lua"
        ).exists()
        and (
            output
            / "Locale"
            / str(profile.get("dataSet", profile["id"]))
            / "enUS.lua"
        ).exists()
    ]


def generate_client_profiles(output: Path, profiles: list[dict[str, object]]) -> None:
    lines = [
        "-- This file is generated. Do not edit it by hand.",
        "local lib = _G.LibTaxiData_Internal",
        "if not lib then return end",
        "",
        "lib.ClientProfiles = {",
    ]
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
    write_lua(output / "Data" / "ClientProfiles.lua", lines)


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


def update_toc(output: Path, profiles: list[dict[str, object]]) -> None:
    toc_path = output / "LibTaxiData.toc"
    if not toc_path.exists():
        return
    enabled = active_profiles(output, profiles)
    by_game_type: dict[str, list[int]] = defaultdict(list)
    for profile in enabled:
        interface = build_to_interface(str(profile["build"]))
        if interface not in by_game_type[str(profile["gameType"])]:
            by_game_type[str(profile["gameType"])].append(interface)

    all_interfaces = [
        interface
        for values in by_game_type.values()
        for interface in values
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
                f"## Interface-{label}: " + ", ".join(map(str, by_game_type[game_type]))
            )

    file_lines = []
    data_names = ("TaxiNodes.lua", "PlayerConditions.lua", "ModifierTrees.lua", "SupportingData.lua")
    written_data_sets = set()
    for profile in enabled:
        profile_id = str(profile.get("dataSet", profile["id"]))
        if profile_id in written_data_sets:
            continue
        written_data_sets.add(profile_id)
        game_type = str(profile["gameType"])
        for name in data_names:
            file_lines.append(
                f"Data\\{profile_id}\\{name} [AllowLoadGameType {game_type}]"
            )
        for locale in LOCALES:
            file_lines.append(
                f"Locale\\{profile_id}\\{locale}.lua [AllowLoadGameType {game_type}]"
            )
        file_lines.append("")
    if file_lines and not file_lines[-1]:
        file_lines.pop()

    toc = toc_path.read_text(encoding="utf-8-sig")
    toc = replace_generated_block(toc, "Interfaces", interface_lines)
    toc = replace_generated_block(toc, "Profiles", file_lines)
    toc_path.write_text(toc, encoding="utf-8", newline="\n")


def profile_content_fingerprint(output: Path, profile_id: str) -> str | None:
    paths = [
        *(output / "Data" / profile_id).glob("*.lua"),
        *(output / "Locale" / profile_id).glob("*.lua"),
    ]
    if not paths:
        return None
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: (item.parent.parent.name, item.name)):
        lines = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if line.startswith("-- Source:"):
                continue
            if line.startswith("if not lib.Client"):
                continue
            if stripped.startswith(("build = ", "profile = ", "dataSet = ", "channel = ")):
                continue
            lines.append(line)
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update("\n".join(lines).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def assign_data_sets(output: Path, profiles: list[dict[str, object]]) -> None:
    representatives: dict[tuple[str, str], str] = {}
    for profile in profiles:
        if not profile.get("build"):
            profile.pop("dataSet", None)
            continue
        profile_id = str(profile["id"])
        fingerprint = profile_content_fingerprint(output, profile_id)
        if not fingerprint:
            continue
        key = str(profile["gameType"]), fingerprint
        data_set = representatives.setdefault(key, profile_id)
        profile["dataSet"] = data_set


def classify_map(row: dict[str, str]) -> str | None:
    value = f"{row.get('MapName_lang', '')} {row.get('Directory', '')}"
    return "development-map" if MAP_DEV_RULE.search(value) else None


def classify_taxi(row: dict[str, str], dev_maps: set[int]) -> str | None:
    if integer(row["ContinentID"]) in dev_maps:
        return "development-map"
    name = row.get("Name_lang", "").strip()
    for reason, pattern in TAXI_DEV_RULES:
        if pattern.search(name):
            return reason
    return None


def collect_condition_data(
    nodes: list[dict[str, str]],
    player_condition_rows: list[dict[str, str]],
    modifier_tree_rows: list[dict[str, str]],
) -> tuple[set[int], set[int], set[int]]:
    conditions = {
        integer(node[field])
        for node in nodes
        for field in ("ConditionID", "SpecialIconConditionID", "VisibilityConditionID")
        if integer(node[field])
    }
    player_conditions = {integer(row["ID"]): row for row in player_condition_rows}
    modifier_trees = {integer(row["ID"]): row for row in modifier_tree_rows}
    children: dict[int, list[int]] = defaultdict(list)
    for row in modifier_tree_rows:
        children[integer(row["Parent"])].append(integer(row["ID"]))

    trees: set[int] = set()
    visited_conditions: set[int] = set()
    visited_trees: set[int] = set()
    condition_queue = deque(sorted(conditions))
    tree_queue: deque[int] = deque()

    while condition_queue or tree_queue:
        while condition_queue:
            condition_id = condition_queue.popleft()
            if condition_id in visited_conditions:
                continue
            visited_conditions.add(condition_id)
            row = player_conditions.get(condition_id)
            if not row:
                continue
            tree_id = integer(row.get("ModifierTreeID", "0"))
            if tree_id:
                trees.add(tree_id)
                tree_queue.append(tree_id)

        while tree_queue:
            tree_id = tree_queue.popleft()
            if tree_id in visited_trees:
                continue
            visited_trees.add(tree_id)
            row = modifier_trees.get(tree_id)
            if not row:
                continue
            tree_queue.extend(children.get(tree_id, ()))
            modifier_type = integer(row["Type"])
            asset = integer(row["Asset"])
            if modifier_type == 2 and asset and asset not in visited_conditions:
                conditions.add(asset)
                condition_queue.append(asset)
            elif modifier_type == 73 and asset and asset not in visited_trees:
                trees.add(asset)
                tree_queue.append(asset)

    missing_conditions = conditions.difference(player_conditions)
    return conditions, visited_trees, missing_conditions


def grouped_condition(row: dict[str, str]) -> list[tuple[str, str | list[str]]]:
    scalars: list[tuple[str, str]] = []
    arrays: dict[str, dict[int, str]] = defaultdict(dict)
    for key, raw_value in row.items():
        if key in ("ID", "Failure_description_lang"):
            continue
        match = re.fullmatch(r"(.+)_([0-9]+)", key)
        if match:
            arrays[match.group(1)][int(match.group(2))] = numeric(raw_value)
            continue
        value = numeric(raw_value)
        if value not in ("0", "-1"):
            scalars.append((key, value))

    result: list[tuple[str, str | list[str]]] = list(scalars)
    for key in sorted(arrays):
        values_by_index = arrays[key]
        values = [values_by_index.get(i, "0") for i in range(max(values_by_index) + 1)]
        if any(value != "0" for value in values):
            # The two race mask words are unsigned bit fields even though the
            # CSV representation may use signed int32 values.
            if key == "RaceMasks":
                values = [str(int(value) & 0xFFFFFFFF) for value in values]
            result.append((key, values))
    return sorted(result, key=lambda item: item[0])


def generate_nodes(
    output: Path,
    profile: dict[str, object],
    build: str,
    nodes: list[dict[str, str]],
    excluded: list[tuple[dict[str, str], str]],
    missing_conditions: set[int],
) -> None:
    profile_id = str(profile["id"])
    lines = generated_header("TaxiNodes", build, profile_id)
    lines.extend(
        [
            "lib.Source = {",
            f"    build = {lua_string(build)},",
            f"    profile = {lua_string(profile_id)},",
            f"    dataSet = {lua_string(profile_id)},",
            f"    gameType = {lua_string(str(profile['gameType']))},",
            f"    channel = {lua_string(str(profile['channel']))},",
            '    provider = "Wago Tools",',
            '    tableName = "TaxiNodes",',
            f"    nodeCount = {len(nodes)},",
            f"    excludedNodeCount = {len(excluded)},",
            "}",
            "",
            "lib.Nodes = {",
        ]
    )
    for row in sorted(nodes, key=lambda item: integer(item["ID"])):
        fields = ", ".join(
            f"{name} = {numeric(row.get(column, '0'))}" for name, column in NODE_FIELDS
        )
        lines.append(f"    [{integer(row['ID'])}] = {{ {fields} }},")
    lines.extend(["}", "", "lib.ExcludedNodes = {"])
    for row, reason in sorted(excluded, key=lambda item: integer(item[0]["ID"])):
        lines.append(
            f"    [{integer(row['ID'])}] = {{ reason = {lua_string(reason)}, "
            f"name = {lua_string(row.get('Name_lang', '').strip())} }},"
        )
    lines.extend(["}", "", "lib.MissingPlayerConditions = {"])
    for condition_id in sorted(missing_conditions):
        lines.append(f"    [{condition_id}] = true,")
    lines.append("}")
    write_lua(output / "Data" / profile_id / "TaxiNodes.lua", lines)


def generate_conditions(
    output: Path,
    profile: dict[str, object],
    build: str,
    rows: list[dict[str, str]],
    condition_ids: set[int],
) -> None:
    profile_id = str(profile["id"])
    by_id = {integer(row["ID"]): row for row in rows}
    lines = generated_header("PlayerCondition", build, profile_id)
    lines.append("lib.PlayerConditions = {")
    for condition_id in sorted(condition_ids):
        row = by_id.get(condition_id)
        if not row:
            continue
        values = []
        for key, value in grouped_condition(row):
            if isinstance(value, list):
                values.append(f"{key} = {{ {', '.join(value)} }}")
            else:
                values.append(f"{key} = {value}")
        lines.append(f"    [{condition_id}] = {{ {', '.join(values)} }},")
    lines.append("}")
    write_lua(output / "Data" / profile_id / "PlayerConditions.lua", lines)


def generate_modifier_trees(
    output: Path,
    profile: dict[str, object],
    build: str,
    rows: list[dict[str, str]],
    tree_ids: set[int],
) -> set[int]:
    profile_id = str(profile["id"])
    by_id = {integer(row["ID"]): row for row in rows}
    content_tuning_ids: set[int] = set()
    lines = generated_header("ModifierTree", build, profile_id)
    lines.append("lib.ModifierTrees = {")
    for tree_id in sorted(tree_ids):
        row = by_id.get(tree_id)
        if not row:
            continue
        modifier_type = integer(row["Type"])
        asset = integer(row["Asset"])
        if modifier_type == 272 and asset:
            content_tuning_ids.add(asset)
        lines.append(
            f"    [{tree_id}] = {{ parent = {integer(row['Parent'])}, operator = {integer(row['Operator'])}, "
            f"amount = {integer(row['Amount'])}, type = {modifier_type}, asset = {asset}, "
            f"secondaryAsset = {integer(row['SecondaryAsset'])}, "
            f"tertiaryAsset = {integer(row['TertiaryAsset'])} }},"
        )
    lines.append("}")
    write_lua(output / "Data" / profile_id / "ModifierTrees.lua", lines)
    return content_tuning_ids


def generate_supporting_data(
    output: Path,
    profile: dict[str, object],
    build: str,
    race_rows: list[dict[str, str]],
    content_tuning_rows: list[dict[str, str]],
    player_condition_rows: list[dict[str, str]],
    condition_ids: set[int],
    modifier_content_tuning_ids: set[int],
) -> None:
    profile_id = str(profile["id"])
    player_conditions = {integer(row["ID"]): row for row in player_condition_rows}
    content_tuning_ids = set(modifier_content_tuning_ids)
    for condition_id in condition_ids:
        row = player_conditions.get(condition_id)
        if row and integer(row.get("ContentTuningID", "0")):
            content_tuning_ids.add(integer(row["ContentTuningID"]))

    lines = generated_header("ChrRaces + ContentTuning", build, profile_id)
    lines.append("lib.RaceBits = {")
    for row in sorted(race_rows, key=lambda item: integer(item["ID"])):
        bit_index = integer(row.get("PlayableRaceBit", "-1"))
        if bit_index >= 0:
            lines.append(f"    [{integer(row['ID'])}] = {bit_index},")
    lines.extend(["}", "", "lib.ContentTuning = {"])
    content_by_id = {integer(row["ID"]): row for row in content_tuning_rows}
    for tuning_id in sorted(content_tuning_ids):
        row = content_by_id.get(tuning_id)
        if not row:
            continue
        lines.append(
            f"    [{tuning_id}] = {{ minLevel = {integer(row['MinLevelSquish'])}, "
            f"maxLevel = {integer(row['MaxLevelSquish'])}, "
            f"minLevelOffset = {integer(row.get('MinLevelScalingOffset', '0'))}, "
            f"maxLevelOffset = {integer(row.get('MaxLevelScalingOffset', '0'))} }},"
        )
    lines.append("}")
    write_lua(output / "Data" / profile_id / "SupportingData.lua", lines)


def generate_locales(
    output: Path,
    profile: dict[str, object],
    build: str,
    included_ids: set[int],
    locale_rows: dict[str, list[dict[str, str]]],
) -> None:
    profile_id = str(profile["id"])
    en_names = {
        integer(row["ID"]): row.get("Name_lang", "").strip()
        for row in locale_rows["enUS"]
    }
    for locale in LOCALES:
        localized = {
            integer(row["ID"]): row.get("Name_lang", "").strip()
            for row in locale_rows[locale]
        }
        lines = generated_header("TaxiNodes", build, profile_id)
        lines.extend(
            [
                f"if GetLocale() ~= {lua_string(locale)} then return end",
                "",
                "lib.Names = {",
            ]
        )
        for node_id in sorted(included_ids):
            name = localized.get(node_id) or en_names.get(node_id) or ""
            lines.append(f"    [{node_id}] = {lua_string(name)},")
        lines.append("}")
        write_lua(output / "Locale" / profile_id / f"{locale}.lua", lines)


def generate_profile(
    output: Path,
    profile: dict[str, object],
    build: str,
    cache_dir: Path | None,
    locale_fallback_build: str | None,
) -> None:
    if not BUILD_PATTERN.fullmatch(build):
        raise ValueError(f"Invalid Blizzard build: {build!r}")

    tables = {
        "PlayerCondition": download_csv("PlayerCondition", build, "enUS", cache_dir),
        "ModifierTree": download_csv("ModifierTree", build, "enUS", cache_dir),
        "Map": download_csv("Map", build, "enUS", cache_dir),
        "ChrRaces": download_csv("ChrRaces", build, "enUS", cache_dir),
        "ContentTuning": download_csv("ContentTuning", build, "enUS", cache_dir),
    }
    locale_rows = {
        "enUS": download_csv("TaxiNodes", build, "enUS", cache_dir),
    }
    use_profile_locales = profile.get("localized") is not False
    if not use_profile_locales:
        print(
            f"Profile {profile['id']} uses localized names from "
            f"{locale_fallback_build or 'enUS'}.",
            file=sys.stderr,
        )
    for locale in LOCALES:
        if locale == "enUS":
            continue
        if use_profile_locales:
            try:
                locale_rows[locale] = download_csv(
                    "TaxiNodes",
                    build,
                    locale,
                    cache_dir,
                    attempts=1 if locale_fallback_build else 3,
                    timeout=45 if locale_fallback_build else 120,
                )
                continue
            except (OSError, TimeoutError, ValueError) as error:
                use_profile_locales = False
                print(
                    f"Localized exports are unavailable for {profile['id']} ({build}): "
                    f"{error}. Falling back to {locale_fallback_build or 'enUS'}.",
                    file=sys.stderr,
                )
        if locale_fallback_build:
            locale_rows[locale] = download_csv(
                "TaxiNodes", locale_fallback_build, locale, cache_dir
            )
        else:
            locale_rows[locale] = locale_rows["enUS"]

    base_nodes = locale_rows["enUS"]
    dev_maps = {
        integer(row["ID"])
        for row in tables["Map"]
        if classify_map(row)
    }
    included: list[dict[str, str]] = []
    excluded: list[tuple[dict[str, str], str]] = []
    for row in base_nodes:
        reason = classify_taxi(row, dev_maps)
        if reason:
            excluded.append((row, reason))
        else:
            included.append(row)

    condition_ids, tree_ids, missing_conditions = collect_condition_data(
        included,
        tables["PlayerCondition"],
        tables["ModifierTree"],
    )
    included_ids = {integer(row["ID"]) for row in included}

    generate_nodes(output, profile, build, included, excluded, missing_conditions)
    generate_conditions(output, profile, build, tables["PlayerCondition"], condition_ids)
    modifier_content_tuning_ids = generate_modifier_trees(
        output, profile, build, tables["ModifierTree"], tree_ids
    )
    generate_supporting_data(
        output,
        profile,
        build,
        tables["ChrRaces"],
        tables["ContentTuning"],
        tables["PlayerCondition"],
        condition_ids,
        modifier_content_tuning_ids,
    )
    generate_locales(output, profile, build, included_ids, locale_rows)

    print(
        f"Generated profile {profile['id']} ({build}): {len(included)} taxi nodes; "
        f"excluded {len(excluded)} development nodes; "
        f"included {len(condition_ids) - len(missing_conditions)} player conditions and "
        f"{len(tree_ids)} modifier-tree rows.",
        file=sys.stderr,
    )
    if missing_conditions:
        print(
            "Referenced PlayerCondition rows missing from the Wago export: "
            + ", ".join(map(str, sorted(missing_conditions))),
            file=sys.stderr,
        )


def main() -> int:
    args = parse_args()
    if args.all and (args.build or args.product):
        raise ValueError("--all cannot be combined with --build or --product")

    profiles = load_profiles()
    by_id = {str(profile["id"]): profile for profile in profiles}
    if args.all:
        selected = [profile for profile in profiles if profile.get("product")]
    else:
        selected = [by_id[args.profile or "retail"]]

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for profile in selected:
        product = args.product or profile.get("product")
        build = args.build
        if not build:
            if not product:
                raise ValueError(
                    f"Profile {profile['id']!r} has no active Blizzard product; pass --build"
                )
            build = get_product_build(str(product), args.region)
        fallback_profile = next(
            (
                candidate
                for candidate in profiles
                if candidate.get("gameType") == profile.get("gameType")
                and candidate.get("default")
                and candidate.get("build")
            ),
            None,
        )
        locale_fallback_build = None
        if fallback_profile and fallback_profile is not profile:
            locale_fallback_build = str(fallback_profile["build"])
        generate_profile(
            output,
            profile,
            build,
            args.cache_dir,
            locale_fallback_build,
        )
        profile["build"] = build

    assign_data_sets(output, profiles)
    save_profiles(profiles)
    generate_client_profiles(output, profiles)
    update_toc(output, profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
