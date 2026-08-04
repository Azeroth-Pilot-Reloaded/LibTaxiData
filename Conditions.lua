local lib = _G.LibTaxiData_Internal
if not lib then return end
local Compatibility = lib.Compatibility
if not Compatibility then return end

local bit = _G.bit
local band = bit and bit.band
local rshift = bit and bit.rshift

local PLAYER_CONDITION_INVERT = 0x0008
local PLAYER_CONDITION_WITHIN_OR_ABOVE = 0x0020
local PLAYER_CONDITION_USE_EFFECTIVE_LEVEL = 0x0040
local PLAYER_CONDITION_DISABLED = 0x0100
local PLAYER_CONDITION_INVERT_MODIFIER_TREE = 0x0200

local SUPPORTED_PLAYER_CONDITION_FIELDS = {
    Achievement = true,
    AchievementLogic = true,
    AuraSpellID = true,
    AuraSpellLogic = true,
    AuraStacks = true,
    ClassMask = true,
    ContentTuningID = true,
    CovenantID = true,
    CurrQuestID = true,
    CurrQuestLogic = true,
    CurrentCompletedQuestID = true,
    CurrentCompletedQuestLogic = true,
    CurrentPvpFaction = true,
    Flags = true,
    Gender = true,
    ItemCount = true,
    ItemFlags = true,
    ItemID = true,
    ItemLogic = true,
    MaxFactionID = true,
    MaxLevel = true,
    MaxReputation = true,
    MinFactionID = true,
    MinLevel = true,
    MinReputation = true,
    ModifierTreeID = true,
    NativeGender = true,
    PrevQuestID = true,
    PrevQuestLogic = true,
    RaceMasks = true,
    ReputationLogic = true,
    SpellID = true,
    SpellLogic = true,
}

local function TriAnd(left, right)
    if left == false or right == false then
        return false
    end
    if left == nil or right == nil then
        return nil
    end
    return true
end

local function TriOr(left, right)
    if left == true or right == true then
        return true
    end
    if left == nil or right == nil then
        return nil
    end
    return false
end

local function TriNot(value)
    if value == nil then
        return nil
    end
    return not value
end

local function HasFlag(value, flag)
    return band and band(value or 0, flag) ~= 0 or false
end

local function GetPlayerLevel(flags)
    if HasFlag(flags, PLAYER_CONDITION_USE_EFFECTIVE_LEVEL) and _G.UnitEffectiveLevel then
        return UnitEffectiveLevel("player")
    end
    return UnitLevel("player")
end

local function IsQuestCompleted(questID)
    return Compatibility.IsQuestCompleted(questID)
end

local function IsOnQuest(questID)
    return Compatibility.IsOnQuest(questID)
end

local function IsQuestReadyToTurnIn(questID)
    return Compatibility.IsQuestReadyToTurnIn(questID)
end

local function HasAchievement(achievementID)
    if not _G.GetAchievementInfo then
        return nil
    end
    local _, _, _, completed = GetAchievementInfo(achievementID)
    if completed == nil then
        return nil
    end
    return completed == true
end

local function GetAuraCount(spellID)
    return Compatibility.GetAuraCount(spellID)
end

local function HasAura(spellID)
    local count = GetAuraCount(spellID)
    if count == nil then
        return nil
    end
    return count > 0
end

local function KnowsSpell(spellID)
    return Compatibility.KnowsSpell(spellID)
end

local function GetItemCount(itemID, includeBank)
    return Compatibility.GetItemCount(itemID, includeBank)
end

local function GetCurrencyCount(currencyID)
    return Compatibility.GetCurrencyCount(currencyID)
end

local function GetCovenantID()
    return Compatibility.GetCovenantID()
end

local function GetFactionIndex()
    local faction = UnitFactionGroup("player")
    if faction == "Horde" then
        return 0
    end
    if faction == "Alliance" then
        return 1
    end
    return nil
