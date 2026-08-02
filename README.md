# LibTaxiData

LibTaxiData is a standalone Retail World of Warcraft addon and reusable global
API for localized flight-master data. It provides taxi names in every client
language, raw DB2 metadata, character-aware condition evaluation, coordinate
conversion, nearest-node searches, and native Blizzard waypoints.

It is autonomous: no LibStub, HereBeDragons, or other addon is required.

[![Discord](https://github.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/assets/43384589/f9fc38ba-26b0-4669-a584-ce56f0bf57d6)](https://discord.gg/YgcdybKdWX)
[![GitHub](https://github.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/assets/43384589/2c9d96ac-f38a-4442-9dfc-cc6b3ce36981)](https://github.com/Azeroth-Pilot-Reloaded/LibTaxiData)
[![CurseForge](https://github.com/user-attachments/assets/1bae5d08-d88b-403a-b902-ad3aa5c55248)](https://www.curseforge.com/wow/addons/libtaxidata)
[![Patreon](https://github.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/assets/43384589/8431a849-5507-4489-b6ab-f3b7993ef4ef)](https://www.patreon.com/AzerothPilotReloaded)

![Features](https://github.com/user-attachments/assets/a3af1185-9b5d-411a-8b14-60a0a21249f9)

- **Standalone addon:** install the `LibTaxiData` folder directly under
  `Interface/AddOns`; `LibTaxiData.toc` loads the API for consumers.
- **Localized taxi names:** `enUS`, `enGB`, `deDE`, `esES`, `esMX`, `frFR`,
  `itIT`, `koKR`, `ptBR`, `ruRU`, `zhCN`, and `zhTW`, with an `enUS` fallback
  applied while generating data.
- **Complete node metadata:** positions, map offsets, flags, texture IDs,
  faction mounts, PlayerCondition references, visibility conditions, and audit
  records for deliberately excluded development nodes.
- **Character-aware results:** faction, race, class, level, quest, reputation,
  item, spell, achievement, covenant, and supported ModifierTree requirements.
- **Navigation helpers:** local-map/world/APR coordinate conversion, nearest
  usable taxi searches, and native Blizzard user waypoints.

![Settings & Commands](https://github.com/user-attachments/assets/f691f4d2-d9ee-4a14-8135-2d85a0334c6b)

Use `/ltd` or `/libtaxidata` in chat. Local coordinates accept either normalized
values (`0.438 0.682`) or percentages (`43.8 68.2`).

| Command                                             | What it does                                                                                                                                                                                    |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/ltd name <nodeID>`                                | Prints only the localized node name.                                                                                                                                                            |
| `/ltd node <nodeID> [uiMapID]`                      | Prints the localized name, all retained condition/flag/mount/offset/visual information, standard world coordinates, APR coordinates, and optional local map coordinates. `details` is an alias. |
| `/ltd nearest`                                      | Finds the nearest usable taxi to the player, prints its name/distance, and sets a Blizzard waypoint.                                                                                            |
| `/ltd nearest <uiMapID> <x> <y>`                    | Finds the nearest taxi from normalized or percentage local map coordinates and sets a waypoint.                                                                                                 |
| `/ltd nearest world <instanceID> <worldX> <worldY>` | Finds the nearest taxi from conventional world coordinates. A waypoint is set when the node can be resolved on the current map hierarchy.                                                       |
| `/ltd waypoint <nodeID> [uiMapID]`                  | Sets and super-tracks a native Blizzard waypoint on the requested node.                                                                                                                         |
| `/ltd help`                                         | Prints the command list.                                                                                                                                                                        |

## Public API

The addon exposes `_G.LibTaxiData_API`. It does not register a LibStub major and
there is no minimum data-version constant for consumers to maintain.

```lua
local taxi = _G.LibTaxiData_API

local name = taxi.GetNodeName(2)
local raw = taxi.GetAllNodeData(2)
local details = taxi.GetNodeDetails(2, 84)

local nearest = taxi.FindNearestNodeToPlayer()
if nearest then
    taxi.SetWaypointToNode(nearest.nodeID)
end
```

### Node data

| API                                                       | Result                                                                                                                               |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `GetNode(nodeID)` / `GetAllNodeData(nodeID)`              | Raw generated TaxiNodes record with every retained DB2 field.                                                                        |
| `GetAllNodes()`                                           | Raw node table keyed by node ID.                                                                                                     |
| `GetNodeDetails(nodeID[, uiMapID])`                       | Copy of all raw fields enriched with `nodeID`, localized name, world/APR/map positions, availability, visibility, and faction mount. |
| `GetNodeName(nodeID)`                                     | Name for the active WoW client locale.                                                                                               |
| `GetNodeWorldPosition(nodeID[, format])`                  | Standard world-position object, or APR format when `format` is `"apr-world"`.                                                        |
| `GetNodeAPRWorldPosition(nodeID)`                         | APR's historical swapped-axis world-position object.                                                                                 |
| `GetNodeMapPosition(nodeID, uiMapID[, allowOutOfBounds])` | Node position normalized to `0..1` on the requested UI map.                                                                          |
| `IterateNodes()`                                          | `next` iterator over retained nodes.                                                                                                 |
| `GetExcludedNode(nodeID)`                                 | Excluded development-node name and audit reason.                                                                                     |
| `GetSource()`                                             | Current build, provider, DB2 table, and row counts.                                                                                  |

### Coordinate formats

Every object contains a `coordinateSystem` field. The names are also available
through `API.COORDINATE_FORMATS`.

| Format      | Shape                                       | Meaning                                                                                 |
| ----------- | ------------------------------------------- | --------------------------------------------------------------------------------------- |
| `world`     | `{ x = worldX, y = worldY, z, instanceID }` | Conventional TaxiNodes/HereBeDragons world coordinates in yards.                        |
| `apr-world` | `{ x = worldY, y = worldX, z, instanceID }` | APR's historical storage format, matching the return order handled from `UnitPosition`. |
| `map`       | `{ x = 0..1, y = 0..1, mapID, instanceID }` | Normalized coordinates on a specific UI map.                                            |

The conversions use Retail's native `C_Map` API. Object-returning methods are
preferred because they preserve the coordinate system explicitly:

```lua
local world = taxi.MapToWorld(2437, 0.438, 0.682)
local localPosition = taxi.WorldToMap(
    world.instanceID,
    world.x,
    world.y,
    2437
)
```

For easy migration, the library also exposes HereBeDragons-style signatures:

```lua
local worldX, worldY, instanceID =
    taxi.GetWorldCoordinatesFromZone(0.438, 0.682, 2437)

local mapX, mapY = taxi.GetZoneCoordinatesFromWorld(worldX, worldY, 2437)
local sameMapX, sameMapY =
    taxi.GetZoneCoordinatesFromWorldInstance(worldX, worldY, instanceID, 2437)
```

### Nearest-node searches

| API                                                               | Origin format                       |
| ----------------------------------------------------------------- | ----------------------------------- |
| `FindNearestNodeToPlayer([options])`                              | Current player position.            |
| `FindNearestNodeFromMap(uiMapID, x, y[, options])`                | Local normalized map coordinates.   |
| `FindNearestNodeFromWorld(worldX, worldY, instanceID[, options])` | Conventional world coordinates.     |
| `FindNearestNodeFromAPRWorld(aprX, aprY, instanceID[, options])`  | APR swapped-axis world coordinates. |

A successful search returns `nodeID`, raw `node`, localized `name`, distance in
yards, both world formats, availability, visibility, and the origin when it is
known. By default the search excludes known-unavailable, hidden,
`END_POINT_ONLY`, and `IGNORE_FOR_FIND_NEAREST` nodes. An unevaluable server-only
condition remains eligible instead of being incorrectly rejected.

The optional table supports `includeUnavailable`, `includeUnknown = false`,
`includeHidden`, `includeEndpointOnly`, `includeIgnored`, `threeDimensional`,
`z`, and a custom `filter(nodeID, node, availability, visibility)` callback.

### Conditions

`IsNodeAvailable`, `IsNodeVisible`, `EvaluatePlayerCondition`, and
`EvaluateModifierTree` use tri-state results:

- `true`: all known requirements pass;
- `false`: at least one requirement is known to fail;
- `nil`: the public addon API cannot safely evaluate a server-only requirement.

The library never turns an unknown phase, WorldStateExpression, objective,
AreaTable, or other server-only state into a false positive.

##

![Credits](https://github.com/user-attachments/assets/e1e2c4f3-9e84-40fe-af3b-618a0d2a948f)

**Development**

- Neoldric - developer

**Data and tooling**

- Blizzard Entertainment - World of Warcraft client APIs and public build feed
- [Wago Tools](https://wago.tools/) - Versioned DB2 exports
- [BigWigsMods Packager](https://github.com/BigWigsMods/packager) - Multi-platform packaging and deployment
