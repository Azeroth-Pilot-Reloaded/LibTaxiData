-- This file is generated. Do not edit it by hand.
local lib = _G.LibTaxiData_Internal
if not lib then return end

lib.ClientGameTypes = {
    { gameType = "mainline", projectConstant = "WOW_PROJECT_MAINLINE" },
    { gameType = "mists", projectConstant = "WOW_PROJECT_MISTS_CLASSIC" },
    { gameType = "classic", projectConstant = "WOW_PROJECT_CLASSIC" },
    { gameType = "tbc", projectConstant = "WOW_PROJECT_BURNING_CRUSADE_CLASSIC" },
    { gameType = "wrath", projectConstant = "WOW_PROJECT_WRATH_CLASSIC" },
    { gameType = "cata", projectConstant = "WOW_PROJECT_CATACLYSM_CLASSIC" },
}

lib.ClientProfiles = {
    { profile = "retail", dataSet = "retail", gameType = "mainline", channel = "live", build = "12.0.7.68887", interface = 120007, product = "wow", default = true },
    { profile = "retail_ptr", dataSet = "retail_ptr", gameType = "mainline", channel = "ptr", build = "12.1.0.68914", interface = 120100, product = "wowt" },
    { profile = "mists", dataSet = "mists", gameType = "mists", channel = "live", build = "5.5.4.68806", interface = 50504, product = "wow_classic", default = true },
    { profile = "mists_ptr", dataSet = "mists", gameType = "mists", channel = "ptr", build = "5.5.4.67849", interface = 50504, product = "wow_classic_ptr" },
    { profile = "classic", dataSet = "classic", gameType = "classic", channel = "live", build = "1.15.9.68940", interface = 11509, product = "wow_classic_era", default = true },
    { profile = "tbc", dataSet = "tbc", gameType = "tbc", channel = "ptr", build = "2.5.6.68184", interface = 20506, product = "wow_classic_era_ptr", default = true },
}
