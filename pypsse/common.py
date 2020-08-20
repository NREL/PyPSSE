
SIMULATION_SETTINGS_FILENAME = "pyPSSE_settings.toml"
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