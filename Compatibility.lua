local lib = _G.LibTaxiData_Internal
if not lib then return end

local client = lib.Client or {}
local preferLegacy = client.apiFamily == "legacy"

local function Ordered(feature, modern, legacy)
    local override = client.apiOverrides and client.apiOverrides[feature]
    local useLegacy = override == "legacy" or
        (override ~= "modern" and preferLegacy)
    if useLegacy then
        return legacy, modern, legacy and "legacy" or modern and "modern" or false
    end
    return modern, legacy, modern and "modern" or legacy and "legacy" or false
end

local function Try(callback, ...)
    if not callback then
        return false
    end
    local success, value = pcall(callback, ...)
    return success, value
end

local function FirstResult(primary, fallback, ...)
    local success, value = Try(primary, ...)
    if success then
        return value
    end
    success, value = Try(fallback, ...)
    if success then
        return value
    end
end

local quest = _G.C_QuestLog
local auras = _G.C_UnitAuras
local spellBook = _G.C_SpellBook
local items = _G.C_Item
local currencies = _G.C_CurrencyInfo
local covenants = _G.C_Covenants
local reputation = _G.C_Reputation
local maps = _G.C_Map

local questCompletedPrimary, questCompletedFallback, questCompletedStrategy = Ordered(
    "questCompleted",
    quest and quest.IsQuestFlaggedCompleted,
    _G.IsQuestFlaggedCompleted
)
local questReadyPrimary, questReadyFallback, questReadyStrategy = Ordered(
    "questReady",
    quest and quest.IsComplete,
    _G.IsQuestComplete
)
local spellPrimary, spellFallback, spellStrategy = Ordered(
    "spellBook",
    spellBook and spellBook.IsSpellKnown,
    _G.IsSpellKnown
)
local itemPrimary, itemFallback, itemStrategy = Ordered(
    "items",
    items and items.GetItemCount,
    _G.GetItemCount
)

local Compatibility = {}

function Compatibility.IsQuestCompleted(questID)
    local completed = FirstResult(
        questCompletedPrimary,
        questCompletedFallback,
        questID
    )
    if completed == nil then return nil end
    return completed == true
end

local function ModernIsOnQuest(questID)
    if not quest or not quest.IsOnQuest then return nil end
    return quest.IsOnQuest(questID) == true
end

local function LegacyIsOnQuest(questID)
    local getIndex = _G.GetQuestLogIndexByID or
        (quest and quest.GetLogIndexForQuestID)
    if not getIndex then return nil end
    local success, index = Try(getIndex, questID)
    if not success or type(index) ~= "number" then return nil end
    return index > 0
end

local onQuestPrimary, onQuestFallback, onQuestStrategy = Ordered(
    "questLog",
    quest and quest.IsOnQuest and ModernIsOnQuest or nil,
    (_G.GetQuestLogIndexByID or (quest and quest.GetLogIndexForQuestID)) and
        LegacyIsOnQuest or nil
)

function Compatibility.IsOnQuest(questID)
    return FirstResult(onQuestPrimary, onQuestFallback, questID)
end

function Compatibility.IsQuestReadyToTurnIn(questID)
    local completed = FirstResult(questReadyPrimary, questReadyFallback, questID)
    if completed == nil then return nil end
    return completed == true
end

local function ModernAuraCount(spellID)
    local aura = auras.GetPlayerAuraBySpellID(spellID)
    if not aura then return 0 end
    return aura.applications or 1
end

local function LegacyAuraCount(spellID)
    for _, filter in ipairs({ "HELPFUL", "HARMFUL" }) do
        for index = 1, 40 do
            local name, _, applications, _, _, _, _, _, _, auraSpellID =
                UnitAura("player", index, filter)
            if not name then break end
            if auraSpellID == spellID then
                return applications or 1
            end
        end
    end
    return 0
end

local auraPrimary, auraFallback, auraStrategy = Ordered(
    "auras",
    auras and auras.GetPlayerAuraBySpellID and ModernAuraCount or nil,
    _G.UnitAura and LegacyAuraCount or nil
)

function Compatibility.GetAuraCount(spellID)
    return FirstResult(auraPrimary, auraFallback, spellID)
end

function Compatibility.KnowsSpell(spellID)
    local known = FirstResult(spellPrimary, spellFallback, spellID)
    if known == nil then return nil end
    return known == true
end

function Compatibility.GetItemCount(itemID, includeBank)
    return FirstResult(itemPrimary, itemFallback, itemID, includeBank == true)
end

local function ModernCurrencyCount(currencyID)
    local info = currencies.GetCurrencyInfo(currencyID)
    return info and info.quantity or nil
end

local function LegacyCurrencyCount(currencyID)
    return select(2, GetCurrencyInfo(currencyID))
end

local currencyPrimary, currencyFallback, currencyStrategy = Ordered(
    "currency",
    currencies and currencies.GetCurrencyInfo and ModernCurrencyCount or nil,
    _G.GetCurrencyInfo and LegacyCurrencyCount or nil
)

function Compatibility.GetCurrencyCount(currencyID)
    return FirstResult(currencyPrimary, currencyFallback, currencyID)
end

function Compatibility.GetCovenantID()
    if not covenants or not covenants.GetActiveCovenantID then return nil end
    return FirstResult(covenants.GetActiveCovenantID, nil)
end

local function ModernReputationReaction(factionID)
    local faction = reputation.GetFactionDataByID(factionID)
    return faction and faction.reaction or nil
end

local function LegacyReputationReaction(factionID)
    return select(3, GetFactionInfoByID(factionID))
end

local reputationPrimary, reputationFallback, reputationStrategy = Ordered(
    "reputation",
    reputation and reputation.GetFactionDataByID and ModernReputationReaction or nil,
    _G.GetFactionInfoByID and LegacyReputationReaction or nil
)

function Compatibility.GetReputationReaction(factionID)
    return FirstResult(reputationPrimary, reputationFallback, factionID)
end

local capabilities = {
    preferredFamily = client.apiFamily,
    questCompleted = questCompletedStrategy,
    questLog = onQuestStrategy,
    questReady = questReadyStrategy,
    auras = auraStrategy,
    spellBook = spellStrategy,
    items = itemStrategy,
    currency = currencyStrategy,
    covenant = covenants and covenants.GetActiveCovenantID and "modern" or false,
    reputation = reputationStrategy,
    mapCoordinates = maps and maps.GetWorldPosFromMapPos and
        maps.GetMapPosFromWorldPos and _G.CreateVector2D and true or false,
    playerPosition = _G.UnitPosition and true or false,
    waypoint = maps and maps.SetUserWaypoint and _G.UiMapPoint and
        _G.UiMapPoint.CreateFromCoordinates and true or false,
}

Compatibility.capabilities = capabilities
client.apiCapabilities = capabilities
lib.Compatibility = Compatibility
