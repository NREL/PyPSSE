

CASESTUDY_FOLDER = "case_study"
SETTINGS_FOLDER = "settings"
EXPORTS_FOLDER = "exports"
LOGS_FOLDER = "logs"
PROFILES_FOLDER = "profiles"

SIMULATION_SETTINGS_FILENAME = "simulation_settings.toml"
EXPORTS_SETTINGS_FILENAME = "export_settings.toml"
DEFAULT_SUBSCRIPTION_FILENAMES = "Subscriptions.csv"
DEFAULT_PROFILE_MAPPING_FILENAME = "Profile_mapping.toml"
DEFAULT_PROFILE_STORE_FILENAME = "Profiles.hdf5"
PROJECT_FOLDERS = ["Case_study", "Exports", "GIS_data", "Logs", "Profiles", "Settings"]
REQUIRED_GLOBAL = ["PSSE_path", "Project Path", ["Case study", "Raw file"]]
REQUIRED_DYNAMIC = ["Dyr file"]
REQUIRED_NETWORKX = ["GIC file"]
REQUIRED_HELICS = ["Subscriptions file"]
SUBSCRIPTION_FIELDS = {"bus_subsystem_id", "bus_id", "load_id",	"load_type", "sub_tag"}

MAPPED_CLASS_NAMES = {
        "buses" : "Buses",
        "areas" : "Areas",
        "zones" : "Zones",
        "loads" : "Loads",
        "branches" : "Branches",
        "machines" : "Machines",
        "stations" : "Stations",
        "transformers" : "Transformers",
        "fixed_shunts" : "Fixed_shunts",
        "switched_shunts" : "Switched_shunts",
        "induction_generators" : "Induction_generators",
        "dc_transmission_lines" : "DCtransmissionlines",
    }



MACHINE_CHANNELS = {
    "ANGLE": 1,
    "PELEC": 2,
    "QELEC": 3,
    "ETERM": 4,
    "EFD": 5,
    "PMECH": 6,
    "SPEED": 7,
    "XADIFD": 8,
    "ECOMP": 9,
    "VOTHSG": 10,
    "VREF": 11,
    "VUEL": 12,
    "VOEL": 13,
    "GREF": 14,
    "LCREF": 15,
    "WVLCTY": 16,
    "WTRBSP": 17,
    "WPITCH": 18,
    "WAEROT": 19,
    "WROTRV": 20,
    "WROTRI": 21,
    "WPCMND": 22,
    "WQCMND": 23,
    "WAUXSG": 24,

}