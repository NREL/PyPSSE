from datetime import datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field, model_validator
from pydantic.networks import IPvAnyAddress

from pypsse.common import CASESTUDY_FOLDER, EXPORTS_FOLDER, LOGS_FOLDER


class BulkWriteModes(Enum):
    "Supported bulk writers"
    CSV = "csv"
    PKL = "pkl"


class StreamedWriteModes(Enum):
    "Supported stream writers"
    H5 = "h5"


class SimulationModes(Enum):
    "Valid PyPSSE simulation modes"
    PCM = "PCM"
    SNAP = "Snap"
    STATIC = "Steady-state"
    DYNAMIC = "Dynamic"


class HelicsCoreTypes(Enum):
    "HILICS core types"
    ZMQ = "zmq"


class ModelTypes(Enum):
    "Supported asset tpyes in PyPSSE"
    BUSES = "Buses"
    BRANCHES = "Branches"
    LOADS = "Loads"
    GENERATORS = "Induction_generators"
    MACHINES = "Machines"
    FIXED_SHUNTS = "Fixed_shunts"
    SWITCHED_SHUNTS = "Switched_shunts"
    TRANSFORMERS = "Transformers"
    AREAS = "Areas"
    ZONES = "Zones"
    DC_LINES = "DCtransmissionlines"
    STATIONS = "Stations"


class ModelProperties(Enum):
    "Support model properties"
    PU = "PU"
    FREQ = "FREQ"
    ANGLE = "ANGLE"
    ANGLED = "ANGLED"


class LoggingLevels(IntEnum):
    "logging level setting options"
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


class SubscriptionFileRequiredColumns(Enum):
    "Subscription file requirements"
    bus_subsystem_id = "bus_subsystem_id"
    element_type = "element_type"
    element_id = "element_id"
    element_property = "element_property"
    sub_tag = "sub_tag"
    scaler = "scaler"
    bus = "bus"


class SimSettings(BaseModel):
    "Simulation setting  model defination"
    simulation_time: timedelta = timedelta(seconds=3.0)
    simulation_step_resolution: timedelta = timedelta(seconds=0.025)
    psse_solver_timestep: timedelta = timedelta(seconds=0.00333333333)
    start_time: datetime = "01/01/2020 00:00:00"
    use_profile_manager: bool
    psse_path: Path = "C:/Program Files/PTI/PSSE35/35.4/PSSPY39232"
    project_path: Path = "C:/Users/alatif/Desktop/NAERM/models/pyPSSEModel"
    case_study: Optional[Path] = None
    raw_file: Optional[Path] = None
    snp_file: Optional[Path] = None
    dyr_file: Optional[Path] = None
    rwm_file: Optional[Path] = None
    gic_file: Optional[Path] = None
    subscriptions_file: Optional[Path] = None
    user_models: List[str] = []
    setup_files: List[str] = []
    simulation_mode: SimulationModes

    @model_validator(mode="after")
    def sim_res_smaller_than_sim_time(self):
        assert (
            self.simulation_step_resolution <= self.simulation_time
        ), "simulation_step_resolution should be smaller than simulation_time"
        return self

    @model_validator(mode="after")
    def psse_res_smaller_than_sim_time(self):
        assert (
            self.psse_solver_timestep <= self.simulation_time
        ), "psse_solver_timestep should be smaller than simulation_time"
        return self

    @model_validator(mode="after")
    def validate_case_study(self):
        file_types = ["case_study", "raw_file", "snp_file", "dyr_file", "rwm_file", "gic_file"]
        base_project_path = self.project_path
        for file in file_types:
            file_path = getattr(self, file)
            if file_path:
                file_path = base_project_path / CASESTUDY_FOLDER / file_path
                setattr(self, file, file_path)
                assert file_path.exists(), f"{file_path} does not exist"
        return self

    @model_validator(mode="after")
    def validate_subscription_file(self):
        base_project_path = self.project_path
        if self.subscriptions_file:
            self.subscriptions_file = base_project_path / self.subscriptions_file
            assert self.subscriptions_file.exists(), f"{self.subscriptions_file} does not exist"
            data = pd.read_csv(self.subscriptions_file)
            csv_cols = set(data.columns)
            sub_cols = {e.value for e in SubscriptionFileRequiredColumns}
            assert sub_cols.issubset(csv_cols), f"{sub_cols} are required columns for a valid subscription file"
        return self

    @model_validator(mode="after")
    def validate_user_models(self):
        base_project_path = self.project_path
        if self.user_models:
            paths = []
            for file in self.user_models:
                model_file = base_project_path / CASESTUDY_FOLDER / file
                assert model_file.exists(), f"{model_file} does not esist"
                assert model_file.suffix == ".dll", "Invalid file extension. Use dll files"
                paths.append(model_file)
            self.user_models = paths
        return self

    @model_validator(mode="after")
    def validate_simulation_mode(self):
        if self.simulation_mode in [SimulationModes.DYNAMIC, SimulationModes.SNAP]:
            assert (
                not self.use_profile_manager
            ), "Profile manager can not be used for dynamic simulations. Set 'Use profile manager' to False"
        return self