end

local function EvaluateLogic(logic, results)
    local resultCount = results.n or #results
    if not band or not rshift or resultCount == 0 then
        return nil
    end

    logic = logic or 0
    local inverseMask = rshift(logic, 16)
    local function ApplyInverse(value, index)
        if band(inverseMask, 2 ^ (index - 1)) ~= 0 then
            return TriNot(value)
        end
        return value
    end

    local result = ApplyInverse(results[1], 1)
    for index = 2, resultCount do
        local operator = band(rshift(logic, 2 * (index - 2)), 3)
        local value = ApplyInverse(results[index], index)
        if operator == 1 then
            result = TriAnd(result, value)
        elseif operator == 2 then
            result = TriOr(result, value)
        end
    end
    return result
end

local function EvaluateArray(values, logic, predicate, extraValues)
    if type(values) ~= "table" then
        return true
    end
    local results = {}
    results.n = #values
    for index, value in ipairs(values) do
        if value == 0 then
            results[index] = true
        else
            results[index] = predicate(value, extraValues and extraValues[index] or nil)
        end
    end
    return EvaluateLogic(logic, results)
end

local function EvaluateRaceMask(masks)
    if type(masks) ~= "table" or not band then
        return type(masks) ~= "table" and true or nil
    end
    local _, _, raceID = UnitRace("player")
    local raceBit = raceID and lib.RaceBits[raceID]
    if raceBit == nil then
        return nil
    end
    local wordIndex = math.floor(raceBit / 32) + 1
    local word = masks[wordIndex] or 0
    return band(word, 2 ^ (raceBit % 32)) ~= 0
end

local function EvaluateClassMask(classMask)
    if not classMask or classMask == 0 then
        return true
    end
    if not band then
        return nil
    end
    local classID = select(3, UnitClass("player"))
    if not classID then
        return nil
    end
    return band(classMask, 2 ^ (classID - 1)) ~= 0
end

local function EvaluateReputation(factionID, requiredRank, maximum)
    local reaction = Compatibility.GetReputationReaction(factionID)
    if not reaction then
        return nil
    end
    local rank = reaction - 1
    if maximum then
        return rank <= (requiredRank or 0)
    end
    return rank >= (requiredRank or 0)
end

local modifierChildren

local function GetModifierChildren()
    if modifierChildren then
        return modifierChildren
    end
    modifierChildren = {}
    for treeID, tree in pairs(lib.ModifierTrees) do
        local parent = tree.parent
        if parent and parent ~= 0 then
            modifierChildren[parent] = modifierChildren[parent] or {}
            table.insert(modifierChildren[parent], treeID)
        end
    end
    return modifierChildren
end

local EvaluatePlayerCondition
local EvaluateModifierTree

local function EvaluateModifierLeaf(tree, guard)
    local modifierType = tree.type
    local asset = tree.asset
    if modifierType == 2 then
        return EvaluatePlayerCondition(asset, guard)
    elseif modifierType == 8 then
        return HasAura(asset)
    elseif modifierType == 32 then
        if not _G.GetInstanceInfo then
            return nil
        end
        return select(8, GetInstanceInfo()) == asset
    elseif modifierType == 71 then
        return UnitLevel("player") <= asset
    elseif modifierType == 73 then
        return EvaluateModifierTree(asset, guard)
    elseif modifierType == 84 then
        return IsOnQuest(asset)
    elseif modifierType == 86 or modifierType == 87 then
        return HasAchievement(asset)
    elseif modifierType == 110 then
        return IsQuestCompleted(asset)
    elseif modifierType == 111 then
        return IsQuestReadyToTurnIn(asset)
    elseif modifierType == 116 then
        local factionIndex = GetFactionIndex()
        if factionIndex == nil then
            return nil
        end
        return factionIndex == asset
    elseif modifierType == 119 then
        local quantity = GetCurrencyCount(asset)
        if quantity == nil then
            return nil
        end
        return quantity >= tree.secondaryAsset
    elseif modifierType == 257 then
        local count = GetAuraCount(tree.secondaryAsset)
        if count == nil then
            return nil
        end
        return count >= asset
    elseif modifierType == 271 then
        return TriOr(IsOnQuest(asset), IsQuestCompleted(asset))
    elseif modifierType == 272 then
        local tuning = lib.ContentTuning[asset]
        if not tuning then
            return nil
        end
        local minimum = tuning.minLevel
        if tree.secondaryAsset ~= 0 then
            minimum = minimum + (tuning.minLevelOffset or 0)
        end
        return UnitLevel("player") >= minimum
    elseif modifierType == 288 then
        local covenantID = GetCovenantID()
        if covenantID == nil then
            return nil
        end
        return covenantID == asset
    end

    -- AreaTable, phase, world-state expressions, quest objectives, garrison
    -- talents, time events and Chromie Time do not have a reliable public API
    -- equivalent. Returning nil prevents false positives.
    return nil
