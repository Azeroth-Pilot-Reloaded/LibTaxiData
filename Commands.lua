if _G.LibTaxiData_CommandsRegistered then return end

local API = _G.LibTaxiData_API
if not API then return end

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
        return "unknown"
    end
    return value and "yes" or "no"
end

local function PrintHelp()
    Print("/ltd name <nodeID> - localized node name")
    Print("/ltd node <nodeID> [uiMapID] - localized name and full node details")
    Print("/ltd nearest - nearest taxi to the player and set a waypoint")
    Print("/ltd nearest <uiMapID> <x> <y> - nearest taxi from local map coordinates")
    Print("/ltd nearest world <instanceID> <x> <y> - nearest taxi from world coordinates")
    Print("/ltd waypoint <nodeID> [uiMapID] - set a waypoint on a taxi node")
end

local function PrintNode(nodeID, uiMapID)
    local details = API.GetNodeDetails(nodeID, uiMapID)
    if not details then
        Print("unknown node ID " .. tostring(nodeID))
        return
    end

    Print(string.format("%s (node %d)", details.name or UNKNOWN or "Unknown", nodeID))
    Print(string.format(
        "world: instance=%d x=%.3f y=%.3f z=%.3f; APR: x=%.3f y=%.3f",
        details.worldPosition.instanceID,
        details.worldPosition.x,
        details.worldPosition.y,
        details.worldPosition.z,
        details.aprWorldPosition.x,
        details.aprWorldPosition.y
    ))
    if details.mapPosition then
        Print(string.format(
            "map: uiMapID=%d x=%.4f y=%.4f (%.2f, %.2f)",
            details.mapPosition.mapID,
            details.mapPosition.x,
            details.mapPosition.y,
            details.mapPosition.x * 100,
            details.mapPosition.y * 100
        ))
    end
    Print(string.format(
        "available=%s visible=%s conditions: node=%d visibility=%d specialIcon=%d flags=0x%X",
        State(details.availability),
        State(details.visibility),
        details.conditionID or 0,
        details.visibilityConditionID or 0,
        details.specialIconConditionID or 0,
        details.flags or 0
    ))
    Print(string.format(
        "mounts: Horde=%d Alliance=%d current=%s; characterBit=%d",
        details.hordeMountCreatureID or 0,
        details.allianceMountCreatureID or 0,
        tostring(details.mountCreatureID or "none"),
        details.characterBitNumber or 0
    ))
    Print(string.format(
        "offsets: map=(%.5f, %.5f) flight=(%.5f, %.5f); textureKit=%d minimapAtlas=%d facing=%.3f",
        details.mapOffsetX or 0,
        details.mapOffsetY or 0,
        details.flightMapOffsetX or 0,
        details.flightMapOffsetY or 0,
        details.uiTextureKitID or 0,
        details.minimapAtlasMemberID or 0,
        details.facing or 0
    ))
end

local function Waypoint(nodeID, uiMapID)
    local success, positionOrError = API.SetWaypointToNode(nodeID, uiMapID)
    if not success then
        Print("cannot set waypoint: " .. tostring(positionOrError))
        return
    end
    Print(string.format(
        "waypoint set: %s (node %d) on map %d at %.2f, %.2f",
        API.GetNodeName(nodeID) or UNKNOWN or "Unknown",
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
        Print("no matching taxi node was found; check the coordinate format and node conditions")
        return
    end

    Print(string.format(
        "nearest: %s (node %d), %.1f yards",
        result.name or UNKNOWN or "Unknown",
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
            Print("unknown node ID " .. tostring(words[2] or ""))
            return
        end
        Print(string.format("%s (node %d)", name, nodeID))
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
