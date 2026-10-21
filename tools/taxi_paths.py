"""Build compact, directed taxi connections from build-pinned DB2 exports.

Geometry is a polyline estimate, not the client flight spline or a measured ETA.
Manual source files are maintained separately from generated data.
"""
from __future__ import annotations

import json
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_SPEED = 32.0


def _integer(row, field):
    value = row.get(field)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing TaxiPath field {field}")
    result = int(value)
    if result < 0:
        raise ValueError(f"Negative TaxiPath field {field}: {value}")
    return result


def load_manual(root: Path, data_set: str) -> dict:
    path = root / "tools" / "manual" / f"{data_set}.json"
    if not path.exists():
        return {"schemaVersion": 1, "nodes": {}}
    manual = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(manual, dict) or manual.get("schemaVersion") != 1 or not isinstance(manual.get("nodes"), dict):
        raise ValueError(f"Invalid manual taxi catalog: {path}")
    if "complete" in manual and not isinstance(manual["complete"], bool):
        raise ValueError("Manual catalog complete must be a boolean")
    unknown = set(manual) - {"schemaVersion", "nodes", "complete", "description"}
    if unknown:
        raise ValueError(f"Unknown manual catalog fields: {sorted(unknown)}")
    return manual


def _geometry(rows: list[dict], speed: float) -> dict:
    if len(rows) < 2:
        return {"durationSource": "unknown"}
    ordered = sorted(rows, key=lambda row: _integer(row, "NodeIndex"))
    indices = [_integer(row, "NodeIndex") for row in ordered]
    if len(set(indices)) != len(indices):
        raise ValueError("Duplicate TaxiPathNode NodeIndex")
    # Missing nodes and world transitions cannot produce a complete estimate.
    if indices != list(range(indices[0], indices[-1] + 1)):
        return {"durationSource": "unknown"}
    length = 0.0
    delay = 0.0
    previous = None
    cross_world = False
    has_teleports = False
    for row in ordered:
        coords = tuple(float(row[f"Loc_{index}"]) for index in range(3))
        if not all(math.isfinite(value) for value in coords):
            raise ValueError("Non-finite TaxiPathNode coordinate")
        world = _integer(row, "ContinentID")
        delay += _integer(row, "Delay")
        if previous:
            if previous[0] != world:
                cross_world = True
            elif previous[2] & 1:
                # TrinityCore DBCEnums.h: TAXI_PATH_NODE_FLAG_TELEPORT = 0x1.
                # TaxiPathGraph excludes the segment after a teleport node.
                has_teleports = True
            else:
                length += math.dist(previous[1], coords)
        previous = world, coords, _integer(row, "Flags")
    if cross_world:
        return {"durationSource": "unknown", "crossWorld": True}
    return {
        "distanceYards": round(length, 3),
        "delaySeconds": round(delay, 3),
        "durationSeconds": round(length / speed + delay, 3),
        "durationSource": "geometry-estimate",
        "hasTeleports": has_teleports,
    }