end

EvaluateModifierTree = function(treeID, guard)
    local tree = lib.ModifierTrees[treeID]
    if not tree then
        return nil
    end
    guard = guard or {}
    local guardKey = "tree:" .. treeID
    if guard[guardKey] then
        return nil
    end
    guard[guardKey] = true

    local result
    if tree.operator == 2 then
        result = tree.type ~= 0 and EvaluateModifierLeaf(tree, guard) or false
    elseif tree.operator == 3 then
        result = tree.type ~= 0 and TriNot(EvaluateModifierLeaf(tree, guard)) or false
    else
        local children = GetModifierChildren()[treeID] or {}
        if tree.operator == 4 then
            result = true
            for _, childID in ipairs(children) do
                result = TriAnd(result, EvaluateModifierTree(childID, guard))
                if result == false then
                    break
                end
            end
        elseif tree.operator == 8 then
            local required = math.max(tree.amount or 1, 1)
            local matches = 0
            local unknown = 0
            for _, childID in ipairs(children) do
                local childResult = EvaluateModifierTree(childID, guard)
                if childResult == true then
                    matches = matches + 1
                elseif childResult == nil then
                    unknown = unknown + 1
                end
            end
            if matches >= required then
                result = true
            elseif matches + unknown < required then
                result = false
            else
                result = nil
            end
        end
    end

    guard[guardKey] = nil
    return result
end

