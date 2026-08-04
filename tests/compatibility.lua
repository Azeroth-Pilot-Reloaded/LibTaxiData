-- Exercise the historical/global API adapters independently of generated data.
dofile("LibTaxiData.lua")
LibTaxiData_Internal.Client = { apiFamily = "legacy" }

local completed = { [42] = true }
function IsQuestFlaggedCompleted(questID) return completed[questID] == true end
function GetQuestLogIndexByID(questID) return questID == 43 and 1 or 0 end
function IsQuestComplete(questID) return questID == 44 end
function IsSpellKnown(spellID) return spellID == 45 end
function GetItemCount(itemID) return itemID == 46 and 3 or 0 end
function GetCurrencyInfo(currencyID)
    return "currency", currencyID == 47 and 5 or 0
end
function GetFactionInfoByID(factionID)
    return "faction", nil, factionID == 48 and 7 or 4
end
function UnitAura(_, index, filter)
    if index == 1 and filter == "HELPFUL" then
        return "Aura", nil, 2, nil, nil, nil, nil, nil, nil, 49
    end
end

dofile("Compatibility.lua")
local compatibility = assert(LibTaxiData_Internal.Compatibility)
local capabilities = assert(LibTaxiData_Internal.Client.apiCapabilities)
assert(capabilities.preferredFamily == "legacy")
assert(capabilities.questCompleted == "legacy")
assert(capabilities.auras == "legacy")
assert(capabilities.items == "legacy")
assert(capabilities.mapCoordinates == false)
assert(compatibility.IsQuestCompleted(42) == true)
assert(compatibility.IsQuestCompleted(99) == false)
assert(compatibility.IsOnQuest(43) == true)
assert(compatibility.IsQuestReadyToTurnIn(44) == true)
assert(compatibility.KnowsSpell(45) == true)
assert(compatibility.GetItemCount(46) == 3)
assert(compatibility.GetCurrencyCount(47) == 5)
assert(compatibility.GetReputationReaction(48) == 7)
assert(compatibility.GetAuraCount(49) == 2)

print("LibTaxiData legacy compatibility tests: OK")