class ExportSettings(BaseModel):
    "Export setting model defination"

    outx_file: Path = "test.outx"
    out_file: Path = "20LS11p.out"
    excel_file: Path = "20LS11p.xls"
    log_file: Path = "20LS11p.log"
    coordinate_file: Path = ""
    networkx_graph_file: Path = "20LS11p.gpickle"


class PublicationDefination(BaseModel):
    """Publication setting model defination

    Attributes:
        bus_subsystems (list(int)): Description of `attr1`.
        model_type (ModelTypes): asdsad.
        attmodel_typer2 (List, optional): Description of `attr2`.
    """

    bus_subsystems: List[int] = [
        0,
    ]
    model_type: ModelTypes = "buses"
    model_properties: List[ModelProperties] = ["FREQ", "PU"]


class HelicsSettings(BaseModel):
    "HELICS co-simualtion setting model defination"
    cosimulation_mode: bool = False
    federate_name: str = "psse"
    time_delta: timedelta = timedelta(seconds=0.00333333333)
    core_type: HelicsCoreTypes = "zmq"
    uninterruptible: bool = True
    helics_logging_level: int = Field(5, ge=1, le=10)
    create_subscriptions: bool = True
    iterative_mode: bool = False
    error_tolerance: float = Field(1e-5, g=0)
    max_coiterations: int = Field(15, ge=1)
    broker_ip: IPvAnyAddress = "127.0.0.1"
    broker_port: int = 23404
    disable_generation_on_coupled_buses: bool = True
    publications: List[PublicationDefination]


class LogSettings(BaseModel):
    "Logger setting model defination"
    disable_psse_logging: bool = True
    logging_level: LoggingLevels
    log_to_external_file: bool = True
    display_on_screen: bool = True
    clear_old_log_file: bool = True
    pre_configured_logging: bool = False


class PlotSettings(BaseModel):
    "Plotting setting model defination"
    enable_dynamic_plots: bool = False
    columns: int = Field(15, ge=1)


class GICExportSettings(BaseModel):
    "GIC export setting model defination"
    include_substation_connections: bool = False
    include_transfomer_connections: bool = False
    include_branch_connections: bool = True


class BusSubsystems(BaseModel):
    "Bus subsystem model defination"
    from_file: bool = False
    bus_file: Optional[str] = None
    bus_subsystem_list: List[List[int]] = [
        [
            74012,
            17735,
            20115,
            38205,
            70008,
            80511,
        ],
    ]
    publish_subsystems: List[int] = [
        0,
    ]


class LoadBreakdown(BaseModel):
    "Load ZIP model defination"
    constant_current_percentage: float = 0.0
    constant_admittance_percentage: float = 0.0


class LoadSettings(BaseModel):
    "Load model defination"
    convert: bool = True
    active_load: LoadBreakdown
    reactive_load: LoadBreakdown


class GeneratorSettings(BaseModel):
    "Generator model defination"
    missing_machine_model: int = 1


class BusFault(BaseModel):
    "Bus fault model defination"
    time: float = 0.2
    bus_id: int = 38205
    duration: float = 0.3
    bus_trip: bool = False
    trip_delay: float = 0.05
    fault_impedance: List[int] = [
        1.0,
        1.0,
    ]


class BusTrip(BaseModel):
    "Bus trip model defination"
    time: float = 0.2
    bus_id: int = 38205


class LineFault(BaseModel):
    "Line fault model defination"
    time: float = 0.2
    bus_ids: List[int]
    duration: float = 0.3
    bus_trip: bool = False
    trip_delay: float = 0.05
    fault_impedance: List[int] = [
        1.0,
        1.0,
    ]


class LineTrip(BaseModel):
    "Line trip model defination"
    time: float = 0.2
    bus_ids: List[int]


class MachineTrip(BaseModel):
    "Machine trip model defination"
    time: float = 0.2
    bus_id: int = 38205
    machine_id: str = ""


