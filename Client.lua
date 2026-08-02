local lib = _G.LibTaxiData_Internal
if not lib then return end

local function DetectGameType(interface)
    local projectTypes = {
        { constant = "WOW_PROJECT_MAINLINE", gameType = "mainline" },
        { constant = "WOW_PROJECT_MISTS_CLASSIC", gameType = "mists" },
        { constant = "WOW_PROJECT_CATACLYSM_CLASSIC", gameType = "cata" },
        { constant = "WOW_PROJECT_WRATH_CLASSIC", gameType = "wrath" },
        { constant = "WOW_PROJECT_BURNING_CRUSADE_CLASSIC", gameType = "tbc" },
        { constant = "WOW_PROJECT_CLASSIC", gameType = "classic" },
    }
    for _, candidate in ipairs(projectTypes) do
        local projectID = _G[candidate.constant]
        if projectID and projectID == _G.WOW_PROJECT_ID then
            return candidate.gameType
        end
    end

    local major = math.floor((tonumber(interface) or 0) / 10000)
    if major >= 10 then return "mainline" end
    if major == 5 then return "mists" end
    if major == 4 then return "cata" end
    if major == 3 then return "wrath" end
    if major == 2 then return "tbc" end
    if major == 1 then return "classic" end
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
