-- This file is generated. Do not edit it by hand.
local lib = _G.LibTaxiData_Internal
if not lib then return end

lib.ClientVersions = {
    { version = "retail", name = "Retail", gameType = "mainline", projectConstant = "WOW_PROJECT_MAINLINE", apiFamily = "modern", minimumInterfaceMajor = 10 },
    { version = "classic", name = "Classic Era", gameType = "classic", projectConstant = "WOW_PROJECT_CLASSIC", apiFamily = "modern", interfaceMajor = 1, tocLabel = "Classic" },
    { version = "anniversary", name = "Anniversary / Burning Crusade Classic", gameType = "tbc", projectConstant = "WOW_PROJECT_BURNING_CRUSADE_CLASSIC", apiFamily = "modern", interfaceMajor = 2, tocLabel = "TBC" },
    { version = "wrath", name = "Wrath of the Lich King Classic", gameType = "wrath", projectConstant = "WOW_PROJECT_WRATH_CLASSIC", apiFamily = "legacy", interfaceMajor = 3, tocLabel = "Wrath" },
    { version = "cataclysm", name = "Cataclysm Classic", gameType = "cata", projectConstant = "WOW_PROJECT_CATACLYSM_CLASSIC", apiFamily = "legacy", interfaceMajor = 4, tocLabel = "Cata" },
    { version = "mists", name = "Mists of Pandaria Classic", gameType = "mists", projectConstant = "WOW_PROJECT_MISTS_CLASSIC", apiFamily = "modern", interfaceMajor = 5, tocLabel = "Mists" },
}
-- Compatibility alias for consumers of the first catalog format.
lib.ClientGameTypes = lib.ClientVersions

lib.ClientProfiles = {
    { profile = "retail", dataSet = "retail", version = "retail", gameType = "mainline", channel = "live", build = "12.1.0.69382", interface = 120100, product = "wow", default = true },
    { profile = "mists", dataSet = "mists", version = "mists", gameType = "mists", channel = "live", build = "5.5.4.69155", interface = 50504, product = "wow_classic", default = true },
    { profile = "mists_ptr", dataSet = "mists", version = "mists", gameType = "mists", channel = "ptr", build = "5.5.4.67849", interface = 50504, product = "wow_classic_ptr" },
    { profile = "classic", dataSet = "classic", version = "classic", gameType = "classic", channel = "live", build = "1.15.9.69109", interface = 11509, product = "wow_classic_era", default = true },
    { profile = "tbc", dataSet = "tbc", version = "anniversary", gameType = "tbc", channel = "ptr", build = "2.5.6.69110", interface = 20506, product = "wow_classic_era_ptr", default = true },
}
