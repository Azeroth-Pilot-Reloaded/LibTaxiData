local lib = _G.LibTaxiData_Internal
if not lib then return end

local function DetectGameType(interface)
    for _, candidate in ipairs(lib.ClientGameTypes or {}) do
        local projectID = _G[candidate.projectConstant]
        if projectID and projectID == _G.WOW_PROJECT_ID then
            return candidate.gameType
        end
    end

    local major = math.floor((tonumber(interface) or 0) / 10000)
    for _, profile in ipairs(lib.ClientProfiles or {}) do
        if math.floor((tonumber(profile.interface) or 0) / 10000) == major then
            return profile.gameType
        end
    end
end

local version, buildNumber, _, interface
if _G.GetBuildInfo then
    version, buildNumber, _, interface = GetBuildInfo()
end
local detectedBuild
if type(version) == "string" and (type(buildNumber) == "string" or type(buildNumber) == "number") then
    detectedBuild = version .. "." .. tostring(buildNumber)
end
local gameType = DetectGameType(interface)

local selected
for _, profile in ipairs(lib.ClientProfiles or {}) do
    if profile.build == detectedBuild and (not gameType or profile.gameType == gameType) then
        selected = profile
        break
    end
end
if not selected and gameType then
    for _, profile in ipairs(lib.ClientProfiles or {}) do
        if profile.gameType == gameType and profile.default then
            selected = profile
            break
        end
    end
end
if not selected and not gameType then
    for _, profile in ipairs(lib.ClientProfiles or {}) do
        if profile.default then
            selected = profile
            break
        end
    end
end

if not selected then
    lib.Client = {
        detectedBuild = detectedBuild,
        detectedInterface = interface,
        gameType = gameType,
        projectID = _G.WOW_PROJECT_ID,
        supported = false,
    }
    return
end

lib.Client = {}
for key, value in pairs(selected) do
    lib.Client[key] = value
end
lib.Client.detectedBuild = detectedBuild
lib.Client.detectedInterface = interface
lib.Client.projectID = _G.WOW_PROJECT_ID
lib.Client.exactBuild = detectedBuild == selected.build
lib.Client.fallback = not lib.Client.exactBuild
lib.Client.supported = true