class SimulationSettings(BaseModel):
    "PyPSSE project settings"

    simulation: SimSettings
    export: ExportSettings
    helics: Optional[HelicsSettings] = None
    log: LogSettings
    plots: Optional[PlotSettings] = None
    gic_export_settings: Optional[GICExportSettings] = None
    bus_subsystems: BusSubsystems
    loads: LoadSettings
    generators: GeneratorSettings
    contingencies: Optional[List[Union[BusFault, LineFault, LineTrip, BusTrip, MachineTrip]]] = None

    @model_validator(mode="after")
    def validate_export_paths(self):
        base_project_path = self.simulation.project_path
        if self.export.outx_file:
            self.export.outx_file = base_project_path / EXPORTS_FOLDER / self.export.outx_file
        if self.export.out_file:
            self.export.out_file = base_project_path / EXPORTS_FOLDER / self.export.out_file
        if self.export.excel_file:
            self.export.excel_file = base_project_path / EXPORTS_FOLDER / self.export.excel_file
        if self.export.log_file:
            self.export.log_file = base_project_path / LOGS_FOLDER / self.export.log_file
        if self.export.networkx_graph_file:
            self.export.networkx_graph_file = base_project_path / EXPORTS_FOLDER / self.export.networkx_graph_file
        if self.export.coordinate_file:
            self.export.coordinate_file = base_project_path / EXPORTS_FOLDER / self.export.coordinate_file
        return self


class BusProperties(Enum):
    "Valid bus properties"

    BASE = "BASE"
    FREQ = "FREQ"
    PU = "PU"
    KV = "KV"
    ANGLE = "ANGLE"
    ANGLED = "ANGLED"
    NVLMHI = "NVLMHI"
    NVLMLO = "NVLMLO"
    EVLMHI = "EVLMHI"
    EVLMLO = "EVLMLO"


class AreaProperties(Enum):
    "Valid area properties"

    LOAD = "LOAD"
    LOADID = "LOADID"
    LGDN = "LGDN"
    LDGNLD = "LDGNLD"
    GEN = "GEN"
    AREANAME = "AREANAME"
    AREANUMBER = "AREANUMBER"


class ZoneProperties(Enum):
    "Valid zone properties"

    LOAD = "LOAD"
    LOADID = "LOADID"
    LGDN = "LGDN"
    LDGNLD = "LDGNLD"
    GEN = "GEN"
    ZONENAME = "ZONENAME"
    ZONENUMBER = "ZONENUMBER"


class StationProperties(Enum):
    "Valid station properties"

    SUBNAME = "SUBNAME"
    SUBNUMBER = "SUBNUMBER"
    BUSES = "BUSES"
    GENERATORS = "GENERATORS"
    TRANSFORMERS = "TRANSFORMERS"
    NOMKV = "NOMKV"
    LOADMW = "LOADMW"
    GENMW = "GENMW"


class DCLineProperties(Enum):
    "Valid DC line properties"

    DCLINENAME = "DCLINENAME"
    MDC = "MDC"
    RECT = "RECT"
    INV = "INV"
    METER = "METER"
    NBR = "NBR"
    NBI = "NBI"
    ICR = "ICR"
    ICI = "ICI"
    NDR = "NDR"
    NDI = "NDI"


class LoadProperties(Enum):
    "Valid load properties"

    MVA = "MVA"
    IL = "IL"
    YL = "YL"
    TOTAL = "TOTAL"
    YNEG = "YNEG"
    YZERO = "YZERO"
    FmA = "FmA"
    FmB = "FmB"
    FmC = "FmC"
    FmD = "FmD"
    Fel = "Fel"
    PFel = "PFel"
    TD = "TD"
    TC = "TC"


class FixedShuntProperties(Enum):
    "Valid fixed shunt properties"

    ACT = "ACT"
    O_ACT = "O_ACT"
    NOM = "NOM"
    O_NOM = "O_NOM"
    PQZERO = "PQZERO"
    PQZ = "PQZ"
    O_PQZ = "O_PQZ"


class SwitchedShuntProperties(Enum):
    "Valid switched shunt properties"

    VSWHI = "VSWHI"
    VSWLO = "VSWLO"
    RMPCT = "RMPCT"
    BINIT = "BINIT"
    O_BINIT = "O_BINIT"


