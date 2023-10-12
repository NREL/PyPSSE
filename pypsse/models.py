from pydantic import BaseModel, Field
from pydantic.networks import IPvAnyAddress
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import List

class SimulationModes(Enum):
    PCM = "PCM"
    SNAP = "Snap"
    STATIC = "Static"
    DYNAMIC = "Dynamic"

class HelicsCoreTypes(Emun):
    ZMQ = "zmq"

class ModelTypes(Enum):
    BUSES = "Buses"

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

class SimulationSettings(BaseModel):
    simulation_time : timedelta =  timedelta(seconds=3.0)
    simulation_step_resolution : timedelta =  timedelta(seconds=0.025)
    psse_solver_timestep : timedelta = timedelta(seconds=0.00333333333)
    simulation_mode : SimulationModes
    start_time : datetime = "01/01/2020 00:00:00"
    use_profile_manager : bool
    psse_path : Path = "C:/Program Files/PTI/PSSE35/35.4/PSSPY39"
    project_path : Path = "C:/Users/alatif/Desktop/NAERM/models/pypsse_model"
    case_study : str = "21LS1ap_basecase_dera.sav"
    raw_file : str = ""
    snp_file : str = "21LS1ap_basecase_dera.snp"
    dyr_file : str = ""
    rwm_file : str = ""
    gic_file : str = ""
    subscriptions_file = "Subscriptions.csv"
    user_models : List[str] = [ "gewt.dll",]
    setup_files : List[str] = []
    
class ExportSettings(BaseModel):
    dll_file : str = "gewt.dll"
    outx_file : str = "test.outx"
    out_file : str = "20LS11p.out"
    excel_file : str = "20LS11p.xls"
    log_file : str = "20LS11p.log"
    coordinate_file : str = ""
    networkx_graph_file : str = "20LS11p.gpickle"

class PublicationDefination(BaseModel):
    bus_subsystems: List[int] = [ 0,]
    model_type : ModelTypes = "Buses"   
    model_properties : List[ModelProperties] = [ModelProperties.freq, ModelProperties.pu]

class HelicsSettings(BaseModel):
    cosimulation_mode: bool = False
    federate_name : str = "psse"
    time_delta : timedelta = timedelta(seconds=0.00333333333)
    core_type : HelicsCoreTypes = HelicsCoreTypes.zmq
    uninterruptibleL : bool = True
    helics_logging_level : int = Field(5, ge=1, le=10)
    create_subscriptions: bool = True
    iterative_mode : bool = False
    error_tolerance : float = Field(1e-5, g=0) 
    max_coiterations : int = Field(15, ge=1)
    subscription_file : str = "Subscriptions.csv"
    broker_ip :IPvAnyAddress = "127.0.0.1"
    broker_port : int = 23404
    disable_generation_on_coupled_buses : bool = True
    publications : List(PublicationDefination)

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
    from_file : bool = false
    bus_file : str = "bus_file.csv"
    bus_subsystem_list : List[List[int]] = [ [ 74012, 17735, 20115, 38205, 70008, 80511,],]
    publish_subsystems : List[int] = [ 0,]

class LoadBreakdown(BaseModel):
    constant_current_percentage = 0.0
    constant_admittance_percentage = 0.0

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

class Contingencies(BaseModel):
    bus_fault : List[BusFault]
    line_fault: List[LineFault]
    line_trip: List[LineTrip]
    bus_trip: List[BusTrip]
    machine_trip: List[MachineTrip]

class SimulationSettings(BaseModel):
    simulation : SimulationSettings
    export : ExportSettings
    publications : PublicationDefination
    helics : HelicsSettings
    log : LogSettings
    plots : PlotSettings
    gic_export_Settings = GICExportSettings
    bus_subsystems = BusSubsystems
    loads : LoadSettings
    generators : GeneratorSettings
    contingencies : Contingencies
    