EvaluatePlayerCondition = function(conditionID, guard)
    if not conditionID or conditionID == 0 then
        return true
    end
    local condition = lib.PlayerConditions[conditionID]
    if not condition then
        return nil
    end
    guard = guard or {}
    local guardKey = "condition:" .. conditionID
    if guard[guardKey] then
        return nil
    end
    guard[guardKey] = true

    local flags = condition.Flags or 0
    if HasFlag(flags, PLAYER_CONDITION_DISABLED) then
        guard[guardKey] = nil
        return not HasFlag(flags, PLAYER_CONDITION_INVERT)
    end

    local result = true
    local level = GetPlayerLevel(flags)
    if condition.MinLevel and condition.MinLevel < 255 then
        result = TriAnd(result, level >= condition.MinLevel)
    end
    if condition.MaxLevel and condition.MaxLevel > 0 and condition.MaxLevel < 255 then
        result = TriAnd(result, level <= condition.MaxLevel)
    end
    if condition.ContentTuningID then
        local tuning = lib.ContentTuning[condition.ContentTuningID]
        if tuning then
            result = TriAnd(result, level >= tuning.minLevel)
            if not HasFlag(flags, PLAYER_CONDITION_WITHIN_OR_ABOVE) and tuning.maxLevel > 0 then
                result = TriAnd(result, level <= tuning.maxLevel)
            end
        else
            result = TriAnd(result, nil)
        end
    end

    result = TriAnd(result, EvaluateRaceMask(condition.RaceMasks))
    result = TriAnd(result, EvaluateClassMask(condition.ClassMask))

    if condition.Gender ~= nil then
        result = TriAnd(result, UnitSex("player") - 2 == condition.Gender)
    end
    if condition.NativeGender ~= nil then
        -- WoW exposes the current sex but not PlayerCondition's distinct
        -- native-gender field.
        result = TriAnd(result, nil)
    end
    if condition.CurrentPvpFaction then
        local factionIndex = GetFactionIndex()
        local factionResult
        if factionIndex ~= nil then
            factionResult = factionIndex == condition.CurrentPvpFaction - 1
        end
        result = TriAnd(result, factionResult)
    end

    result = TriAnd(result, EvaluateArray(condition.PrevQuestID, condition.PrevQuestLogic, IsQuestCompleted))
    result = TriAnd(result, EvaluateArray(condition.CurrQuestID, condition.CurrQuestLogic, IsOnQuest))
    result = TriAnd(result,
        EvaluateArray(condition.CurrentCompletedQuestID, condition.CurrentCompletedQuestLogic, IsQuestReadyToTurnIn))
    result = TriAnd(result, EvaluateArray(condition.SpellID, condition.SpellLogic, KnowsSpell))
    result = TriAnd(result, EvaluateArray(condition.AuraSpellID, condition.AuraSpellLogic,
        function(spellID, stacks)
            local count = GetAuraCount(spellID)
            if count == nil then
                return nil
            end
            return count >= ((stacks and stacks > 0) and stacks or 1)
        end, condition.AuraStacks))
    result = TriAnd(result, EvaluateArray(condition.Achievement, condition.AchievementLogic, HasAchievement))
    result = TriAnd(result, EvaluateArray(condition.ItemID, condition.ItemLogic,
        function(itemID, count)
            local itemCount = GetItemCount(itemID, HasFlag(condition.ItemFlags, 1))
            if itemCount == nil then
                return nil
            end
            return itemCount >= (count or 1)
        end, condition.ItemCount))

    if condition.MinFactionID then
        local reputationResults = {}
        reputationResults.n = #condition.MinFactionID
        for index, factionID in ipairs(condition.MinFactionID) do
            reputationResults[index] = factionID == 0 and true or
                EvaluateReputation(factionID, condition.MinReputation and condition.MinReputation[index])
        end
        if condition.MaxFactionID then
            reputationResults[4] = EvaluateReputation(condition.MaxFactionID, condition.MaxReputation, true)
            reputationResults.n = 4
        end
        result = TriAnd(result, EvaluateLogic(condition.ReputationLogic, reputationResults))
    elseif condition.MaxFactionID then
        result = TriAnd(result, EvaluateReputation(condition.MaxFactionID, condition.MaxReputation, true))
    end

    if condition.CovenantID then
        local covenantID = GetCovenantID()
        local covenantResult
        if covenantID ~= nil then
            covenantResult = covenantID == condition.CovenantID
        end
        result = TriAnd(result, covenantResult)
    end
    if condition.ModifierTreeID then
        local modifierResult = EvaluateModifierTree(condition.ModifierTreeID, guard)
        if HasFlag(flags, PLAYER_CONDITION_INVERT_MODIFIER_TREE) then
            modifierResult = TriNot(modifierResult)
        end
        result = TriAnd(result, modifierResult)
    end

    for field in pairs(condition) do
        if not SUPPORTED_PLAYER_CONDITION_FIELDS[field] then
            result = TriAnd(result, nil)
        end
    end

    if HasFlag(flags, PLAYER_CONDITION_INVERT) then
        result = TriNot(result)
    end
    guard[guardKey] = nil
    return result
end

lib.EvaluatePlayerCondition = EvaluatePlayerCondition
lib.EvaluateModifierTree = EvaluateModifierTree
lib.TriAnd = TriAnd
