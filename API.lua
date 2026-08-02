local lib = _G.LibTaxiData_Internal
if not lib then return end

local bit = _G.bit
local band = bit and bit.band

local FLAG_ALLIANCE = 0x001
local FLAG_HORDE = 0x002
local FLAG_SHOW_IF_CONDITION = 0x008
local FLAG_END_POINT_ONLY = 0x020
local FLAG_IGNORE_FOR_NEAREST = 0x040
local FLAG_DO_NOT_SHOW = 0x080

local API = {
    SOURCE = lib.Source,
    COORDINATE_FORMATS = lib.CoordinateFormats,
    FLAGS = {
        SHOW_ON_ALLIANCE_MAP = FLAG_ALLIANCE,
        SHOW_ON_HORDE_MAP = FLAG_HORDE,
        SHOW_ON_MAP_BORDER = 0x004,
        SHOW_IF_CLIENT_PASSES_CONDITION = FLAG_SHOW_IF_CONDITION,
        USE_PLAYER_FAVORITE_MOUNT = 0x010,
        END_POINT_ONLY = FLAG_END_POINT_ONLY,
        IGNORE_FOR_FIND_NEAREST = FLAG_IGNORE_FOR_NEAREST,
        DO_NOT_SHOW_IN_WORLD_MAP_UI = FLAG_DO_NOT_SHOW,
        SHOW_NPC_MINIMAP_ATLAS_IF_CLIENT_PASSES_CONDITION = 0x100,
        MAP_LAYER_TRANSITION = 0x200,
        NOT_ACCOUNT_WIDE = 0x400,
    },
    DATA = {
        Nodes = lib.Nodes,
        Names = lib.Names,
        PlayerConditions = lib.PlayerConditions,
        ModifierTrees = lib.ModifierTrees,
        ContentTuning = lib.ContentTuning,
        RaceBits = lib.RaceBits,
        ExcludedNodes = lib.ExcludedNodes,
        MissingPlayerConditions = lib.MissingPlayerConditions,
    },
}

local function HasFlag(value, flag)
    return band and band(value or 0, flag) ~= 0 or false
end

local function EvaluateFaction(flags)
    if not band then
        return nil
    end
    local allianceOnly = HasFlag(flags, FLAG_ALLIANCE)
    local hordeOnly = HasFlag(flags, FLAG_HORDE)
    if allianceOnly == hordeOnly then
        return true
    end
    local faction = UnitFactionGroup("player")
    if not faction then
        return nil
    end
    return allianceOnly and faction == "Alliance" or hordeOnly and faction == "Horde"
end

local function AddMapAndParents(candidates, seen, uiMapID)
    local guard = 0
    while type(uiMapID) == "number" and uiMapID > 0 and not seen[uiMapID] and guard < 20 do
        seen[uiMapID] = true
        table.insert(candidates, uiMapID)
        guard = guard + 1
        local info = C_Map and C_Map.GetMapInfo and C_Map.GetMapInfo(uiMapID) or nil
        uiMapID = info and info.parentMapID or nil
    end
end

---Return the raw generated TaxiNodes record for a node ID.
---@param nodeID number
---@return table|nil
function API.GetNode(nodeID)
    return lib.Nodes[nodeID]
end

---Return the raw generated table containing every retained node.
---@return table
function API.GetAllNodes()
    return lib.Nodes
end

---Alias that makes the all-fields behavior explicit to consumers.
API.GetAllNodeData = API.GetNode

---Return the current-client-locale name for a node ID.
---@param nodeID number
---@return string|nil
function API.GetNodeName(nodeID)
    return lib.Names[nodeID]
end

---Return the data-source metadata.
---@return table
function API.GetSource()
    return lib.Source
end

---Iterate over all retained (non-development) nodes.
---@return function, table, nil
function API.IterateNodes()
    return next, lib.Nodes, nil
end

---Return a deliberately excluded test/development node and its reason.
---@param nodeID number
---@return table|nil
function API.GetExcludedNode(nodeID)
    return lib.ExcludedNodes[nodeID]
end

---Return a PlayerCondition record referenced by the taxi data.
---@param conditionID number
---@return table|nil
function API.GetPlayerCondition(conditionID)
    return lib.PlayerConditions[conditionID]
end

