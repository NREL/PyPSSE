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
    BUSES = "Buses"
    BRANCHES = 'Branches'
    LOADS = 'Loads'
    GENERATORS = 'Induction_generators'
    MACHINES = 'Machines'
    FIXED_SHUNTS = 'Fixed_shunts'
    SWITCHED_SHUNTS = 'Switched_shunts'
    TRANSFORMERS = 'Transformers'
    AREAS = "Areas"
    ZONES = "Zones"
    DC_LINES = "DCtransmissionlines"
    STATIONS = "Stations"

class ModelProperties(Enum):
    FREQ = "FREQ"
    PU = "PU"
    
class LoggingLevels(IntEnum):
    NOTSET=0
    DEBUG=10
    INFO=20
    WARN=30
    ERROR=40
    CRITICAL=50
    
class SubscriptionFileRequiredColumns(Enum):
    bus_subsystem_id = 	"bus_subsystem_id"
    element_type = "element_type"	
    element_id = "element_id"	
    property = "property"	
    sub_tag	 = "sub_tag"
    scaler = "scaler"
    bus	= "bus"


class SimSettings(BaseModel):
    simulation_time : timedelta =  timedelta(seconds=3.0)
    simulation_step_resolution : timedelta =  timedelta(seconds=0.025)
    psse_solver_timestep : timedelta = timedelta(seconds=0.00333333333)
    start_time : datetime = "01/01/2020 00:00:00"
    use_profile_manager : bool
    psse_path : Path = "C:/Program Files/PTI/PSSE35/35.4/PSSPY39232"
    project_path : Path = "C:/Users/alatif/Desktop/NAERM/models/pypsse_model"
    case_study : Optional[Path] 
    raw_file : Optional[Path] 
    snp_file : Optional[Path] 
    dyr_file : Optional[Path] 
    rwm_file : Optional[Path] 
    gic_file : Optional[Path] 
    subscriptions_file : Optional[Path]
    user_models : List[str] = []
    setup_files : List[str] = []
    simulation_mode : SimulationModes
    
    @validator('simulation_step_resolution')
    def sim_res_smaller_than_sim_time(cls, v, values, **kwargs):
        assert v < values['simulation_time'], "simulation_step_resolution should be smaller than simulation_time"
        return v
    
    @validator('psse_solver_timestep')
    def psse_res_smaller_than_sim_time(cls, v, values, **kwargs):
        assert v < values['simulation_time'], "psse_solver_timestep should be smaller than simulation_time"     
        return v
    
    @validator('case_study', "raw_file", "snp_file", "dyr_file", "rwm_file", "gic_file")
    def validate_case_study(cls, v, values, **kwargs):
        base_project_path = Path(values["project_path"])
        if v:
            v = base_project_path / CASESTUDY_FOLDER / v
            assert v.exists(), f"{v} does not esist" 
            return v
        return None

    @validator('subscriptions_file')
    def validate_subscription_file(cls, v, values, **kwargs):
        base_project_path = Path(values["project_path"])
        if v:
            v = base_project_path / v
            assert v.exists(), f"{v} does not esist"
            data = pd.read_csv(v)
            csv_cols = set(data.columns)
            sub_cols = set([e.value for e in SubscriptionFileRequiredColumns])
            assert sub_cols.issubset(csv_cols), f"{sub_cols} are required columns for a valid subscription file"
            return v
        return None
    
    @validator('user_models')
    def validate_user_models(cls, v, values, **kwargs):
        base_project_path = Path(values["project_path"])
        if v:
            paths = []
            for file in v:
                model_file = base_project_path / CASESTUDY_FOLDER / file
                assert model_file.exists(), f"{model_file} does not esist" 
                assert model_file.suffix == ".dll", f"Invalid file extension. Use dll files"
                paths.append(model_file)
            return paths
        return v
    
    @validator('simulation_mode')
    def validate_simulation_mode(cls, v, values, **kwargs):
        if v == SimulationModes.DYNAMIC:
            assert values["use_profile_manager"] == False, "Profile manager can not be used for dynamic simulations. Set 'Use profile manager' to False"
        return v
    
class ExportSettings(BaseModel):
    outx_file : Path = "test.outx"
    out_file : Path = "20LS11p.out"
    excel_file : Path = "20LS11p.xls"
    log_file : Path = "20LS11p.log"
    coordinate_file : Path = ""
    networkx_graph_file : Path = "20LS11p.gpickle"

    
