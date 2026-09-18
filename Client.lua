local lib = _G.LibTaxiData_Internal
if not lib then return end

local versionsByID = {}
for _, candidate in ipairs(lib.ClientVersions or {}) do
    versionsByID[candidate.version] = candidate
end

local function DetectVersion(interface)
    local numericInterface = tonumber(interface) or 0
    local major = math.floor(numericInterface / 10000)
    local minor = math.floor(numericInterface / 100) % 100

    local function MatchesInterface(candidate)
        if candidate.interfaceMajor then
            return candidate.interfaceMajor == major and
                (not candidate.minimumInterfaceMinor or
                    minor >= candidate.minimumInterfaceMinor)
        end
        return candidate.minimumInterfaceMajor and
            major >= candidate.minimumInterfaceMajor
    end

    -- A project ID can be shared by multiple clients. Resolve those by their
    -- interface rule while retaining the project-only path for older clients.
    local projectMatches = {}
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        local projectID = _G[candidate.projectConstant]
        if projectID and projectID == _G.WOW_PROJECT_ID then
            projectMatches[#projectMatches + 1] = candidate
        end
    end
    if #projectMatches == 1 then
        return projectMatches[1]
    end
    if #projectMatches > 1 then
        for _, candidate in ipairs(projectMatches) do
            if MatchesInterface(candidate) then
                return candidate
            end
        end
        return nil
    end

    -- Interface-major rules are a fallback for test clients and old clients
    -- on which a project constant is missing.
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        if candidate.minimumInterfaceMinor and MatchesInterface(candidate) then
            return candidate
        end
    end
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        if candidate.interfaceMajor and MatchesInterface(candidate) then
            return candidate
        end
    end
    for _, candidate in ipairs(lib.ClientVersions or {}) do
        if candidate.minimumInterfaceMajor and MatchesInterface(candidate) then
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