---Evaluate a PlayerCondition against the current character.
---true means satisfied, false means rejected, nil means that the public WoW
---API cannot determine at least one required part of the condition.
---@param conditionID number
---@return boolean|nil
function API.EvaluatePlayerCondition(conditionID)
    return lib.EvaluatePlayerCondition(conditionID)
end

---Evaluate a ModifierTree against the current character using tri-state logic.
---@param treeID number
---@return boolean|nil
function API.EvaluateModifierTree(treeID)
    return lib.EvaluateModifierTree(treeID)
end

---Evaluate whether a node is usable for the current faction and character.
---@param nodeID number
---@return boolean|nil
function API.IsNodeAvailable(nodeID)
    local node = lib.Nodes[nodeID]
    if not node then
        return false
    end
    return lib.TriAnd(EvaluateFaction(node.flags), lib.EvaluatePlayerCondition(node.conditionID))
end

---Evaluate whether the world-map UI should show a node to the current player.
---@param nodeID number
---@return boolean|nil
function API.IsNodeVisible(nodeID)
    local node = lib.Nodes[nodeID]
    if not node then
        return false
    end
    if HasFlag(node.flags, FLAG_DO_NOT_SHOW) then
        return false
    end
    local result = EvaluateFaction(node.flags)
    if node.visibilityConditionID and node.visibilityConditionID ~= 0 then
        result = lib.TriAnd(result, lib.EvaluatePlayerCondition(node.visibilityConditionID))
    end
    if HasFlag(node.flags, FLAG_SHOW_IF_CONDITION) then
        result = lib.TriAnd(result, lib.EvaluatePlayerCondition(node.conditionID))
    end
    return result
end

---Evaluate whether the node's conditional special icon should be used.
---@param nodeID number
---@return boolean|nil
function API.HasSpecialIcon(nodeID)
    local node = lib.Nodes[nodeID]
    if not node then
        return false
    end
    if not node.specialIconConditionID or node.specialIconConditionID == 0 then
        return false
    end
    return lib.EvaluatePlayerCondition(node.specialIconConditionID)
end

---Return the faction-specific taxi mount creature ID, if one is defined.
---@param nodeID number
---@return number|nil
function API.GetMountCreatureID(nodeID)
    local node = lib.Nodes[nodeID]
    if not node then
        return nil
    end
    local faction = UnitFactionGroup("player")
    if faction == "Alliance" then
        return node.allianceMountCreatureID ~= 0 and node.allianceMountCreatureID or nil
    elseif faction == "Horde" then
        return node.hordeMountCreatureID ~= 0 and node.hordeMountCreatureID or nil
    end
    return nil
end

---Return a node position. The default is conventional world X/Y. Passing
---"apr-world" returns APR's historical { x = worldY, y = worldX } layout.
---@param nodeID number
---@param coordinateFormat string|nil
---@return table|nil
function API.GetNodeWorldPosition(nodeID, coordinateFormat)
    local node = lib.Nodes[nodeID]
    if not node then
        return nil
    end
    if coordinateFormat == lib.CoordinateFormats.APR_WORLD then
        return lib.APRWorldPosition(node.x, node.y, node.z, node.continentID)
    end
    if coordinateFormat and coordinateFormat ~= lib.CoordinateFormats.WORLD then
        return nil
    end
    return lib.WorldPosition(node.x, node.y, node.z, node.continentID)
end

---Return APR's historical swapped-axis world position for a node.
---@param nodeID number
---@return table|nil
function API.GetNodeAPRWorldPosition(nodeID)
    return API.GetNodeWorldPosition(nodeID, lib.CoordinateFormats.APR_WORLD)
end

---Convert a node's world position to normalized coordinates on a UI map.
---@param nodeID number
---@param uiMapID number
---@param allowOutOfBounds boolean|nil
---@return table|nil position
---@return string|nil errorCode
function API.GetNodeMapPosition(nodeID, uiMapID, allowOutOfBounds)
    local node = lib.Nodes[nodeID]
    if not node then
        return nil, "unknown-node"
    end
    return lib.WorldToMap(node.continentID, node.x, node.y, uiMapID, allowOutOfBounds)
end

