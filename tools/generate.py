#!/usr/bin/env python3
"""Generate LibTaxiData from Wago Tools DB2 CSV exports.

The generator intentionally has no third-party Python dependency. It uses an
explicit build when supplied and otherwise resolves the current Retail build
from Blizzard, so a newer PTR/Beta export can never silently replace live data.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from pathlib import Path

from live_build import BUILD_PATTERN, get_live_build


WAGO_CSV_URL = "https://wago.tools/db2/{table}/csv?build={build}&locale={locale}"
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
    parser.add_argument(
        "--build",
        help="Exact Wago/Blizzard build. Defaults to Blizzard's live Retail build.",
    )
    parser.add_argument(
        "--region",
        default="eu",
        help="Retail region used for automatic build detection (default: eu)",
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


def download_csv(table: str, build: str, locale: str, cache_dir: Path | None) -> list[dict[str, str]]:
    cache_path = None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{table}-{build}-{locale}.csv"

    if cache_path and cache_path.exists():
        payload = cache_path.read_bytes()
    else:
        url = WAGO_CSV_URL.format(
            table=urllib.parse.quote(table),
            build=urllib.parse.quote(build),
            locale=urllib.parse.quote(locale),
        )
        request = urllib.request.Request(url, headers={"User-Agent": "LibTaxiData generator"})
        print(f"Downloading {table} ({locale}, {build})...", file=sys.stderr)
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        if cache_path:
            cache_path.write_bytes(payload)

    text = payload.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


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


def generated_header(table: str, build: str) -> list[str]:
    return [
        "-- This file is generated. Do not edit it by hand.",
        f"-- Source: https://wago.tools/db2/{table} (build {build})",
        "local lib = _G.LibTaxiData_Internal",
        "if not lib then return end",
        "",
    ]


def write_lua(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def update_toc_interface(output: Path, build: str) -> None:
    version_parts = build.split(".")
    if len(version_parts) != 4 or not all(part.isdigit() for part in version_parts):
        raise ValueError(f"Invalid Blizzard build: {build!r}")
    major, minor, patch = map(int, version_parts[:3])
    interface = major * 10000 + minor * 100 + patch
    toc_path = output / "LibTaxiData.toc"
    if not toc_path.exists():
        return
    toc = toc_path.read_text(encoding="utf-8-sig")
    toc, replacements = re.subn(
        r"^## Interface:.*$",
        f"## Interface: {interface}",
        toc,
        count=1,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise RuntimeError(f"Interface metadata not found in {toc_path}")
    toc_path.write_text(toc, encoding="utf-8", newline="\n")


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
    build: str,
    nodes: list[dict[str, str]],
    excluded: list[tuple[dict[str, str], str]],
    missing_conditions: set[int],
) -> None:
    lines = generated_header("TaxiNodes", build)
    lines.extend(
        [
            "lib.Source = {",
            f"    build = {lua_string(build)},",
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
        fields = ", ".join(f"{name} = {numeric(row[column])}" for name, column in NODE_FIELDS)
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
    write_lua(output / "Data" / "TaxiNodes.lua", lines)


def generate_conditions(
    output: Path,
    build: str,
    rows: list[dict[str, str]],
    condition_ids: set[int],
) -> None:
    by_id = {integer(row["ID"]): row for row in rows}
    lines = generated_header("PlayerCondition", build)
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
    write_lua(output / "Data" / "PlayerConditions.lua", lines)


def generate_modifier_trees(
    output: Path,
    build: str,
    rows: list[dict[str, str]],
    tree_ids: set[int],
) -> set[int]:
    by_id = {integer(row["ID"]): row for row in rows}
    content_tuning_ids: set[int] = set()
    lines = generated_header("ModifierTree", build)
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
    write_lua(output / "Data" / "ModifierTrees.lua", lines)
    return content_tuning_ids


def generate_supporting_data(
    output: Path,
    build: str,
    race_rows: list[dict[str, str]],
    content_tuning_rows: list[dict[str, str]],
    player_condition_rows: list[dict[str, str]],
    condition_ids: set[int],
    modifier_content_tuning_ids: set[int],
) -> None:
    player_conditions = {integer(row["ID"]): row for row in player_condition_rows}
    content_tuning_ids = set(modifier_content_tuning_ids)
    for condition_id in condition_ids:
        row = player_conditions.get(condition_id)
        if row and integer(row.get("ContentTuningID", "0")):
            content_tuning_ids.add(integer(row["ContentTuningID"]))

    lines = generated_header("ChrRaces + ContentTuning", build)
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
            f"minLevelOffset = {integer(row['MinLevelScalingOffset'])}, "
            f"maxLevelOffset = {integer(row['MaxLevelScalingOffset'])} }},"
        )
    lines.append("}")
    write_lua(output / "Data" / "SupportingData.lua", lines)


def generate_locales(
    output: Path,
    build: str,
    included_ids: set[int],
    locale_rows: dict[str, list[dict[str, str]]],
) -> None:
    en_names = {
        integer(row["ID"]): row.get("Name_lang", "").strip()
        for row in locale_rows["enUS"]
    }
    for locale in LOCALES:
        localized = {
            integer(row["ID"]): row.get("Name_lang", "").strip()
            for row in locale_rows[locale]
        }
        lines = generated_header("TaxiNodes", build)
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
        write_lua(output / "Locale" / f"{locale}.lua", lines)


def main() -> int:
    args = parse_args()
    build = args.build or get_live_build(args.region)
    if not BUILD_PATTERN.fullmatch(build):
        raise ValueError(f"Invalid Blizzard build: {build!r}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    tables = {
        "PlayerCondition": download_csv("PlayerCondition", build, "enUS", args.cache_dir),
        "ModifierTree": download_csv("ModifierTree", build, "enUS", args.cache_dir),
        "Map": download_csv("Map", build, "enUS", args.cache_dir),
        "ChrRaces": download_csv("ChrRaces", build, "enUS", args.cache_dir),
        "ContentTuning": download_csv("ContentTuning", build, "enUS", args.cache_dir),
    }
    locale_rows = {
        locale: download_csv("TaxiNodes", build, locale, args.cache_dir)
        for locale in LOCALES
    }

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

    generate_nodes(output, build, included, excluded, missing_conditions)
    generate_conditions(output, build, tables["PlayerCondition"], condition_ids)
    modifier_content_tuning_ids = generate_modifier_trees(
        output, build, tables["ModifierTree"], tree_ids
    )
    generate_supporting_data(
        output,
        build,
        tables["ChrRaces"],
        tables["ContentTuning"],
        tables["PlayerCondition"],
        condition_ids,
        modifier_content_tuning_ids,
    )
    generate_locales(output, build, included_ids, locale_rows)
    update_toc_interface(output, build)

    print(
        f"Generated {len(included)} taxi nodes; excluded {len(excluded)} development nodes; "
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
