# Client profiles and data generation

`GetBuildInfo()` and `WOW_PROJECT_ID` select the active data profile. Exact
build matching distinguishes Live, PTR, and Beta clients that share the same
WoW project ID. `profile` describes the client build while `dataSet` identifies
the data embedded in the installed archive. A newer ungenerated build uses the
only safe fallback embedded for that base version and reports `fallback = true`
through `GetClientInfo()`.

The catalog deliberately separates permanent client versions from temporary
servers/builds:

- [`tools/versions.json`](../tools/versions.json) contains every supported base client, even when no
  Blizzard server currently exists for it;
- [`tools/profiles.json`](../tools/profiles.json) contains the Live, PTR, Beta, or archived server builds
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

## Adding a base version

Add a base client to `tools/versions.json` once, then run
`python tools/profiles.py sync`. It is included in `Data/ClientProfiles.lua`,
so the runtime can detect it from `WOW_PROJECT_ID` or its interface major even
if there is no corresponding server profile.

| Field | Required | Meaning and source |
| --- | --- | --- |
| `id` | yes | Permanent lowercase identifier referenced by server profiles, for example `anniversary`. |
| `name` | yes | Human-readable base-client name. |
| `gameType` | yes | Value accepted by WoW's TOC `AllowLoadGameType`, such as `mainline`, `classic`, `tbc`, `wrath`, `cata`, or `mists`. |
| `projectConstant` | yes | Client global whose value can equal `WOW_PROJECT_ID`, for example `WOW_PROJECT_MISTS_CLASSIC`. A project constant may be shared by base versions with disjoint interface rules. Inspect both values in-game with `/dump WOW_PROJECT_ID` and `/dump WOW_PROJECT_MISTS_CLASSIC`. |
| `apiFamily` | yes | Preferred adapter order: `modern` tries namespaced `C_*` APIs first; `legacy` tries historical global functions first. Missing or failing calls always fall back to the other implementation. |
| `interfaceMajor` | one rule | Exact first component returned by `GetBuildInfo()`, normally `1` through `5` for Classic branches. |
| `minimumInterfaceMinor` | no | Lower bound for the second component when `interfaceMajor` is set, used to distinguish Forever (`1.60+`) from Classic Era (`1.15`). |
| `minimumInterfaceMajor` | one rule | Open-ended interface rule used by Retail. Only one base version can define it. |
| `tocInterface` | yes | Last known compatible full TOC interface. It keeps the common API loadable when the base has no active server; active profile interfaces are added automatically. |
| `tocLabel` | client branches | Suffix used for `## Interface-<label>` in the TOC, for example `Mists` or `Camelot`. |
| `apiOverrides` | no | Per-feature `modern`/`legacy` preference when this client differs from its general `apiFamily`. Supported keys are `questCompleted`, `questLog`, `questReady`, `auras`, `spellBook`, `items`, `currency`, and `reputation`. |

The base registry currently covers Retail, Classic Era, Forever,
Anniversary/Burning Crusade, Wrath, Cataclysm, and Mists. Forever shares
`WOW_PROJECT_MAINLINE` with Retail but uses the `camelot` game type and
interface `16001`. Wrath and Cataclysm intentionally have no
server profile: they remain detectable with their legacy-first API policy and
report `supported = false` until data is attached to a profile.

`Compatibility.lua` centralizes APIs whose signatures/names changed between
clients. It records the implementation actually found in
`GetClientInfo().apiCapabilities`. Map conversion, player position, and
waypoints are also capability-probed at runtime. When Blizzard changes an API,
add its adapter there; use `apiOverrides` only when a particular base client
must prefer a different valid implementation.

## Adding a profile

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
| `dataSet` | no | Usually omit this and let the generator assign it after comparing complete generated fingerprints. Set it when the generated directory must have a distinct name from the profile ID, as with `wow_forever` using `forever`. |

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
its current US build with:

```sh
python tools/live_build.py --product wow_beta --region us
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
