local lib = _G.LibTaxiData_Internal
if not lib then return end

local WORLD = "world"
local APR_WORLD = "apr-world"
local MAP = "map"

local function IsNumber(value)
    return type(value) == "number" and value == value
end

local function NewVector(x, y)
    if not _G.CreateVector2D then
        return nil
    end
    return CreateVector2D(x, y)
end

local function IsInsideMap(position)
    return position.x >= 0 and position.x <= 1 and position.y >= 0 and position.y <= 1
end

---Convert normalized map coordinates to conventional world coordinates.
---@param uiMapID number
---@param mapX number
---@param mapY number
---@return table|nil position
---@return string|nil errorCode
function lib.MapToWorld(uiMapID, mapX, mapY)
    if not IsNumber(uiMapID) or not IsNumber(mapX) or not IsNumber(mapY) then
        return nil, "invalid-coordinates"
    end
    if not C_Map or not C_Map.GetWorldPosFromMapPos then
        return nil, "map-api-unavailable"
    end

    local vector = NewVector(mapX, mapY)
    if not vector then
        return nil, "vector-api-unavailable"
    end

    local success, instanceID, worldPosition = pcall(C_Map.GetWorldPosFromMapPos, uiMapID, vector)
    if not success or not instanceID or not worldPosition then
        return nil, "map-not-convertible"
    end

    return {
        x = worldPosition.x,
        y = worldPosition.y,
        z = 0,
        instanceID = instanceID,
        sourceMapID = uiMapID,
        coordinateSystem = WORLD,
    }
end

---Convert conventional world coordinates to normalized coordinates on a UI map.
---@param instanceID number
---@param worldX number
---@param worldY number
---@param uiMapID number
---@param allowOutOfBounds boolean|nil
---@return table|nil position
---@return string|nil errorCode
function lib.WorldToMap(instanceID, worldX, worldY, uiMapID, allowOutOfBounds)
    if not IsNumber(instanceID) or not IsNumber(worldX) or not IsNumber(worldY) or not IsNumber(uiMapID) then
        return nil, "invalid-coordinates"
    end
    if not C_Map or not C_Map.GetMapPosFromWorldPos then
        return nil, "map-api-unavailable"
    end

    local vector = NewVector(worldX, worldY)
    if not vector then
        return nil, "vector-api-unavailable"
    end

    local success, resolvedMapID, mapPosition = pcall(
        C_Map.GetMapPosFromWorldPos,
        instanceID,
        vector,
        uiMapID
    )
    if not success or not resolvedMapID or not mapPosition then
        return nil, "map-not-convertible"
    end

    local position = {
        x = mapPosition.x,
        y = mapPosition.y,
        mapID = resolvedMapID,
        instanceID = instanceID,
        coordinateSystem = MAP,
    }
    if not allowOutOfBounds and not IsInsideMap(position) then
        return nil, "outside-map"
    end
    return position
end

---Return the player position in conventional world coordinates.
---@return table|nil position
---@return string|nil errorCode
function lib.GetPlayerWorldPosition()
    if not _G.UnitPosition then
        return nil, "unit-position-unavailable"
    end

    local worldY, worldX, worldZ, instanceID = UnitPosition("player")

    -- Converting the player's best UI map position first lets C_Map apply its
    -- own continent/instance transform. This covers maps whose UnitPosition
    -- instance is not the TaxiNodes continent. UnitPosition remains the safe
    -- fallback for maps that do not expose a player map position.
    local uiMapID = C_Map and C_Map.GetBestMapForUnit and C_Map.GetBestMapForUnit("player") or nil
    if uiMapID and C_Map.GetPlayerMapPosition then
        local success, mapPosition = pcall(C_Map.GetPlayerMapPosition, uiMapID, "player")
        if success and mapPosition then
            local converted = lib.MapToWorld(uiMapID, mapPosition.x, mapPosition.y)
            if converted then
                converted.z = worldZ or 0
                return converted
            end
        end
    end

    -- UnitPosition returns Y before X. LibTaxiData deliberately exposes the
    -- conventional X/Y order used by TaxiNodes and HereBeDragons.
    if not worldX or not worldY or not instanceID then
        return nil, "player-position-unavailable"
    end

    return {
        x = worldX,
        y = worldY,
        z = worldZ or 0,
        instanceID = instanceID,
        coordinateSystem = WORLD,
    }
end

function lib.WorldPosition(worldX, worldY, worldZ, instanceID)
    return {
        x = worldX,
        y = worldY,
        z = worldZ or 0,
        instanceID = instanceID,
        coordinateSystem = WORLD,
    }
end

function lib.APRWorldPosition(worldX, worldY, worldZ, instanceID)
    return {
        x = worldY,
        y = worldX,
        z = worldZ or 0,
        instanceID = instanceID,
        coordinateSystem = APR_WORLD,
    }
end

lib.CoordinateFormats = {
    WORLD = WORLD,
    APR_WORLD = APR_WORLD,
    MAP = MAP,
}
