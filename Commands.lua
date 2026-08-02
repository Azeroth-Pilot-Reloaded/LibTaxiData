if _G.LibTaxiData_CommandsRegistered then return end

local API = _G.LibTaxiData_API
if not API then return end
local L = API.LOCALIZATION
if not L then return end

_G.LibTaxiData_CommandsRegistered = true

local PREFIX = "|cff4db3ffLibTaxiData:|r "

local function Print(message)
    if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
        DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. message)
    else
        print("LibTaxiData: " .. message)
    end
end

local function Words(message)
    local words = {}
    for word in (message or ""):gmatch("%S+") do
        table.insert(words, word)
    end
    return words
end

local function Coordinate(value)
    value = tonumber(value)
    if value and value > 1 and value <= 100 then
        return value / 100
    end
    return value
end

local function State(value)
    if value == nil then
        return L["STATE_UNKNOWN"]
    end
    return value and L["STATE_YES"] or L["STATE_NO"]
end

local function PrintHelp()
    Print(L["COMMAND_HELP_NAME"])
    Print(L["COMMAND_HELP_NODE"])
    Print(L["COMMAND_HELP_NEAREST_PLAYER"])
    Print(L["COMMAND_HELP_NEAREST_MAP"])
    Print(L["COMMAND_HELP_NEAREST_WORLD"])
    Print(L["COMMAND_HELP_WAYPOINT"])
end

local function PrintNode(nodeID, uiMapID)
    local details = API.GetNodeDetails(nodeID, uiMapID)
    if not details then
        Print(string.format(L["UNKNOWN_NODE_ID"], tostring(nodeID)))
        return
    end

    Print(string.format(L["NODE_HEADER"], details.name or L["UNKNOWN_NAME"], nodeID))
    Print(string.format(
        L["NODE_WORLD_POSITION"],
        details.worldPosition.instanceID,
        details.worldPosition.x,
        details.worldPosition.y,
        details.worldPosition.z,
        details.aprWorldPosition.x,
        details.aprWorldPosition.y
    ))
    if details.mapPosition then
        Print(string.format(
            L["NODE_MAP_POSITION"],
            details.mapPosition.mapID,
            details.mapPosition.x,
            details.mapPosition.y,
            details.mapPosition.x * 100,
            details.mapPosition.y * 100
        ))
    end
    Print(string.format(
        L["NODE_CONDITIONS"],
        State(details.availability),
        State(details.visibility),
        details.conditionID or 0,
        details.visibilityConditionID or 0,
        details.specialIconConditionID or 0,
        details.flags or 0
    ))
    Print(string.format(
        L["NODE_MOUNTS"],
        details.hordeMountCreatureID or 0,
        details.allianceMountCreatureID or 0,
        tostring(details.mountCreatureID or L["NONE"]),
        details.characterBitNumber or 0
    ))
    Print(string.format(
        L["NODE_OFFSETS"],
        details.mapOffsetX or 0,
        details.mapOffsetY or 0,
        details.flightMapOffsetX or 0,
        details.flightMapOffsetY or 0,
        details.uiTextureKitID or 0,
        details.minimapAtlasMemberID or 0,
        details.facing or 0
    ))
end

local waypointErrorKeys = {
    ["unknown-node"] = "ERROR_UNKNOWN_NODE",
    ["no-compatible-ui-map"] = "ERROR_NO_COMPATIBLE_UI_MAP",
    ["waypoint-api-unavailable"] = "ERROR_WAYPOINT_API_UNAVAILABLE",
    ["waypoint-rejected"] = "ERROR_WAYPOINT_REJECTED",
    ["invalid-coordinates"] = "ERROR_INVALID_COORDINATES",
    ["map-api-unavailable"] = "ERROR_MAP_API_UNAVAILABLE",
    ["vector-api-unavailable"] = "ERROR_VECTOR_API_UNAVAILABLE",
    ["map-not-convertible"] = "ERROR_MAP_NOT_CONVERTIBLE",
    ["outside-map"] = "ERROR_OUTSIDE_MAP",
    ["unit-position-unavailable"] = "ERROR_UNIT_POSITION_UNAVAILABLE",
    ["player-position-unavailable"] = "ERROR_PLAYER_POSITION_UNAVAILABLE",
}

local function LocalizeWaypointError(errorCode)
    local localizationKey = waypointErrorKeys[errorCode]
    if localizationKey then
        return L[localizationKey]
    end
    return string.format(L["ERROR_UNKNOWN"], tostring(errorCode))
end

local function Waypoint(nodeID, uiMapID)
    local success, positionOrError = API.SetWaypointToNode(nodeID, uiMapID)
    if not success then
        Print(string.format(L["CANNOT_SET_WAYPOINT"], LocalizeWaypointError(positionOrError)))
        return
    end
    Print(string.format(
        L["WAYPOINT_SET"],
        API.GetNodeName(nodeID) or L["UNKNOWN_NAME"],
        nodeID,
        positionOrError.mapID,
        positionOrError.x * 100,
        positionOrError.y * 100
    ))
end

local function Nearest(words)
    local result
    local preferredMapID
    if words[2] == "world" then
        local instanceID = tonumber(words[3])
        local worldX = tonumber(words[4])
        local worldY = tonumber(words[5])
        result = API.FindNearestNodeFromWorld(worldX, worldY, instanceID)
    elseif words[2] then
        preferredMapID = tonumber(words[2])
        local mapX = Coordinate(words[3])
        local mapY = Coordinate(words[4])
        result = API.FindNearestNodeFromMap(preferredMapID, mapX, mapY)
    else
        preferredMapID = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit("player") or nil
        result = API.FindNearestNodeToPlayer()
    end

    if not result then
        Print(L["NO_MATCHING_TAXI"])
        return
    end

    Print(string.format(
        L["NEAREST_TAXI"],
        result.name or L["UNKNOWN_NAME"],
        result.nodeID,
        result.distance
    ))
    Waypoint(result.nodeID, preferredMapID)
end

local function HandleCommand(message)
    local words = Words(message)
    local command = words[1] and words[1]:lower() or "help"
    if command == "name" then
        local nodeID = tonumber(words[2])
        local name = nodeID and API.GetNodeName(nodeID) or nil
        if not name then
            Print(string.format(L["UNKNOWN_NODE_ID"], tostring(words[2] or "")))
            return
        end
        Print(string.format(L["NODE_HEADER"], name, nodeID))
    elseif command == "node" or command == "details" then
        local nodeID = tonumber(words[2])
        if not nodeID then
            PrintHelp()
            return
        end
        PrintNode(nodeID, tonumber(words[3]))
    elseif command == "nearest" then
        Nearest(words)
    elseif command == "waypoint" then
        local nodeID = tonumber(words[2])
        if not nodeID then
            PrintHelp()
            return
        end
        Waypoint(nodeID, tonumber(words[3]))
    else
        PrintHelp()
    end
end

SLASH_LIBTAXIDATA1 = "/libtaxidata"
SLASH_LIBTAXIDATA2 = "/ltd"
SlashCmdList.LIBTAXIDATA = HandleCommand
