<a name="readme-top"></a>

<p align="center">
  <a href="https://www.curseforge.com/wow/addons/libtaxidata">
    <img src="readme/assets/banner-rounded.svg" alt="LibTaxiData" width="1000">
  </a>
</p>

<h1 align="center">Every flight. The right connection.</h1>

<p align="center">
  Localized flight-master data and navigation helpers for <strong>World of Warcraft</strong>.<br>
  Find a nearby taxi, inspect its requirements, or build flight-aware addons with a reusable API.
</p>

<p align="center">
  <a href="https://www.curseforge.com/wow/addons/libtaxidata"><img src="https://raw.githubusercontent.com/Azeroth-Pilot-Reloaded/APR-Route-Recorder/297d201d783cf5b9a86bfe0799878edfd0e64cdc/docs/assets/readme/curseforge-button.svg" alt="CurseForge - Download LibTaxiData" width="260"></a>
  <a href="https://discord.gg/YgcdybKdWX"><img src="https://raw.githubusercontent.com/Azeroth-Pilot-Reloaded/APR-Route-Recorder/297d201d783cf5b9a86bfe0799878edfd0e64cdc/docs/assets/readme/discord-button.svg" alt="Discord - Join the community" width="260"></a>
  <a href="https://github.com/Azeroth-Pilot-Reloaded/LibTaxiData"><img src="https://raw.githubusercontent.com/Azeroth-Pilot-Reloaded/APR-Route-Recorder/297d201d783cf5b9a86bfe0799878edfd0e64cdc/docs/assets/readme/github-button.svg" alt="GitHub - Explore LibTaxiData" width="260"></a>
</p>
<p align="center">
  <a href="https://www.patreon.com/AzerothPilotReloaded"><img src="https://raw.githubusercontent.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/e67d6c36cd4f9e5d5365cccd0c6ba2434f0c781d/readme/assets/patreon-button.svg" alt="Patreon - Support development" width="260"></a>
  <a href="https://www.paypal.com/paypalme/neogeekmo"><img src="https://raw.githubusercontent.com/Azeroth-Pilot-Reloaded/azeroth-pilot-reloaded/e67d6c36cd4f9e5d5365cccd0c6ba2434f0c781d/readme/assets/paypal-button.svg" alt="PayPal - Make a one-time donation" width="260"></a>
</p>

