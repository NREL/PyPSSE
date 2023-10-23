from pydantic import BaseModel, Field, validator
from pydantic.networks import IPvAnyAddress
from datetime import datetime, timedelta
from typing import List, Optional, Union
from enum import Enum, IntEnum
from pathlib import Path


from pypsse.common import CASESTUDY_FOLDER, EXPORTS_FOLDER, LOGS_FOLDER
import pandas as pd


class BulkWriteModes(Enum):
    CSV = "csv"
    PKL = "pkl"


class StreamedWriteModes(Enum):
    H5 = "h5"


class SimulationModes(Enum):
    PCM = "PCM"
    SNAP = "Snap"
    STATIC = "Steady-state"
    DYNAMIC = "Dynamic"


class HelicsCoreTypes(Enum):
    ZMQ = "zmq"


class ModelTypes(Enum):
    BUSES = "buses"
    BRANCHES = "branches"
    LOADS = "loads"
    GENERATORS = "induction_generators"
    MACHINES = "machines"
    FIXED_SHUNTS = "fixed_shunts"
    SWITCHED_SHUNTS = "switched_shunts"
    TRANSFORMERS = "transformers"
    AREAS = "areas"
    ZONES = "zones"
    DC_LINES = "dc_transmission_lines"
    STATIONS = "stations"


class ModelProperties(Enum):
    FREQ = "FREQ"
    PU = "PU"


