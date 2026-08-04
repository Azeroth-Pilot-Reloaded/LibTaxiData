local lib = _G.LibTaxiData_Internal
if not lib then return end

local versionsByID = {}
for _, candidate in ipairs(lib.ClientVersions or {}) do
    versionsByID[candidate.version] = candidate
end

local function DetectVersion(interface)
    -- Project constants are authoritative and continue to work when a family
    -- currently has no active profile/server in tools/profiles.json.
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        local projectID = _G[candidate.projectConstant]
        if projectID and projectID == _G.WOW_PROJECT_ID then
            return candidate
        end
    end

    -- Interface-major rules are a fallback for test clients and old clients
    -- on which a project constant is missing.
    local major = math.floor((tonumber(interface) or 0) / 10000)
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        if candidate.interfaceMajor == major then
            return candidate
        end
    end
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        if candidate.minimumInterfaceMajor and major >= candidate.minimumInterfaceMajor then
            return candidate
        end
    end
end

local versionString, buildNumber, _, interface
if _G.GetBuildInfo then
    versionString, buildNumber, _, interface = GetBuildInfo()
end
local detectedBuild
if type(versionString) == "string" and
    (type(buildNumber) == "string" or type(buildNumber) == "number") then
    detectedBuild = versionString .. "." .. tostring(buildNumber)
end
local detectedVersion = DetectVersion(interface)

local selected
for _, profile in ipairs(lib.ClientProfiles or {}) do
    if profile.build == detectedBuild and
        (not detectedVersion or profile.version == detectedVersion.version) then
        selected = profile
        break
    end
end
if selected and not detectedVersion then
    detectedVersion = versionsByID[selected.version]
end
if not selected and detectedVersion then
    for _, profile in ipairs(lib.ClientProfiles or {}) do
        if profile.version == detectedVersion.version and profile.default then
            selected = profile
            break
        end
    end
end

lib.Client = {}
if detectedVersion then
    for key, value in pairs(detectedVersion) do
        lib.Client[key] = value
    end
end
lib.Client.detectedBuild = detectedBuild
lib.Client.detectedInterface = interface
lib.Client.detectedVersion = detectedVersion and detectedVersion.version or nil
lib.Client.projectID = _G.WOW_PROJECT_ID

if not selected then
    lib.Client.supported = false
    return
end

local baseVersion = versionsByID[selected.version]
if baseVersion then
    for key, value in pairs(baseVersion) do
        lib.Client[key] = value
    end
end
for key, value in pairs(selected) do
    lib.Client[key] = value
end
lib.Client.exactBuild = detectedBuild == selected.build
lib.Client.fallback = not lib.Client.exactBuild
lib.Client.supported = true
