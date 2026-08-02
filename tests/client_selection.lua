WOW_PROJECT_MAINLINE = 1
WOW_PROJECT_CLASSIC = 2
WOW_PROJECT_BURNING_CRUSADE_CLASSIC = 5
WOW_PROJECT_WRATH_CLASSIC = 11
WOW_PROJECT_CATACLYSM_CLASSIC = 14
WOW_PROJECT_MISTS_CLASSIC = 19

local version
local buildNumber
local interface

dofile("LibTaxiData.lua")
dofile("Data/ClientProfiles.lua")
local profileBuilds = {}
for _, profile in ipairs(LibTaxiData_Internal.ClientProfiles) do
    profileBuilds[profile.profile] = profile.build
end

function GetBuildInfo()
    return version, buildNumber, "", interface
end

local function Select(projectID, fullBuild)
    WOW_PROJECT_ID = projectID
    version, buildNumber = assert(fullBuild:match("^(.*)%.(%d+)$"))
    local major, minor, patch = version:match("^(%d+)%.(%d+)%.(%d+)$")
    interface = tonumber(major) * 10000 + tonumber(minor) * 100 + tonumber(patch)
    LibTaxiData_Internal = nil
    dofile("LibTaxiData.lua")
    dofile("Data/ClientProfiles.lua")
    dofile("Client.lua")
    return assert(LibTaxiData_Internal.Client)
end

local exact = Select(WOW_PROJECT_MAINLINE, assert(profileBuilds.retail_ptr))
assert(exact.profile == "retail_ptr" and exact.exactBuild and not exact.fallback)

local retailFallback = Select(WOW_PROJECT_MAINLINE, "12.2.0.70000")
assert(retailFallback.profile == "retail" and retailFallback.fallback)

local classicFallback = Select(WOW_PROJECT_CLASSIC, "1.15.10.70001")
assert(classicFallback.profile == "classic" and classicFallback.fallback)

local mistsFallback = Select(WOW_PROJECT_MISTS_CLASSIC, "5.5.5.70002")
assert(mistsFallback.profile == "mists" and mistsFallback.fallback)

local compatibleMists = Select(WOW_PROJECT_MISTS_CLASSIC, assert(profileBuilds.mists_ptr))
assert(compatibleMists.profile == "mists_ptr" and compatibleMists.dataSet == "mists")

local unsupported = Select(WOW_PROJECT_CATACLYSM_CLASSIC, "4.4.2.70003")
assert(unsupported.supported == false and unsupported.profile == nil)

print("LibTaxiData client selection tests: OK")