class LoggingLevels(IntEnum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


class SubscriptionFileRequiredColumns(Enum):
    bus_subsystem_id = "bus_subsystem_id"
    element_type = "element_type"
    element_id = "element_id"
    property = "property"
    sub_tag = "sub_tag"
    scaler = "scaler"
    bus = "bus"


class SimSettings(BaseModel):
    simulation_time: timedelta = timedelta(seconds=3.0)
    simulation_step_resolution: timedelta = timedelta(seconds=0.025)
    psse_solver_timestep: timedelta = timedelta(seconds=0.00333333333)
    start_time: datetime = "01/01/2020 00:00:00"
    use_profile_manager: bool
    psse_path: Path = "C:/Program Files/PTI/PSSE35/35.4/PSSPY39232"
    project_path: Path = "C:/Users/alatif/Desktop/NAERM/models/pypsse_model"
    case_study: Optional[Path]
    raw_file: Optional[Path]
    snp_file: Optional[Path]
    dyr_file: Optional[Path]
    rwm_file: Optional[Path]
    gic_file: Optional[Path]
    subscriptions_file: Optional[Path]
    user_models: List[str] = []
    setup_files: List[str] = []
    simulation_mode: SimulationModes

    @validator("simulation_step_resolution")
    def sim_res_smaller_than_sim_time(cls, v, values, **kwargs):
        assert (
            v < values["simulation_time"]
        ), "simulation_step_resolution should be smaller than simulation_time"
        return v

    @validator("psse_solver_timestep")
    def psse_res_smaller_than_sim_time(cls, v, values, **kwargs):
        assert (
            v < values["simulation_time"]
        ), "psse_solver_timestep should be smaller than simulation_time"
        return v

    @validator(
        "case_study", "raw_file", "snp_file", "dyr_file", "rwm_file", "gic_file"
    )
    def validate_case_study(cls, v, values, **kwargs):
        base_project_path = Path(values["project_path"])
        if v:
            v = base_project_path / CASESTUDY_FOLDER / v
            assert v.exists(), f"{v} does not esist"
            return v
        return None

    @validator("subscriptions_file")
    def validate_subscription_file(cls, v, values, **kwargs):
        base_project_path = Path(values["project_path"])
        if v:
            v = base_project_path / v
            assert v.exists(), f"{v} does not esist"
            data = pd.read_csv(v)
            csv_cols = set(data.columns)
            sub_cols = set([e.value for e in SubscriptionFileRequiredColumns])
            assert sub_cols.issubset(
                csv_cols
            ), f"{sub_cols} are required columns for a valid subscription file"
            return v
        return None

    @validator("user_models")
    def validate_user_models(cls, v, values, **kwargs):
        base_project_path = Path(values["project_path"])
        if v:
            paths = []
            for file in v:
                model_file = base_project_path / CASESTUDY_FOLDER / file
                assert model_file.exists(), f"{model_file} does not esist"
                assert (
                    model_file.suffix == ".dll"
                ), f"Invalid file extension. Use dll files"
                paths.append(model_file)
            return paths
        return v

    @validator("simulation_mode")
    def validate_simulation_mode(cls, v, values, **kwargs):
        if v == SimulationModes.DYNAMIC:
            assert (
                values["use_profile_manager"] == False
            ), "Profile manager can not be used for dynamic simulations. Set 'Use profile manager' to False"
        return v


class ExportSettings(BaseModel):
    outx_file: Path = "test.outx"
    out_file: Path = "20LS11p.out"
    excel_file: Path = "20LS11p.xls"
    log_file: Path = "20LS11p.log"
    coordinate_file: Path = ""
    networkx_graph_file: Path = "20LS11p.gpickle"


class PublicationDefination(BaseModel):
    bus_subsystems: List[int] = [
        0,
    ]
    model_type: ModelTypes = "Buses"
    model_properties: List[ModelProperties] = ["FREQ", "PU"]


class HelicsSettings(BaseModel):
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
    disable_psse_logging: bool = True
    logging_level: LoggingLevels
    log_to_external_file: bool = True
    display_on_screen: bool = True
    clear_old_log_file: bool = True
    pre_configured_logging: bool = False


class PlotSettings(BaseModel):
    enable_dynamic_plots: bool = False
    columns: int = Field(15, ge=1)


class GICExportSettings(BaseModel):
    include_substation_connections: bool = False
    include_transfomer_connections: bool = False
    include_branch_connections: bool = True


class BusSubsystems(BaseModel):
    from_file: bool = False
    bus_file: Optional[str] = ""
    bus_subsystem_list: List[List[int]] = [[]]
    publish_subsystems: List[int] = []


class LoadBreakdown(BaseModel):
    constant_current_percentage: float = 0.0
    constant_admittance_percentage: float = 0.0


class LoadSettings(BaseModel):
    convert: bool = True
    active_load: LoadBreakdown = LoadBreakdown()
    reactive_load: LoadBreakdown = LoadBreakdown()


class GeneratorSettings(BaseModel):
    missing_machine_model: int = 1


class BusFault(BaseModel):
    time: float = 0.2
    bus_id: int = 38205
    duration: float = 0.3
    bus_trip: bool = False
    trip_delay: float = 0.05
    fault_impedance: List[float] = [
        1.0,
        1.0,
    ]


class BusTrip(BaseModel):
    time: float = 0.2
    bus_id: int = 38205


class LineFault(BaseModel):
    time: float = 0.2
    bus_ids: List[int]
    duration: float = 0.3
    bus_trip: bool = False
    trip_delay: float = 0.05
    fault_impedance: List[float] = [
        1.0,
        1.0,
    ]


class LineTrip(BaseModel):
    time: float = 0.2
    bus_ids: List[int]


class MachineTrip(BaseModel):
    time: float = 0.2
    bus_id: int = 38205
    machine_id: str = ""


class Contingencies(BaseModel):
    contingencies: Optional[List[Union[BusFault, LineFault, LineTrip, BusTrip, MachineTrip]]]

class SimulationSettings(Contingencies):
    simulation: SimSettings
    export: ExportSettings = ExportSettings()
    helics: Optional[HelicsSettings]
    log: LogSettings = LogSettings(logging_level=LoggingLevels.DEBUG)
    plots: Optional[PlotSettings]
    gic_export_Settings: Optional[GICExportSettings]
    bus_subsystems: BusSubsystems = BusSubsystems()
    loads: LoadSettings = LoadSettings()
    generators: GeneratorSettings = GeneratorSettings()

    @validator("export")
    def validate_export_paths(cls, v, values, **kwargs):
        if "simulation" not in values:
            return v
        base_project_path = Path(values["simulation"].project_path)
        if v.outx_file:
            v.outx_file = base_project_path / EXPORTS_FOLDER / v.outx_file
        if v.out_file:
            v.out_file = base_project_path / EXPORTS_FOLDER / v.out_file
        if v.excel_file:
            v.excel_file = base_project_path / EXPORTS_FOLDER / v.excel_file
        if v.log_file:
            v.log_file = base_project_path / LOGS_FOLDER / v.log_file
        if v.networkx_graph_file:
            v.networkx_graph_file = (
                base_project_path / EXPORTS_FOLDER / v.networkx_graph_file
            )
        if v.coordinate_file:
            v.coordinate_file = (
                base_project_path / EXPORTS_FOLDER / v.coordinate_file
            )
        return v


class BusProperties(Enum):
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
    LOAD = "LOAD"
    LOADID = "LOADID"
    LGDN = "LGDN"
    LDGNLD = "LDGNLD"
    GEN = "GEN"
    AREANAME = "AREANAME"
    AREANUMBER = "AREANUMBER"


class ZoneProperties(Enum):
    LOAD = "LOAD"
    LOADID = "LOADID"
    LGDN = "LGDN"
    LDGNLD = "LDGNLD"
    GEN = "GEN"
    ZONENAME = "ZONENAME"
    ZONENUMBER = "ZONENUMBER"


class StationProperties(Enum):
    SUBNAME = "SUBNAME"
    SUBNUMBER = "SUBNUMBER"
    BUSES = "BUSES"
    GENERATORS = "GENERATORS"
    TRANSFORMERS = "TRANSFORMERS"
    NOMKV = "NOMKV"
    LOADMW = "LOADMW"
    GENMW = "GENMW"


class DCLineProperties(Enum):
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
    ACT = "ACT"
    O_ACT = "O_ACT"
    NOM = "NOM"
    O_NOM = "O_NOM"
    PQZERO = "PQZERO"
    PQZ = "PQZ"
    O_PQZ = "O_PQZ"


class SwitchedShuntProperties(Enum):
    VSWHI = "VSWHI"
    VSWLO = "VSWLO"
    RMPCT = "RMPCT"
    BINIT = "BINIT"
    O_BINIT = "O_BINIT"


class TransformerProperties(Enum):
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
    BUSES = "buses"
    LOADS = "loads"
    MACHINES = "machines"


class UseModes(Enum):
    REGEX = "regex"
    LIST = "list"
    ALL = "all"


class BusChannel(BaseModel):
    type: ChannelTypes = ChannelTypes.BUSES
    use: UseModes = UseModes.LIST
    regex: str = ""
    list: List[int] = []
    properties: List[str] = ["voltage_and_angle", "frequency"]


class LoadChannel(BaseModel):
    type: ChannelTypes = ChannelTypes.LOADS
    use: UseModes = UseModes.LIST
    regex: str = ""
    list: List[List[str]] = [[]]
    properties: List[str] = []


class MachineChannel(BaseModel):
    type: ChannelTypes = ChannelTypes.MACHINES
    use: UseModes = UseModes.LIST
    regex: str = ""
    list: List[List[str]] = [[]]
    properties: List[str] = ["PELEC", "QELEC", "SPEED"]


class ExportModes(Enum):
    CSV = "csv"
    H5 = "h5"


class ExportAssetTypes(BaseModel):
    buses: Optional[List[BusProperties]]
    areas: Optional[List[AreaProperties]]
    zones: Optional[List[ZoneProperties]]
    stations: Optional[List[StationProperties]]
    dc_transmission_lines: Optional[List[DCLineProperties]]
    loads: Optional[List[LoadProperties]]
    fixed_shunts: Optional[List[FixedShuntProperties]]
    switched_shunts: Optional[List[SwitchedShuntProperties]]
    transformers: Optional[List[TransformerProperties]]
    branches: Optional[List[BranchProperties]]
    induction_generators: Optional[List[InductionGeneratorProperties]]
    machines: Optional[List[MachinesProperties]]
    channels: Optional[List[str]]
    channel_setup: Optional[
        List[Union[BusChannel, LoadChannel, MachineChannel]]
    ]


class ExportFileOptions(ExportAssetTypes):
    export_results_using_channels: bool = False
    defined_subsystems_only: bool = True
    file_format: ExportModes = "h5"