---Return raw data plus localized and computed information for a node.
---@param nodeID number
---@param uiMapID number|nil
---@return table|nil
function API.GetNodeDetails(nodeID, uiMapID)
    local node = lib.Nodes[nodeID]
    if not node then
        return nil
    end
    local details = {}
    for key, value in pairs(node) do
        details[key] = value
    end
    details.nodeID = nodeID
    details.name = lib.Names[nodeID]
    details.worldPosition = API.GetNodeWorldPosition(nodeID)
    details.aprWorldPosition = API.GetNodeAPRWorldPosition(nodeID)
    details.mapPosition = uiMapID and API.GetNodeMapPosition(nodeID, uiMapID) or nil
    details.availability = API.IsNodeAvailable(nodeID)
    details.visibility = API.IsNodeVisible(nodeID)
    details.mountCreatureID = API.GetMountCreatureID(nodeID)
    return details
end

---Convert normalized UI-map coordinates to a conventional world-position object.
function API.MapToWorld(uiMapID, mapX, mapY)
    return lib.MapToWorld(uiMapID, mapX, mapY)
end

---Convert conventional world coordinates to a normalized UI-map position object.
function API.WorldToMap(instanceID, worldX, worldY, uiMapID, allowOutOfBounds)
    return lib.WorldToMap(instanceID, worldX, worldY, uiMapID, allowOutOfBounds)
end

---HereBeDragons-compatible convenience signature: map X/Y/mapID in, world X/Y/instance out.
function API.GetWorldCoordinatesFromZone(mapX, mapY, uiMapID)
    local position = lib.MapToWorld(uiMapID, mapX, mapY)
    if not position then
        return nil, nil, nil
    end
    return position.x, position.y, position.instanceID
end

---HereBeDragons-compatible inverse signature with an explicit world instance.
function API.GetZoneCoordinatesFromWorldInstance(worldX, worldY, instanceID, uiMapID, allowOutOfBounds)
    local position = lib.WorldToMap(instanceID, worldX, worldY, uiMapID, allowOutOfBounds)
    if not position then
        return nil, nil, nil
    end
    return position.x, position.y, position.mapID
end

---HereBeDragons-compatible inverse signature that infers the target instance.
function API.GetZoneCoordinatesFromWorld(worldX, worldY, uiMapID, allowOutOfBounds)
    local mapCenter = lib.MapToWorld(uiMapID, 0.5, 0.5)
    if not mapCenter then
        return nil, nil, nil
    end
    return API.GetZoneCoordinatesFromWorldInstance(
        worldX,
        worldY,
        mapCenter.instanceID,
        uiMapID,
        allowOutOfBounds
    )
end

---Return the player position in conventional world coordinates.
function API.GetPlayerWorldPosition()
    return lib.GetPlayerWorldPosition()
end

---Convert conventional world coordinates to APR's historical swapped-axis object.
function API.WorldToAPRWorld(worldX, worldY, worldZ, instanceID)
    return lib.APRWorldPosition(worldX, worldY, worldZ, instanceID)
end

---Convert an APR historical position back to conventional world coordinates.
function API.APRWorldToWorld(aprX, aprY, worldZ, instanceID)
    return lib.WorldPosition(aprY, aprX, worldZ, instanceID)
end

local function ShouldIncludeNearestNode(nodeID, node, options)
    if not options.includeIgnored and HasFlag(node.flags, FLAG_IGNORE_FOR_NEAREST) then
        return false
    end
    if not options.includeEndpointOnly and HasFlag(node.flags, FLAG_END_POINT_ONLY) then
        return false
    end

    local availability = API.IsNodeAvailable(nodeID)
    if availability == false and not options.includeUnavailable then
        return false
    end
    if availability == nil and options.includeUnknown == false then
        return false
    end

    local visibility = API.IsNodeVisible(nodeID)
    if visibility == false and not options.includeHidden then
        return false
    end
    if options.filter and options.filter(nodeID, node, availability, visibility) == false then
        return false
    end
    return true, availability, visibility
end

