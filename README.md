# LibTaxiData

LibTaxiData is a standalone multi-client World of Warcraft addon and reusable
global API for localized flight-master data. It provides taxi names in every
client language, raw DB2 metadata, character-aware condition evaluation,
coordinate conversion, nearest-node searches, and native Blizzard waypoints.

It is autonomous: no LibStub, HereBeDragons, or other addon is required.

[![Discord](https://github.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/assets/43384589/f9fc38ba-26b0-4669-a584-ce56f0bf57d6)](https://discord.gg/YgcdybKdWX)
[![GitHub](https://github.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/assets/43384589/2c9d96ac-f38a-4442-9dfc-cc6b3ce36981)](https://github.com/Azeroth-Pilot-Reloaded/LibTaxiData)
[![CurseForge](https://github.com/user-attachments/assets/1bae5d08-d88b-403a-b902-ad3aa5c55248)](https://www.curseforge.com/wow/addons/libtaxidata)
[![Patreon](https://github.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/assets/43384589/8431a849-5507-4489-b6ab-f3b7993ef4ef)](https://www.patreon.com/AzerothPilotReloaded)

![Features](https://github.com/user-attachments/assets/a3af1185-9b5d-411a-8b14-60a0a21249f9)

- **Standalone addon:** install the `LibTaxiData` folder directly under
  `Interface/AddOns`; `LibTaxiData.toc` loads the API for consumers.
- **Multi-client profiles:** Retail Live/PTR, Mists of Pandaria Classic
  Live/PTR, Classic Era, and Burning Crusade Anniversary data are generated and
  selected automatically. Wrath and Cataclysm remain registered as base clients
  without fake servers; additional Live, PTR, Beta, or archived profiles can be
  attached when needed.
- **Small versioned releases:** published ZIPs contain one compatible data set,
  not every generated client database. Builds are grouped only when their
  complete node, condition, and locale fingerprints are identical.
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
| `GetClientInfo()`                                         | Selected profile/data set, game type, channel, detected build, and exact/fallback selection state.                                  |

### Coordinate formats

Every object contains a `coordinateSystem` field. The names are also available
through `API.COORDINATE_FORMATS`.

| Format      | Shape                                       | Meaning                                                                                 |
| ----------- | ------------------------------------------- | --------------------------------------------------------------------------------------- |
| `world`     | `{ x = worldX, y = worldY, z, instanceID }` | Conventional TaxiNodes/HereBeDragons world coordinates in yards.                        |
| `apr-world` | `{ x = worldY, y = worldX, z, instanceID }` | APR's historical storage format, matching the return order handled from `UnitPosition`. |
| `map`       | `{ x = 0..1, y = 0..1, mapID, instanceID }` | Normalized coordinates on a specific UI map.                                            |

The conversions use the clients' native `C_Map` API. Object-returning methods are
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

## Client profiles and data generation

`GetBuildInfo()` and `WOW_PROJECT_ID` select the active data profile. Exact
build matching distinguishes Live, PTR, and Beta clients that share the same
WoW project ID. `profile` describes the client build while `dataSet` identifies
the data embedded in the installed archive. A newer ungenerated build uses the
only safe fallback embedded for that base version and reports `fallback = true`
through `GetClientInfo()`.

The catalog deliberately separates permanent client versions from temporary
servers/builds:

- `tools/versions.json` contains every supported base client, even when no
  Blizzard server currently exists for it;
- `tools/profiles.json` contains the Live, PTR, Beta, or archived server builds
  that can actually generate a data set.

The generator, runtime manifest, TOC, tests, update workflow, and release plan
consume both catalogs. Useful catalog commands are:

```sh
python tools/profiles.py list
python tools/profiles.py check
python tools/package.py --matrix
```

The list command also shows whether a profile is currently publishable and as
which release type. The release rules are:

- a normal profile is published as a stable release;
- a `ptr` profile is published as Beta when its complete build is strictly
  greater than its `releaseBase` build;
- a `beta` profile is published as Alpha under the same condition;
- a PTR/Beta profile without `releaseBase` is a standalone prerelease and is
  published using its channel;
- a PTR/Beta profile whose complete build is older or equal to its
  `releaseBase` remains available to the generator/runtime but is omitted.

All four components of a Blizzard build are compared in order. For example,
`12.1.0.68914` is newer than `12.0.7.68974`. Publishable bundles are uploaded
sequentially from the smallest to the largest complete build.

### Adding a base version

Add a base client to `tools/versions.json` once, then run
`python tools/profiles.py sync`. It is included in `Data/ClientProfiles.lua`,
so the runtime can detect it from `WOW_PROJECT_ID` or its interface major even
if there is no corresponding server profile.

| Field | Required | Meaning and source |
| --- | --- | --- |
| `id` | yes | Permanent lowercase identifier referenced by server profiles, for example `anniversary`. |
| `name` | yes | Human-readable base-client name. |
| `gameType` | yes | Value accepted by WoW's TOC `AllowLoadGameType`, such as `mainline`, `classic`, `tbc`, `wrath`, `cata`, or `mists`. |
| `projectConstant` | yes | Client global whose value can equal `WOW_PROJECT_ID`, for example `WOW_PROJECT_MISTS_CLASSIC`. Inspect both values in-game with `/dump WOW_PROJECT_ID` and `/dump WOW_PROJECT_MISTS_CLASSIC`. |
| `apiFamily` | yes | Preferred adapter order: `modern` tries namespaced `C_*` APIs first; `legacy` tries historical global functions first. Missing or failing calls always fall back to the other implementation. |
| `interfaceMajor` | one rule | Exact first component returned by `GetBuildInfo()`, normally `1` through `5` for Classic branches. |
| `minimumInterfaceMajor` | one rule | Open-ended interface rule used by Retail. Only one base version can define it. |
| `tocInterface` | yes | Last known compatible full TOC interface. It keeps the common API loadable when the base has no active server; active profile interfaces are added automatically. |
| `tocLabel` | Classic branches | Suffix used for `## Interface-<label>` in the TOC, for example `Mists`. |
| `apiOverrides` | no | Per-feature `modern`/`legacy` preference when this client differs from its general `apiFamily`. Supported keys are `questCompleted`, `questLog`, `questReady`, `auras`, `spellBook`, `items`, `currency`, and `reputation`. |

The base registry currently covers Retail, Classic Era, Anniversary/Burning
Crusade, Wrath, Cataclysm, and Mists. Wrath and Cataclysm intentionally have no
server profile: they remain detectable with their legacy-first API policy and
report `supported = false` until data is attached to a profile.

`Compatibility.lua` centralizes APIs whose signatures/names changed between
clients. It records the implementation actually found in
`GetClientInfo().apiCapabilities`. Map conversion, player position, and
waypoints are also capability-probed at runtime. When Blizzard changes an API,
add its adapter there; use `apiOverrides` only when a particular base client
must prefer a different valid implementation.

### Adding a profile

Add one object to `tools/profiles.json`. These fields are supported:

| Field | Required | Meaning and source |
| --- | --- | --- |
| `id` | yes | Stable lowercase identifier used by commands and generated directories, for example `retail_ptr`. |
| `name` | yes | Human-readable label shown by `tools/profiles.py list`. |
| `version` | yes | `id` from `tools/versions.json`; this supplies the game type, project constant, interface rule, and API policy. |
| `channel` | yes | `live`, `ptr`, `beta`, or `legacy`. It controls the release type. |
| `product` | yes | Blizzard product-feed code, such as `wow`, `wowt`, or `wow_classic_ptr`; use `null` only for an archived client without a feed. |
| `build` | yes | Use `null` for a new active profile and let the generator resolve it, or provide an exact four-part archived build. |
| `releaseBase` | to publish PTR/Beta | `id` of the related normal profile. It must use the same base `version`. |
| `default` | no | Set `true` on the single safe fallback profile for a base version; normally omit it on PTR/Beta entries. |
| `localized` | no | Set `false` when localized DB2 exports are unavailable so locale names fall back to the normal build. |
| `dataSet` | no | Always omit this on a new profile. The generator assigns it after comparing complete generated fingerprints. |

Example for re-adding a Retail Beta later:

```json
{
  "id": "retail_beta",
  "name": "Retail Beta",
  "version": "retail",
  "channel": "beta",
  "product": "wow_beta",
  "build": null,
  "releaseBase": "retail",
  "localized": false
}
```

Example for attaching archived data to the already-declared Wrath base client:

```json
{
  "id": "wrath_archive",
  "name": "Wrath Classic archived build",
  "version": "wrath",
  "channel": "legacy",
  "product": null,
  "build": "3.4.3.XXXXX",
  "default": true
}
```

Replace `XXXXX` with the real final build number. Until this object and its
generated data exist, the base client is recognized but deliberately has no
taxi data fallback.

The product code is the segment used by Blizzard's public version endpoint,
`https://us.version.battle.net/<product>/versions`. Test a product and inspect
its current EU build with:

```sh
python tools/live_build.py --product wow_beta --region eu
```

The exact build is also returned by WoW's `GetBuildInfo()` and is visible in the
client's `.build.info`. The generator verifies that Wago Tools exposes the
required DB2 tables for that build.

Generate the new entry after saving the catalog:

```sh
python tools/generate.py --profile retail_beta --cache-dir .cache/db2
python tools/profiles.py check
```

After every successful generation, the script stores the resolved build back
in `tools/profiles.json`, recalculates `dataSet`, regenerates
`Data/ClientProfiles.lua`, and updates all generated interface/profile blocks in
`LibTaxiData.toc`. The TOC interface is derived from the first three build
components; a change limited to the final build number correctly leaves the
interface unchanged.

To remove a profile, delete its catalog object and synchronize with pruning:

```sh
python tools/profiles.py sync --prune
```

Builds without an explicit `--build` are resolved from Blizzard's public
product feeds:

```sh
# Update one active branch from Blizzard's feed.
python tools/generate.py --profile classic --cache-dir .cache/db2

# Generate the exact examples used by Classic Era and Mists Classic.
python tools/generate.py --profile classic --build 1.15.9.68940
python tools/generate.py --profile mists --build 5.5.4.68806

# Refresh every profile backed by an active Blizzard product.
python tools/generate.py --all --cache-dir .cache/db2

# A no-server base version first needs a profile with product=null and an exact
# build. It can then be generated normally.
python tools/generate.py --profile wrath_archive --build 3.4.3.XXXXX
```

Release archives are built separately:

```sh
# Build every minimal release ZIP under dist/.
python tools/package.py --build

# Build only the Classic Era archive.
python tools/package.py --build --data-set classic
```

The repository retains raw per-profile exports so the generator can compare
them. These raw exports are not all shipped. `tools/package.py` creates one
archive per unique `(dataSet, release type)`, trims the TOC and runtime manifest,
and includes only the matching `Data/<dataSet>` and `Locale/<dataSet>`
directories. Identical Live and PTR data can therefore share storage in the
repository while still following different publication channels.

Older DB2 layouts are normalized while generating data. Fields absent from a
client schema, such as Classic's `MinimapAtlasMemberID` and historical content
tuning offsets, receive neutral zero values so the public node shape remains
stable across profiles. If localized PTR/Beta exports are unavailable, names
fall back to the Live build of the same base version; numeric node and condition
data always come from the requested build.

##

![Credits](https://github.com/user-attachments/assets/e1e2c4f3-9e84-40fe-af3b-618a0d2a948f)

**Development**

- Neoldric - developer

**Data and tooling**

- Blizzard Entertainment - World of Warcraft client APIs and public build feed
- [Wago Tools](https://wago.tools/) - Versioned DB2 exports
- [BigWigsMods Packager](https://github.com/BigWigsMods/packager) - Multi-platform packaging and deployment
