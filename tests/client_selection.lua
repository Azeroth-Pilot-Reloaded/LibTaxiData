local version
local buildNumber
local interface

dofile("LibTaxiData.lua")
dofile("Data/ClientProfiles.lua")
local clientGameTypes = LibTaxiData_Internal.ClientGameTypes
local clientProfiles = LibTaxiData_Internal.ClientProfiles
local projectIDs = {}
for index, candidate in ipairs(clientGameTypes) do
    local projectID = 1000 + index
    _G[candidate.projectConstant] = projectID
    projectIDs[candidate.gameType] = projectID
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

local activeGameTypes = {}
for _, profile in ipairs(clientProfiles) do
    activeGameTypes[profile.gameType] = true
    local exact = Select(assert(projectIDs[profile.gameType]), profile.build)
    assert(exact.profile == profile.profile)
    assert(exact.dataSet == profile.dataSet)
    assert(exact.exactBuild and not exact.fallback and exact.supported)
end

for _, profile in ipairs(clientProfiles) do
    if profile.default then
        local versionOnly, number = assert(profile.build:match("^(.*)%.(%d+)$"))
        local unknownBuild = versionOnly .. "." .. tostring(tonumber(number) + 1000000)
        local fallback = Select(assert(projectIDs[profile.gameType]), unknownBuild)
        assert(fallback.profile == profile.profile)
        assert(fallback.fallback and not fallback.exactBuild and fallback.supported)
    end
end

for _, candidate in ipairs(clientGameTypes) do
    if not activeGameTypes[candidate.gameType] then
        local unsupported = Select(assert(projectIDs[candidate.gameType]), "0.0.0.1")
        assert(unsupported.supported == false and unsupported.profile == nil)
    end
end

print("LibTaxiData client selection tests: OK")