LibTaxiData is a **standalone multi-client addon** and a shared data source for other addons, including [Azeroth Pilot Reloaded](https://www.curseforge.com/wow/addons/azeroth-pilot-reloaded). It works without LibStub, HereBeDragons, or any other addon. The same public API exposes localized taxi names, generated DB2 records, character conditions, coordinates, nearby nodes, and native Blizzard waypoints.

<p align="center">
  <a href="#getting-started"><strong>Get started</strong></a> &nbsp;&middot;&nbsp;
  <a href="#features"><strong>Features</strong></a> &nbsp;&middot;&nbsp;
  <a href="#clients-and-compatibility"><strong>Clients</strong></a> &nbsp;&middot;&nbsp;
  <a href="#commands"><strong>Commands</strong></a> &nbsp;&middot;&nbsp;
  <a href="#public-api"><strong>API</strong></a> &nbsp;&middot;&nbsp;
  <a href="#data-profiles-and-generation"><strong>Data</strong></a> &nbsp;&middot;&nbsp;
  <a href="#support-and-contributions"><strong>Support</strong></a>
</p>

---

## Getting started

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>01 &nbsp; Install your version</h3>
      <p>Download the release for your game client from <a href="https://www.curseforge.com/wow/addons/libtaxidata">CurseForge</a>. LibTaxiData has no addon dependencies.</p>
      <p>Installing manually? Place the <code>LibTaxiData</code> folder in <code>Interface/AddOns</code>, then enable it on the character selection screen.</p>
    </td>
    <td width="50%" valign="top">
      <h3>02 &nbsp; Find your next flight</h3>
      <p>Type <code>/ltd nearest</code> to find a nearby taxi node that passes the default availability and visibility filters.</p>
      <p>The command prints its name and distance, then attempts to set a native Blizzard waypoint.</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>03 &nbsp; Inspect a flight master</h3>
      <p>Use <code>/ltd node &lt;nodeID&gt;</code> for coordinates, conditions, flags, mounts, and visual metadata. Add a map ID to request local map coordinates.</p>
      <p>Need just the name? Use <code>/ltd name &lt;nodeID&gt;</code>. Type <code>/ltd</code> or <code>/ltd help</code> for the command list.</p>
    </td>
    <td width="50%" valign="top">
      <h3>04 &nbsp; Build with the data</h3>
      <p>Other addons access <code>_G.LibTaxiData_API</code> after LibTaxiData has loaded. Use the public methods for names, node details, searches, and coordinate conversion.</p>
      <p>Declare <code>LibTaxiData</code> as a dependency in your addon's TOC when your addon requires it.</p>
    </td>
  </tr>
</table>

> **Tip:** Local coordinates in chat commands accept normalized values (`0.438 0.682`) or percentages (`43.8 68.2`). Coordinate APIs use normalized map values. Native waypoints and map conversions depend on the APIs available in your game client and on finding a compatible map.

---

<p align="center">
  <img src="readme/assets/features-rounded.svg" alt="Features" width="1000">
</p>

## Features

<p align="center">
  <strong>Localized names &nbsp;&middot;&nbsp; Character-aware data &nbsp;&middot;&nbsp; Navigation helpers &nbsp;&middot;&nbsp; A shared API</strong>
</p>

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Flight data in your language</h3>
      <ul>
        <li><strong>Localized taxi names</strong> for all 12 supported client locales, selected automatically from the active game language.</li>
        <li><strong>English fallback</strong> applied during data generation when a translated name is missing.</li>
        <li><strong>Stable node IDs</strong> let addons look up the same flight master across languages.</li>
        <li><strong>Localized chat output</strong> for node details, search results, help, and waypoint errors.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>Complete node records</h3>
      <ul>
        <li><strong>Raw generated DB2 metadata</strong>: world positions, map and flight-map offsets, flags, textures, facing, and faction mounts.</li>
        <li><strong>Enriched node details</strong> combine the raw record with its localized name, coordinate formats, availability, visibility, and faction mount.</li>
        <li><strong>Condition references</strong> include availability, world-map visibility, and special-icon requirements.</li>
        <li><strong>Excluded-node audit records</strong> retain the name and reason for deliberately omitted test or development nodes.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Results that fit your character</h3>
      <ul>
        <li><strong>Faction and character checks</strong> cover supported race, class, level, quest, reputation, item, spell, achievement, covenant, and ModifierTree requirements.</li>
        <li><strong>Separate availability and visibility</strong> checks distinguish using a node from displaying it on the map.</li>
        <li><strong>Three-state evaluation</strong> returns satisfied, rejected, or unknown when the public game API cannot evaluate a requirement.</li>
        <li><strong>Configurable search filters</strong> let addon authors control unavailable, hidden, arrival-only, ignored, and unknown nodes.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>Coordinates and navigation</h3>
      <ul>
        <li><strong>Nearest-node searches</strong> from the player, a map position, conventional world coordinates, or APR's historical coordinate format.</li>
        <li><strong>Distance in yards</strong>, with optional three-dimensional distance and custom filters through the API.</li>
        <li><strong>Map and world conversion</strong> with explicit coordinate-system fields and HereBeDragons-style convenience signatures.</li>
        <li><strong>Native Blizzard waypoints</strong> resolve nodes on a preferred or current map and its parents, with super-tracking when available.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>The right data for your client</h3>
      <ul>
        <li><strong>Automatic profile selection</strong> uses the detected client build and WoW project, including branches that share a project ID.</li>
        <li><strong>Separate client and server catalogs</strong> describe permanent client versions and their Live, PTR, Beta, or archived data profiles.</li>
        <li><strong>Explicit fallback reporting</strong> identifies when an installed archive uses its compatible fallback on an ungenerated build.</li>
        <li><strong>Capability checks</strong> and modern/legacy API adapters account for differences between game clients.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>Lightweight releases, reusable API</h3>
      <ul>
        <li><strong>One compatible data set per release archive</strong>, rather than shipping every generated client database.</li>
        <li><strong>Complete data fingerprints</strong> group builds only when their node, condition, and locale data match.</li>
        <li><strong>A standalone global API</strong> that consumers can check by capability, without a LibStub major or minimum data-version constant.</li>
        <li><strong>Generated data and tooling</strong> keep the runtime manifest, interface metadata, release plan, and profile catalogs synchronized.</li>
      </ul>
    </td>
  </tr>
</table>

### Supported languages

`enUS`, `enGB`, `deDE`, `esES`, `esMX`, `frFR`, `itIT`, `koKR`, `ptBR`, `ruRU`, `zhCN`, and `zhTW`.

## Clients and compatibility

| Client family                             | Data coverage in the current catalog                                             |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| **Retail**                                | Live and PTR profiles with their own generated node, condition, and locale data. |
| **Mists of Pandaria Classic**             | Live and PTR profiles.                                                           |
| **Classic Era**                           | A dedicated Live profile and generated data set.                                 |
| **WoW Forever**                           | A dedicated Beta profile and generated data set.                                 |
| **Anniversary / Burning Crusade Classic** | A dedicated TBC data set; the current catalog uses a PTR profile.                |
| **Wrath of the Lich King Classic**        | Registered as a base client; no active data profile is attached.                 |
| **Cataclysm Classic**                     | Registered as a base client; no active data profile is attached.                 |

Install the published archive that matches your client. Registered base clients without a generated data profile are recognized but report `supported = false`. A generated PTR or Beta profile is published only when its release rules allow it; catalog coverage does not imply that every profile has a currently published prerelease.

Addon authors can inspect the selected profile, embedded data set, detected build, exact/fallback state, and API capabilities through `GetClientInfo()`.

---

<p align="center">
  <img src="readme/assets/settings-commands-rounded.svg" alt="Settings and Commands" width="1000">
</p>

## Commands

Use **`/ltd`** or **`/libtaxidata`** in chat. Both prefixes open the same commands. LibTaxiData's controls are available through chat commands and its public API.

| Command                                             | What it does                                                                                                                                                                                   |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/ltd` / `/ltd help`                                | Print the command list.                                                                                                                                                                        |
| `/ltd name <nodeID>`                                | Print the localized node name and its ID.                                                                                                                                                      |
| `/ltd node <nodeID> [uiMapID]`                      | Print the node's localized name, world/APR coordinates, conditions, flags, mounts, offsets, and visual metadata; include map coordinates when a map ID can be resolved. `details` is an alias. |
| `/ltd nearest`                                      | Find the nearest node using the default availability and visibility filters, print its name and distance, and attempt to set a waypoint.                                                       |
| `/ltd nearest <uiMapID> <x> <y>`                    | Search from normalized or percentage map coordinates and attempt to set a waypoint.                                                                                                            |
| `/ltd nearest world <instanceID> <worldX> <worldY>` | Search from conventional world coordinates and attempt to resolve the result on the current map hierarchy.                                                                                     |
| `/ltd waypoint <nodeID> [uiMapID]`                  | Set a native Blizzard waypoint for the node, using the preferred map when provided; enable super-tracking when available.                                                                      |

Examples:

```text
/ltd nearest
/ltd name 2
/ltd node 2 84
/ltd waypoint 2 84
/ltd nearest 2437 43.8 68.2
```

> **Important:** A nearest-node result reflects the library's data and character filters. Requirements that depend on unknown server-side state remain unknown and are eligible by default. Use the API option `includeUnknown = false` if your addon needs to reject nodes with unknown availability.

---

## Public API

The addon exposes `_G.LibTaxiData_API`. It does not register a LibStub major and
there is no minimum data-version constant for consumers to maintain.

### Load LibTaxiData before your addon

When LibTaxiData is required, declare it in your addon's TOC:

```toc
## Dependencies: LibTaxiData
```

Consumers should check the public methods they use and inspect `GetClientInfo().supported` when deciding whether flight data is available for the detected client.

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
| `GetClientInfo()`                                         | Selected profile/data set, game type, channel, detected build, and exact/fallback selection state.                                   |

### Node conditions and mounts

| API                                    | Result                                                                                                        |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `GetPlayerCondition(conditionID)`      | Raw generated PlayerCondition record, or `nil` when it is not retained.                                       |
| `IsNodeAvailable(nodeID)`              | Whether the node's faction and availability requirements pass; `nil` when required state cannot be evaluated. |
| `IsNodeVisible(nodeID)`                | Whether the node should appear for the character according to faction, visibility conditions, and flags.      |
| `HasSpecialIcon(nodeID)`               | Whether the node's conditional special icon applies.                                                          |
| `EvaluatePlayerCondition(conditionID)` | Three-state evaluation of a PlayerCondition.                                                                  |
| `EvaluateModifierTree(treeID)`         | Three-state evaluation of a supported ModifierTree.                                                           |
| `GetMountCreatureID(nodeID)`           | The current faction's taxi mount creature ID when one is defined.                                             |

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

### Coordinate conversion helpers

| API                                                                                            | Result                                                                              |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `MapToWorld(uiMapID, mapX, mapY)`                                                              | Convert normalized map coordinates to a conventional world-position object.         |
| `WorldToMap(instanceID, worldX, worldY, uiMapID[, allowOutOfBounds])`                          | Convert world coordinates to normalized coordinates on the requested UI map.        |
| `GetPlayerWorldPosition()`                                                                     | The player's conventional world-position object when it can be resolved.            |
| `WorldToAPRWorld(worldX, worldY, worldZ, instanceID)`                                          | Convert conventional world X/Y to APR's historical swapped-axis position object.    |
| `APRWorldToWorld(aprX, aprY, worldZ, instanceID)`                                              | Convert an APR position back to a conventional world-position object.               |
| `GetWorldCoordinatesFromZone(mapX, mapY, uiMapID)`                                             | Return conventional `worldX`, `worldY`, and `instanceID`.                           |
| `GetZoneCoordinatesFromWorld(worldX, worldY, uiMapID[, allowOutOfBounds])`                     | Return normalized `mapX`, `mapY`, and `mapID`, inferring the target world instance. |
| `GetZoneCoordinatesFromWorldInstance(worldX, worldY, instanceID, uiMapID[, allowOutOfBounds])` | Return normalized `mapX`, `mapY`, and `mapID` with an explicit world instance.      |

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

### Native waypoints

| API                                                | Result                                                                                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ResolveNodeMapPosition(nodeID[, preferredMapID])` | Find the node's normalized position on a preferred or current map, checking parent maps as needed. Returns `nil` and an error code when no map can be resolved.   |
| `SetWaypointToNode(nodeID[, preferredMapID])`      | Set a native Blizzard waypoint and enable super-tracking when available. Returns `true` and the map position on success, or `false` and an error code on failure. |

Map conversion, player-position lookup, and native waypoints depend on client API capabilities. A successful nearest-node search does not guarantee that a waypoint can be placed on the current map hierarchy.

### Conditions

`IsNodeAvailable`, `IsNodeVisible`, `EvaluatePlayerCondition`, and
`EvaluateModifierTree` use tri-state results:

- `true`: all known requirements pass;
- `false`: at least one requirement is known to fail;
- `nil`: the public addon API cannot safely evaluate a server-only requirement.

The library never turns an unknown phase, WorldStateExpression, objective,
AreaTable, or other server-only state into a false positive.

## Data profiles and generation

Client detection selects the profile from `GetBuildInfo()` and `WOW_PROJECT_ID`. `profile` describes the client build, while `dataSet` identifies the data shipped in the installed archive. `GetClientInfo()` reports the selected profile, exact/fallback state, support status, and available API capabilities.

The generator uses Blizzard's public build feed and versioned Wago Tools DB2 exports. It keeps client profiles, generated data, and TOC interfaces synchronized. Release archives include one compatible data set; builds share storage only when their complete node, condition, and locale fingerprints match.

```sh
python tools/profiles.py list
python tools/profiles.py check
python tools/package.py --matrix
```

See the **[data-generation guide](readme/DATA-GENERATION.md)** for adding base clients or server profiles, regenerating data, API adapters, release-channel rules, archived builds, and packaging commands.

---

## Support and contributions

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Read the source and report an issue</h3>
      <p>Browse the <a href="https://github.com/Azeroth-Pilot-Reloaded/LibTaxiData">GitHub repository</a> for the API, generated data, tests, and build tooling.</p>
      <p>Report bugs or request improvements through <a href="https://github.com/Azeroth-Pilot-Reloaded/LibTaxiData/issues">GitHub Issues</a>. Include your addon version, game client and build, node or map IDs, the command or API call, and any Lua error.</p>
    </td>
    <td width="50%" valign="top">
      <h3>Join the community</h3>
      <p>Visit <a href="https://discord.gg/YgcdybKdWX">Discord</a> for setup help, API discussions, and translation contributions.</p>
      <p>For client-selection or data problems, include the result of <code>GetClientInfo()</code> and <code>GetSource()</code> so the selected profile and data source can be identified.</p>
    </td>
  </tr>
</table>

---

<p align="center">
  <img src="readme/assets/credits-rounded.svg" alt="Credits" width="1000">
</p>

## Credits

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Development</h3>
      <p><strong>Neoldric</strong><br>Addon development, public API, and data tooling.</p>
      <p>Built for the World of Warcraft addon community and the <a href="https://github.com/Azeroth-Pilot-Reloaded">Azeroth Pilot Reloaded</a> projects.</p>
    </td>
    <td width="50%" valign="top">
      <h3>Data and tooling</h3>
      <ul>
        <li><strong>Blizzard Entertainment</strong> - World of Warcraft client APIs and public build feed.</li>
        <li><a href="https://wago.tools/"><strong>Wago Tools</strong></a> - Versioned DB2 exports.</li>
      </ul>
    </td>
  </tr>
</table>

---

<p align="center">
  <strong>LibTaxiData</strong><br>
  Flight data for your next connection.<br><br>
  <a href="#readme-top">Back to top</a>
</p>
