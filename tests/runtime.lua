local profile = arg and arg[1] or "retail"
local initialInternal = LibTaxiData_Internal
dofile("LibTaxiData.lua")
dofile("Data/ClientProfiles.lua")
local clientGameTypes = LibTaxiData_Internal.ClientGameTypes
local gameType
local versionID
for _, candidate in ipairs(LibTaxiData_Internal.ClientProfiles) do
    if candidate.profile == profile then
        gameType = candidate.gameType
        versionID = candidate.version
        break
    end
end
assert(gameType, "unknown test profile: " .. tostring(profile))
local baseVersion
for _, candidate in ipairs(clientGameTypes) do
    if candidate.version == versionID then
        baseVersion = candidate
        break
    end
end
assert(baseVersion, "unknown base version: " .. tostring(versionID))

local projectIDs = {}
for index, candidate in ipairs(clientGameTypes) do
    local projectID = 1000 + index
    _G[candidate.projectConstant] = projectID
    projectIDs[candidate.gameType] = projectID
end
LibTaxiData_Internal = initialInternal

local expectedBuild = arg and arg[2]
if not expectedBuild then
    local sourceFile = assert(io.open("Data/" .. profile .. "/TaxiNodes.lua", "rb"))
    local sourceText = sourceFile:read("*a")
    sourceFile:close()
    expectedBuild = assert(sourceText:match('build = "([%d%.]+)"'))
end
local version, buildNumber = assert(expectedBuild:match("^(.*)%.(%d+)$"))
local major, minor, patch = version:match("^(%d+)%.(%d+)%.(%d+)$")
local interface = tonumber(major) * 10000 + tonumber(minor) * 100 + tonumber(patch)

WOW_PROJECT_ID = projectIDs[gameType]

local function Band(left, right)
    left = left % 4294967296
    right = right % 4294967296
    local result = 0
    local place = 1
    for _ = 1, 32 do
        if left % 2 >= 1 and right % 2 >= 1 then
            result = result + place
        end
        left = math.floor(left / 2)
        right = math.floor(right / 2)
        place = place * 2
    end
    return result
end

bit = {
    band = Band,
    rshift = function(value, count)
        return math.floor((value % 4294967296) / (2 ^ count))
    end,
}

local faction = "Alliance"
local classID = 8
local completedQuests = {}
local waypoint

function GetLocale() return "frFR" end
function GetBuildInfo() return version, buildNumber, "", interface end
function UnitFactionGroup() return faction end
function UnitRace() return "Humain", "Human", 1 end
function UnitClass() return "Mage", "MAGE", classID end
function UnitLevel() return 80 end
function UnitEffectiveLevel() return 80 end
function UnitSex() return 2 end
function UnitPosition() return 490, -8840, 100, 0 end
function GetInstanceInfo() return "", "", 0, "", 0, 0, false, 0 end
function GetAchievementInfo() return nil, nil, nil, false end
function CreateVector2D(x, y) return { x = x, y = y } end

C_QuestLog = {
    IsQuestFlaggedCompleted = function(questID) return completedQuests[questID] == true end,
    IsOnQuest = function() return false end,
    IsComplete = function() return false end,
}
C_UnitAuras = { GetPlayerAuraBySpellID = function() return nil end }
C_SpellBook = { IsSpellKnown = function() return false end }
C_Covenants = { GetActiveCovenantID = function() return 0 end }
C_CurrencyInfo = { GetCurrencyInfo = function() return { quantity = 0 } end }
C_Reputation = { GetFactionDataByID = function() return { reaction = 4 } end }
C_Item = { GetItemCount = function() return 0 end }
C_Map = {
    GetWorldPosFromMapPos = function(uiMapID, position)
        assert(uiMapID == 84 or uiMapID == 13)
        return 0, { x = -9000 + position.x * 1000, y = position.y * 1000 }
    end,
    GetMapPosFromWorldPos = function(instanceID, position, uiMapID)
        if instanceID ~= 0 or (uiMapID ~= 84 and uiMapID ~= 13) then
            return nil
        end
        return uiMapID, { x = (position.x + 9000) / 1000, y = position.y / 1000 }
    end,
    GetBestMapForUnit = function() return 84 end,
    GetPlayerMapPosition = function() return { x = 0.16, y = 0.49 } end,
    GetMapInfo = function(uiMapID)
        if uiMapID == 84 then return { parentMapID = 13 } end
        if uiMapID == 13 then return { parentMapID = 0 } end
    end,
    SetUserWaypoint = function(point) waypoint = point end,
}
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }
UiMapPoint = {
    CreateFromCoordinates = function(mapID, x, y)
        return { mapID = mapID, x = x, y = y }
    end,
}
DEFAULT_CHAT_FRAME = { AddMessage = function() end }
SlashCmdList = {}

dofile("LibTaxiData.lua")
dofile("Data/ClientProfiles.lua")
dofile("Client.lua")
local selectedClient = assert(LibTaxiData_Internal.Client)
local dataSet = assert(selectedClient.dataSet)
local dataBuild
for _, candidate in ipairs(LibTaxiData_Internal.ClientProfiles) do
    if candidate.profile == dataSet then
        dataBuild = candidate.build
        break
    end
end
assert(dataBuild, "missing source profile for data set: " .. dataSet)
dofile("Data/" .. dataSet .. "/TaxiNodes.lua")
dofile("Data/" .. dataSet .. "/PlayerConditions.lua")
dofile("Data/" .. dataSet .. "/ModifierTrees.lua")
dofile("Data/" .. dataSet .. "/SupportingData.lua")
dofile("Locale/" .. dataSet .. "/frFR.lua")
dofile("Localization.lua")
dofile("Compatibility.lua")
dofile("Conditions.lua")
dofile("Coordinates.lua")
dofile("API.lua")
dofile("Commands.lua")