class TransformerProperties(Enum):
    "Valid transformer properties"

    RATIO = "RATIO"
    RATIO2 = "RATIO2"
    ANGLE = "ANGLE"
    RMAX = "RMAX"
    RMIN = "RMIN"
    VMAX = "VMAX"
    VMIN = "VMIN"
    STEP = "STEP"
    CR = "CR"
    CX = "CX"
    CNXANG = "CNXANG"
    SBASE1 = "SBASE1"
    NOMV1 = "NOMV1"
    NOMV2 = "NOMV2"
    GMAGNT = "GMAGNT"
    BMAGNT = "BMAGNT"
    RG1 = "RG1"
    XG1 = "XG1"
    R01 = "R01"
    X01 = "X01"
    RG2 = "RG2"
    XG2 = "XG2"
    R02 = "R02"
    X02 = "X02"
    RNUTRL = "RNUTRL"
    XNUTRL = "XNUTRL"
    RX1_2 = "RX1-2"
    RX2_3 = "RX2-3"
    RX3_1 = "RX3-1"
    YMAGNT = "YMAGNT"
    ZG1 = "ZG1"
    Z01 = "Z01"
    ZG2 = "ZG2"
    Z02 = "Z02"
    ZG3 = "ZG3"
    Z03 = "Z03"
    ZNUTRL = "ZNUTRL"


class BranchProperties(Enum):
    "Valid branch properties"

    RATEn = "RATEn"
    RATEA = "RATEA"
    RATEB = "RATEB"
    RATEC = "RATEC"
    RATE = "RATE"
    LENGTH = "LENGTH"
    CHARG = "CHARG"
    CHARGZ = "CHARGZ"
    FRACT1 = "FRACT1"
    FRACT2 = "FRACT2"
    FRACT3 = "FRACT3"
    FRACT4 = "FRACT4"
    RX = "RX"
    ISHNT = "ISHNT"
    JSHNT = "JSHNT"
    RXZ = "RXZ"
    ISHNTZ = "ISHNTZ"
    JSHNTZ = "JSHNTZ"
    LOSSES = "LOSSES"
    O_LOSSES = "O_LOSSES"
    MVA = "MVA"
    AMPS = "AMPS"
    PUCUR = "PUCUR"
    CURANG = "CURANG"
    P = "P"
    O_P = "O_P"
    Q = "Q"
    O_Q = "O_Q"
    PLOS = "PLOS"
    O_PLOS = "O_PLOS"
    QLOS = "QLOS"
    O_QLOS = "O_QLOS"


class InductionGeneratorProperties(Enum):
    "Valid induction generator properties"

    MBASE = "MBASE"
    RATEKV = "RATEKV"
    PSET = "PSET"
    RA = "RA"
    XA = "XA"
    R1 = "R1"
    X1 = "X1"
    R2 = "R2"
    X2 = "X2"
    X3 = "X3"
    E1 = "E1"
    SE1 = "SE1"
    E2 = "E2"
    SE2 = "SE2"
    IA1 = "IA1"
    IA2 = "IA2"
    XAMULT = "XAMULT"
    TRQA = "TRQA"
    TRQB = "TRQB"
    TRQD = "TRQD"
    TRQE = "TRQE"
    H = "H"
    IRATIO = "IRATIO"
    ROVERX = "ROVERX"
    RZERO = "RZERO"
    XZERO = "XZERO"
    RGRND = "RGRND"
    XGRND = "XGRND"
    P = "P"
    O_P = "O_P"
    Q = "Q"
    O_Q = "O_Q"
    MVA = "MVA"
    O_MVA = "O_MVA"
    SLIP = "SLIP"
    ZA = "ZA"
    Z1 = "Z1"
    Z2 = "Z2"
    ZZERO = "ZZERO"
    ZGRND = "ZGRND"
    PQ = "PQ"
    O_PQ = "O_PQ"


class MachinesProperties(Enum):
    "Valid machine properties"

    QMAX = "QMAX"
    O_QMAX = "O_QMAX"
    QMIN = "QMIN"
    O_QMIN = "O_QMIN"
    PMAX = "PMAX"
    O_PMAX = "O_PMAX"
    PMIN = "PMIN"
    O_PMIN = "O_PMIN"
    MBASE = "MBASE"
    MVA = "MVA"
    O_MVA = "O_MVA"
    P = "P"
    O_P = "O_P"
    Q = "Q"
    O_Q = "O_Q"
    PERCENT = "PERCENT"
    GENTAP = "GENTAP"
    VSCHED = "VSCHED"
    WPF = "WPF"
    RMPCT = "RMPCT"
    RPOS = "RPOS"
    XSUBTR = "XSUBTR"
    XTRANS = "XTRANS"
    XSYNCH = "XSYNCH"
    PQ = "PQ"
    O_PQ = "O_PQ"
    ZSORCE = "ZSORCE"
    XTRAN = "XTRAN"
    ZPOS = "ZPOS"
    ZNEG = "ZNEG"
    ZZERO = "ZZERO"
    ZGRND = "ZGRND"