---Find the nearest suitable taxi node from conventional world coordinates.
---Unknown server-only conditions are included by default; known unavailable,
---hidden, arrival-only, and IGNORE_FOR_FIND_NEAREST nodes are excluded.
---@param worldX number
---@param worldY number
---@param instanceID number
---@param options table|nil
---@return table|nil result
function API.FindNearestNodeFromWorld(worldX, worldY, instanceID, options)
    if type(worldX) ~= "number" or type(worldY) ~= "number" or type(instanceID) ~= "number" then
        return nil
    end
    options = options or {}

    local nearest
    local nearestDistanceSquared
    for nodeID, node in pairs(lib.Nodes) do
        if node.continentID == instanceID then
            local include, availability, visibility = ShouldIncludeNearestNode(nodeID, node, options)
            if include then
                local deltaX = node.x - worldX
                local deltaY = node.y - worldY
                local distanceSquared = deltaX * deltaX + deltaY * deltaY
                if options.threeDimensional and type(options.z) == "number" then
                    local deltaZ = (node.z or 0) - options.z
                    distanceSquared = distanceSquared + deltaZ * deltaZ
                end
                if not nearestDistanceSquared or distanceSquared < nearestDistanceSquared then
                    nearestDistanceSquared = distanceSquared
                    nearest = {
                        nodeID = nodeID,
                        node = node,
                        name = lib.Names[nodeID],
                        distance = math.sqrt(distanceSquared),
                        worldPosition = API.GetNodeWorldPosition(nodeID),
                        aprWorldPosition = API.GetNodeAPRWorldPosition(nodeID),
                        availability = availability,
                        visibility = visibility,
                    }
                end
            end
        end
    end
    return nearest
end

---Find the nearest node from APR's { x = worldY, y = worldX } coordinates.
function API.FindNearestNodeFromAPRWorld(aprX, aprY, instanceID, options)
    return API.FindNearestNodeFromWorld(aprY, aprX, instanceID, options)
end

---Find the nearest node from normalized coordinates on a UI map.
function API.FindNearestNodeFromMap(uiMapID, mapX, mapY, options)
    local origin, errorCode = lib.MapToWorld(uiMapID, mapX, mapY)
    if not origin then
        return nil, errorCode
    end
    local result = API.FindNearestNodeFromWorld(origin.x, origin.y, origin.instanceID, options)
    if result then
        result.origin = origin
        result.mapPosition = API.GetNodeMapPosition(result.nodeID, uiMapID, true)
    end
    return result
end

---Find the nearest node to the current player.
function API.FindNearestNodeToPlayer(options)
    local origin, errorCode = lib.GetPlayerWorldPosition()
    if not origin then
        return nil, errorCode
    end
    options = options or {}
    if options.threeDimensional and options.z == nil then
        options.z = origin.z
    end
    local result = API.FindNearestNodeFromWorld(origin.x, origin.y, origin.instanceID, options)
    if result then
        result.origin = origin
    end
    return result
end

---Resolve a node onto a preferred/current UI map or one of its parents.
function API.ResolveNodeMapPosition(nodeID, preferredMapID)
    local candidates = {}
    local seen = {}
    AddMapAndParents(candidates, seen, preferredMapID)
    local currentMapID = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit("player") or nil
    AddMapAndParents(candidates, seen, currentMapID)

    for _, uiMapID in ipairs(candidates) do
        local position = API.GetNodeMapPosition(nodeID, uiMapID)
        if position then
            return position
        end
    end
    return nil, "no-compatible-ui-map"
end

---Set and super-track a native Blizzard waypoint for a node.
function API.SetWaypointToNode(nodeID, preferredMapID)
    local position, errorCode = API.ResolveNodeMapPosition(nodeID, preferredMapID)
    if not position then
        return false, errorCode
    end
    if not C_Map or not C_Map.SetUserWaypoint or not UiMapPoint or not UiMapPoint.CreateFromCoordinates then
        return false, "waypoint-api-unavailable"
    end

    local pointCreated, point = pcall(
        UiMapPoint.CreateFromCoordinates,
        position.mapID,
        position.x,
        position.y
    )
    if not pointCreated or not point then
        return false, "waypoint-rejected"
    end
    local success = pcall(C_Map.SetUserWaypoint, point)
    if not success then
        return false, "waypoint-rejected"
    end
    if C_SuperTrack and C_SuperTrack.SetSuperTrackedUserWaypoint then
        C_SuperTrack.SetSuperTrackedUserWaypoint(true)
    end
    return true, position
end

_G.LibTaxiData_API = API
_G.LibTaxiData_Internal = nil