local taxi = assert(LibTaxiData_API)
assert(taxi.LOCALIZATION["STATE_YES"] == "oui")
assert(taxi.GetSource().build == dataBuild)
assert(taxi.GetSource().profile == dataSet)
assert(taxi.GetSource().dataSet == dataSet)
assert(taxi.GetSource().gameType == gameType)
assert(taxi.GetClientInfo().profile == profile)
assert(taxi.GetClientInfo().version == versionID)
assert(taxi.GetClientInfo().apiFamily == baseVersion.apiFamily)
assert(type(taxi.GetClientInfo().apiCapabilities.questLog) == "string")
assert(taxi.GetClientInfo().apiCapabilities.mapCoordinates == true)
assert(taxi.GetClientInfo().dataSet == dataSet)
assert(taxi.GetClientInfo().detectedBuild == expectedBuild)
assert(taxi.GetClientInfo().exactBuild == true)
assert(taxi.GetClientInfo().fallback == false)
assert(type(taxi.GetNodeName(2)) == "string" and taxi.GetNodeName(2) ~= "")
assert(taxi.GetNode(2).continentID == 0)
assert(taxi.GetAllNodeData(2) == taxi.GetNode(2))
assert(taxi.GetAllNodes()[2] == taxi.GetNode(2))

if profile ~= "retail" then
    local world = assert(taxi.GetNodeWorldPosition(2))
    assert(world.coordinateSystem == "world")
    assert(taxi.FindNearestNodeFromWorld(world.x, world.y, world.instanceID).nodeID == 2)
    assert(type(SlashCmdList.LIBTAXIDATA) == "function")
    print("LibTaxiData " .. profile .. " runtime tests: OK")
    return
end

assert(taxi.GetNodeName(2) == "Hurlevent, Elwynn")
assert(taxi.GetNode(3) == nil)
assert(taxi.GetExcludedNode(3).reason == "programmer-isle")

assert(taxi.IsNodeAvailable(2) == true)
assert(taxi.IsNodeAvailable(10) == false)
assert(taxi.EvaluatePlayerCondition(924) == true)  -- Alliance races
assert(taxi.EvaluatePlayerCondition(923) == false) -- Horde races

assert(taxi.EvaluatePlayerCondition(7305) == false) -- Death Knight class mask
classID = 6
assert(taxi.EvaluatePlayerCondition(7305) == true)

assert(taxi.EvaluatePlayerCondition(7376) == false)
completedQuests[12523] = true
assert(taxi.EvaluatePlayerCondition(7376) == true)

assert(taxi.EvaluatePlayerCondition(5703) == nil)  -- WorldStateExpression
assert(taxi.EvaluatePlayerCondition(55365) == nil) -- missing DB2 row
assert(taxi.HasSpecialIcon(2) == false)

local world = assert(taxi.GetNodeWorldPosition(2))
assert(world.coordinateSystem == "world")
assert(world.x == taxi.GetNode(2).x and world.y == taxi.GetNode(2).y)
local aprWorld = assert(taxi.GetNodeAPRWorldPosition(2))
assert(aprWorld.coordinateSystem == "apr-world")
assert(aprWorld.x == world.y and aprWorld.y == world.x)

local convertedWorld = assert(taxi.MapToWorld(84, 0.25, 0.75))
assert(convertedWorld.x == -8750 and convertedWorld.y == 750 and convertedWorld.instanceID == 0)
local mapPosition = assert(taxi.WorldToMap(0, convertedWorld.x, convertedWorld.y, 84))
assert(mapPosition.x == 0.25 and mapPosition.y == 0.75)
local worldX, worldY, instanceID = taxi.GetWorldCoordinatesFromZone(0.25, 0.75, 84)
assert(worldX == -8750 and worldY == 750 and instanceID == 0)
local mapX, mapY, mapID = taxi.GetZoneCoordinatesFromWorld(worldX, worldY, 84)
assert(mapX == 0.25 and mapY == 0.75 and mapID == 84)
mapX, mapY, mapID = taxi.GetZoneCoordinatesFromWorldInstance(worldX, worldY, instanceID, 84)
assert(mapX == 0.25 and mapY == 0.75 and mapID == 84)

local nearest = assert(taxi.FindNearestNodeFromWorld(world.x, world.y, world.instanceID))
assert(nearest.nodeID == 2 and nearest.distance == 0)
assert(taxi.FindNearestNodeFromAPRWorld(aprWorld.x, aprWorld.y, aprWorld.instanceID).nodeID == 2)
assert(taxi.FindNearestNodeFromMap(84, (world.x + 9000) / 1000, world.y / 1000).nodeID == 2)
assert(taxi.FindNearestNodeToPlayer().nodeID == 2)

local details = assert(taxi.GetNodeDetails(2, 84))
assert(details.name == "Hurlevent, Elwynn")
assert(details.mapPosition and details.mapPosition.mapID == 84)
local waypointSet = taxi.SetWaypointToNode(2, 84)
assert(waypointSet == true and waypoint and waypoint.mapID == 84)
assert(type(SlashCmdList.LIBTAXIDATA) == "function")
SlashCmdList.LIBTAXIDATA("node 2 84")
waypoint = nil
SlashCmdList.LIBTAXIDATA("nearest")
assert(waypoint and waypoint.mapID == 84)

faction = "Horde"
assert(taxi.IsNodeAvailable(2) == false)
assert(taxi.IsNodeAvailable(10) == true)

print("LibTaxiData runtime tests: OK")