class PublicationDefination(BaseModel):
    bus_subsystems: List[int] = [ 0,]
    model_type : ModelTypes = "Buses"   
    model_properties : List[ModelProperties] = ["FREQ", "PU"]

class HelicsSettings(BaseModel):
    cosimulation_mode: bool = False
    federate_name : str = "psse"
    time_delta : timedelta = timedelta(seconds=0.00333333333)
    core_type : HelicsCoreTypes = "zmq"
    uninterruptible : bool = True
    helics_logging_level : int = Field(5, ge=1, le=10)
    create_subscriptions: bool = True
    iterative_mode : bool = False
    error_tolerance : float = Field(1e-5, g=0) 
    max_coiterations : int = Field(15, ge=1)
    broker_ip :IPvAnyAddress = "127.0.0.1"
    broker_port : int = 23404
    disable_generation_on_coupled_buses : bool = True
    publications : List[PublicationDefination]

class LogSettings(BaseModel):
    disable_psse_logging : bool = True
    logging_level : LoggingLevels
    log_to_external_file : bool = True
    display_on_screen : bool = True
    clear_old_log_file : bool = True
    pre_configured_logging : bool = False
    
class PlotSettings(BaseModel):
    enable_dynamic_plots : bool = False
    columns : int = Field(15, ge=1)

class GICExportSettings(BaseModel):
    include_substation_connections: bool = False
    include_transfomer_connections: bool = False
    include_branch_connections: bool = True

class BusSubsystems(BaseModel):
    from_file : bool = False
    bus_file : Optional[str] 
    bus_subsystem_list : List[List[int]] = [ [ 74012, 17735, 20115, 38205, 70008, 80511,],]
    publish_subsystems : List[int] = [ 0,]

class LoadBreakdown(BaseModel):
    constant_current_percentage : float = 0.0
    constant_admittance_percentage : float = 0.0

class LoadSettings(BaseModel):
    convert : bool = True
    active_load : LoadBreakdown
    reactive_load: LoadBreakdown

class GeneratorSettings(BaseModel):
    missing_machine_model : int = 1

class BusFault(BaseModel):
    time : float = 0.2
    bus_id : int = 38205
    duration: float = 0.3
    bus_trip  : bool = False
    trip_delay : float = 0.05
    fault_impedance : List[int] = [ 1.0, 1.0,]

class BusTrip(BaseModel):
    time : float = 0.2
    bus_id : int = 38205

class LineFault(BaseModel):
    time : float = 0.2
    bus_ids : List[int] 
    duration: float = 0.3
    bus_trip  : bool = False
    trip_delay : float = 0.05
    fault_impedance : List[int] = [ 1.0, 1.0,]
    
class LineTrip(BaseModel):
    time : float = 0.2
    bus_ids : List[int] 

class MachineTrip(BaseModel):
    time : float = 0.2
    bus_id : int = 38205
    machine_id : str = ""

class SimulationSettings(BaseModel):
    simulation : SimSettings
    export : ExportSettings
    helics : Optional[HelicsSettings]
    log : LogSettings
    plots : Optional[PlotSettings]
    gic_export_Settings : Optional[GICExportSettings]
    bus_subsystems : BusSubsystems
    loads : LoadSettings
    generators : GeneratorSettings
    contingencies : Optional[List[Union[BusFault, LineFault, LineTrip, BusTrip,MachineTrip]]]

    @validator('export')
    def validate_export_paths(cls, v, values, **kwargs):
        if 'simulation' not in values:
            return v
        base_project_path = Path(values['simulation'].project_path)
        if v.outx_file:
            v.outx_file = base_project_path / EXPORTS_FOLDER / v.outx_file
        if v.out_file:
            v.out_file = base_project_path / EXPORTS_FOLDER / v.out_file
        if v.excel_file:
            v.excel_file = base_project_path / EXPORTS_FOLDER / v.excel_file
        if v.log_file:
            v.log_file = base_project_path / LOGS_FOLDER / v.log_file
        if v.networkx_graph_file:
            v.networkx_graph_file = base_project_path / EXPORTS_FOLDER / v.networkx_graph_file
        if v.coordinate_file:
            v.coordinate_file = base_project_path / EXPORTS_FOLDER / v.coordinate_file
        return v