Channels = {
    "ANGLE = false machine relative rotor angle (degrees).": False,
    "PELEC = false machine electrical power (pu on SBASE).": False,
    "QELEC = false machine reactive power.": False,
    "ETERM = false machine terminal voltage (pu).": False,
    "EFD = false generator main field voltage (pu).": False,
    "PMECH = false turbine mechanical power (pu on MBASE).": False,
    "SPEED = false machine speed deviation from nominal (pu).": False,
    "XADIFD = false machine field current (pu).": False,
    "ECOMP = false voltage regulator compensated voltage (pu).": False,
    "VOTHSG = false stabilizer output signal (pu).": False,
    "VREF = false voltage regulator voltage setpoint (pu).": False,
    "BSFREQ = false bus pu frequency deviations.": False,
    "VOLT = false bus pu voltages (complex).": False,
    "voltage and angle.": False,
    "flow (P).": False,
    "flow (P and Q).": False,
    "flow (MVA).": False,
    "apparent impedance (R and X).": False,
    "ITERM.": False,
    "machine apparent impedance.": False,
    "VUEL = false minimum excitation limiter output signal (pu).": False,
    "VOEL = false maximum excitation limiter output signal (pu).": False,
    "PLOAD.": False,
    "QLOAD.": False,
    "GREF = false turbine governor reference.": False,
    "LCREF = false turbine load control reference.": False,
    "WVLCTY = false wind velocity (m/s).": False,
    "WTRBSP = false wind turbine rotor speed deviation (pu).": False,
    "WPITCH = false pitch angle (degrees).": False,
    "WAEROT = false aerodynamic torque (pu on MBASE).": False,
    "WROTRV = false rotor voltage (pu on MBASE).": False,
    "WROTRI = false rotor current (pu on MBASE).": False,
    "WPCMND = false active power command from wind control (pu on MBASE).": False,
    "WQCMND = false reactive power command from wind control (pu on MBASE).": False,
}


class ChannelTypes(Enum):
    "Valid channel types"

    BUSES = "buses"
    LOADS = "loads"
    MACHINES = "machines"


class UseModes(Enum):
    "Valid use modes"

    REGEX = "regex"
    LIST = "list"
    ALL = "all"


class BusChannel(BaseModel):
    "Bus channel model defination"

    asset_type: ChannelTypes = ChannelTypes.BUSES
    use: UseModes = UseModes.LIST
    regex: str = ""
    asset_list: List[int] = []
    asset_properties: List[str] = ["voltage_and_angle", "frequency"]


class LoadChannel(BaseModel):
    "Load channel model defination"

    asset_type: ChannelTypes = ChannelTypes.LOADS
    use: UseModes = UseModes.LIST
    regex: str = ""
    asset_list: List[List[str]] = [[]]
    asset_properties: List[str] = []


class MachineChannel(BaseModel):
    "Machine channel model defination"

    asset_type: ChannelTypes = ChannelTypes.MACHINES
    use: UseModes = UseModes.LIST
    regex: str = ""
    asset_list: List[List[str]] = [[]]
    asset_properties: List[str] = ["PELEC", "QELEC", "SPEED"]


class ExportModes(Enum):
    "Valid export modes"

    CSV = "csv"
    H5 = "h5"


class ExportAssetTypes(BaseModel):
    "Valid export models and associated options"

    buses: Optional[List[BusProperties]] = None
    areas: Optional[List[AreaProperties]] = None
    zones: Optional[List[ZoneProperties]] = None
    stations: Optional[List[StationProperties]] = None
    dctransmissionlines: Optional[List[DCLineProperties]] = None
    loads: Optional[List[LoadProperties]] = None
    fixed_shunts: Optional[List[FixedShuntProperties]] = None
    switched_shunts: Optional[List[SwitchedShuntProperties]] = None
    transformers: Optional[List[TransformerProperties]] = None
    branches: Optional[List[BranchProperties]] = None
    induction_generators: Optional[List[InductionGeneratorProperties]] = None
    machines: Optional[List[MachinesProperties]] = None
    channels: Optional[List[str]] = None
    channel_setup: Optional[List[Union[BusChannel, LoadChannel, MachineChannel]]] = None


class ExportFileOptions(ExportAssetTypes):
    "Exoprt settings for a PyPSSE project"

    export_results_using_channels: bool = False
    defined_subsystems_only: bool = True
    file_format: ExportModes = "h5"
