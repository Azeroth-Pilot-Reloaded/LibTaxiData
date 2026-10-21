# Taxi connections, prices and durations

`LibTaxiData_API.GetAllPaths()`, `GetPath(pathID)` and
`GetOutgoingPaths(nodeID)` expose directed paths for the selected data set.
`DATA.Paths` is the same path table. Outgoing results are keyed by path ID,
not destination ID: parallel alternatives remain distinct. Unknown nodes return
an empty table. No-server client versions also expose a safe empty catalog.

A record contains `fromNodeID`, `toNodeID`, optional `basePriceCopper`, optional
`durationSeconds`, and `durationSource`. DB2 IDs are numbers; manually added IDs
are strings beginning with `manual:`. Prices and durations never share a field.
A base price is not the current character's payable fare (discounts and server
rules may apply). Consumers must check the live offered route and its price
before taking a taxi. Catalog existence does not establish character discovery,
reachability, permission, or that a particular flight master offers the path.

## Automatic generation

The existing six-hour update workflow downloads **TaxiPath** and **TaxiPathNode**
with the same exact build as TaxiNodes and all other tables. Raw exports are
cached as `{Table}-{build}-enUS.csv`; they are never borrowed from another client.
The runtime ships only compact `Data/<dataset>/TaxiPaths.lua` records. Full
geometry stays in the generator cache. The entire profile is generated and
validated in staging before its output files are replaced. A failed file-copy
commit rolls back all touched files; acquisition/schema failures leave the old
profile untouched.

The default estimate is the 3D polyline length / **32 yards per second**, plus
TaxiPathNode `Delay` in **seconds**. `durationSource = "geometry-estimate"`
identifies this approximation: it is neither a measured flight duration nor a
reproduction of the client's spline, speed changes, or scripted movement.
Teleport-flagged jumps are excluded from geometric distance (TrinityCore
[TAXI_PATH_NODE_FLAG_TELEPORT](https://github.com/TrinityCore/TrinityCore/blob/master/src/server/game/DataStores/DBCEnums.h) = 0x1).
Missing/incomplete geometry and transitions between world coordinate spaces
leave duration unknown. `durationSource = "unknown"` and an absent value never
mean zero. A real zero base price remains a known free price.

`readme/coverage/<dataset>.json` lists outgoing counts and missing prices or
durations per node, excluded paths, and estimate statistics. These reports are
maintenance artifacts; they are not part of release archives.

## Manual corrections by departure node

Edit `tools/manual/<dataset>.json` rather than generated Lua. The seven source
files are retained during every generation. Example:

```json
{
  "schemaVersion": 1,
  "nodes": {
    "2": {
      "name": "Stormwind",
      "outgoing": [
        {"id": 6, "toNodeID": 4, "durationSeconds": 71, "source": "Measured in game", "verifiedBuild": "1.60.1.70205"},
        {"toNodeID": 5, "basePriceCopper": 10, "source": "Flight master observation", "verifiedBuild": "1.60.1.70205"}
      ]
    }
  }
}
```

An existing numeric ID corrects that DB2 path without changing its endpoints.
An entry without an ID adds `manual:<from>:<to>`; an explicit `manual:` ID permits
multiple documented alternatives. Fields not supplied retain their DB2 values.
`null` price/duration means no correction. An added route with no supplied price
or duration keeps those values unknown. Active manual entries require a source
and verification build. `disabled: true` removes the specified path. An outdated
verification build remains visible as provenance; it does not become current
character evidence.

Only set top-level `complete: true` when the manual catalog is an intentionally
complete fallback for a profile whose Wago path tables cannot be acquired.
Otherwise acquisition failure preserves the previous complete generated profile
and fails the update. Never fill unknown connections by pairing all known nodes.

Actual character flight offers, discounted prices, and measured durations belong
to the consuming addon's per-character observations. This library does not save
character state.

## Validation

Run `python tests/taxi_path_generation.py`, the existing Lua tests for every generated
profile, `python tools/profiles.py check`, archive generation and archive tests.
Path-only price/duration corrections trigger data releases even within one build.
Fingerprint/dataset sharing includes all generated paths; distinct client
versions never share a data set solely because their node lists happen to match.