def build_paths(path_rows: list[dict], point_rows: list[dict], node_ids: set[int],
                manual: dict, build: str, speed: float = DEFAULT_SPEED):
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError("Taxi estimate speed must be positive and finite")
    points = defaultdict(list)
    for row in point_rows:
        points[_integer(row, "PathID")].append(row)
    paths = {}
    excluded = []
    seen = set()
    for row in path_rows:
        path_id = _integer(row, "ID")
        if path_id in seen:
            raise ValueError(f"Duplicate TaxiPath ID {path_id}")
        seen.add(path_id)
        origin, target = _integer(row, "FromTaxiNode"), _integer(row, "ToTaxiNode")
        if origin not in node_ids or target not in node_ids or origin == target:
            excluded.append({"id": path_id, "fromNodeID": origin, "toNodeID": target,
                             "reason": "excluded-endpoint" if origin != target else "same-node"})
            continue
        record = {"fromNodeID": origin, "toNodeID": target,
                  "basePriceCopper": _integer(row, "Cost"), "priceSource": "db2-base"}
        record.update(_geometry(points[path_id], speed))
        paths[path_id] = record
    manual_count = 0
    manual_ids = set()
    for origin_text, node in sorted(manual.get("nodes", {}).items()):
        origin = int(origin_text)
        if origin not in node_ids or not isinstance(node, dict) or set(node) - {"outgoing", "name"}:
            raise ValueError(f"Invalid manual departure node {origin_text}")
        if not isinstance(node.get("outgoing", []), list):
            raise ValueError(f"Manual node {origin} outgoing must be a list")
        for override in node.get("outgoing", []):
            if not isinstance(override, dict):
                raise ValueError("Each manual outgoing path must be an object")
            allowed = {"id", "toNodeID", "basePriceCopper", "durationSeconds", "source", "verifiedBuild", "disabled"}
            if set(override) - allowed:
                raise ValueError(f"Unknown manual taxi fields: {set(override) - allowed}")
            target = int(override["toNodeID"])
            if target not in node_ids or target == origin:
                raise ValueError(f"Invalid manual taxi arrival {origin}->{target}")
            path_id = override.get("id", f"manual:{origin}:{target}")
            if isinstance(path_id, bool) or not isinstance(path_id, (int, str)):
                raise ValueError("Manual path id must be a DB2 integer or manual: string")
            if isinstance(path_id, str) and not path_id.startswith("manual:"):
                raise ValueError("Manual string ids must start with manual:")
            if path_id in manual_ids:
                raise ValueError(f"Duplicate manual path id {path_id}")
            manual_ids.add(path_id)
            current = paths.get(path_id)
            if current and (current["fromNodeID"], current["toNodeID"]) != (origin, target):
                raise ValueError(f"Manual override changes endpoints of {path_id}")
            if override.get("disabled"):
                paths.pop(path_id, None)
                manual_count += 1
                continue
            active = {key: override[key] for key in ("basePriceCopper", "durationSeconds")
                      if override.get(key) is not None}
            if not active and current:
                continue
            if not isinstance(override.get("source"), str) or not override["source"].strip() or not isinstance(override.get("verifiedBuild"), str) or not override["verifiedBuild"].strip():
                raise ValueError(f"Manual path {path_id} requires source and verifiedBuild")
            if isinstance(path_id, int) and not current and not manual.get("complete"):
                raise ValueError(f"Manual addition {path_id} must use a manual: id when DB2 path is absent")
            record = dict(current or {"fromNodeID": origin, "toNodeID": target, "durationSource": "unknown"})
            for key, value in active.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f"Invalid manual {key} on {path_id}")
                if key == "basePriceCopper" and value != int(value):
                    raise ValueError("Manual prices must be integer copper")
                record[key] = value
                record["priceSource" if key == "basePriceCopper" else "durationSource"] = "manual"
            record["manualSource"] = override["source"]
            record["verifiedBuild"] = override["verifiedBuild"]
            paths[path_id] = record
            manual_count += 1
    semantic = [[key, paths[key]] for key in sorted(paths, key=lambda key: (isinstance(key, str), key))]
    content_fingerprint = hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    counts = Counter(record["fromNodeID"] for record in paths.values())
    report = {
        "schemaVersion": 1, "build": build, "pathCount": len(paths), "fingerprint": content_fingerprint,
        "excludedPathCount": len(excluded), "manualPathCount": manual_count,
        "estimatedDurationCount": sum(record.get("durationSource") == "geometry-estimate" for record in paths.values()),
        "unknownDurationCount": sum("durationSeconds" not in record for record in paths.values()),
        "unknownPriceCount": sum("basePriceCopper" not in record for record in paths.values()),
        "estimateSpeedYardsPerSecond": speed,
        "nodes": {str(node): {"outgoingCount": counts[node],
                             "unknownDurationPaths": [key for key, record in paths.items() if record["fromNodeID"] == node and "durationSeconds" not in record],
                             "unknownPricePaths": [key for key, record in paths.items() if record["fromNodeID"] == node and "basePriceCopper" not in record]}
                  for node in sorted(node_ids)},
        "excludedPaths": excluded,
    }
    return paths, report


def _lua(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def generate_paths(output: Path, profile: dict, build: str, path_rows: list[dict],
                   point_rows: list[dict], node_ids: set[int], manual: dict):
    data_set = str(profile["id"])
    paths, report = build_paths(path_rows, point_rows, node_ids, manual, build)
    lines = [
        "-- This file is generated. Do not edit it by hand.",
        f"-- Source: https://wago.tools/db2/TaxiPath + TaxiPathNode (build {build})",
        "-- Prices are base copper. Geometry durations are estimates at 32 yards/second.",
        "-- A DB2 connection is not proof that a character is offered this flight.",
        "local lib = _G.LibTaxiData_Internal", "if not lib then return end",
        f"if not lib.Client or lib.Client.dataSet ~= {_lua(data_set)} then return end", "",
        "lib.Paths = {",
    ]
    for path_id in sorted(paths, key=lambda key: (isinstance(key, str), key)):
        values = ", ".join(f"{key} = {_lua(value)}" for key, value in paths[path_id].items())
        lines.append(f"    [{_lua(path_id)}] = {{ {values} }},")
    lines.extend(["}", "", "lib.Source.paths = {"])
    for key in ("fingerprint", "pathCount", "excludedPathCount", "manualPathCount", "estimatedDurationCount", "unknownDurationCount", "unknownPriceCount", "estimateSpeedYardsPerSecond"):
        lines.append(f"    {key} = {_lua(report[key])},")
    lines.extend(['    tables = "TaxiPath + TaxiPathNode",', "}", ""])
    target = output / "Data" / data_set / "TaxiPaths.lua"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    coverage = output / "readme" / "coverage" / f"{data_set}.json"
    coverage.parent.mkdir(parents=True, exist_ok=True)
    coverage.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return report
