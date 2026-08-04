-- A base client with no server profile must still load the common, safe API.
dofile("LibTaxiData.lua")
dofile("Data/ClientProfiles.lua")

local target
for index, candidate in ipairs(LibTaxiData_Internal.ClientVersions) do
    _G[candidate.projectConstant] = 2000 + index
    if candidate.version == "wrath" then
        target = candidate
    end
end
assert(target, "Wrath base version is missing")

WOW_PROJECT_ID = _G[target.projectConstant]
function GetBuildInfo() return "3.4.3", "99999", "", 30403 end
function GetLocale() return "enUS" end
SlashCmdList = {}

dofile("Client.lua")
assert(LibTaxiData_Internal.Client.version == "wrath")
assert(LibTaxiData_Internal.Client.apiFamily == "legacy")
assert(LibTaxiData_Internal.Client.supported == false)

dofile("Compatibility.lua")
dofile("Localization.lua")
dofile("Conditions.lua")
dofile("Coordinates.lua")
dofile("API.lua")
dofile("Commands.lua")

local api = assert(LibTaxiData_API)
local client = api.GetClientInfo()
assert(client.version == "wrath")
assert(client.detectedInterface == 30403)
assert(client.supported == false)
assert(client.apiCapabilities.preferredFamily == "legacy")
assert(next(api.GetAllNodes()) == nil)
assert(api.GetSource() == nil)

print("LibTaxiData no-server base-version tests: OK")
