from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field, model_validator
from pydantic.networks import IPvAnyAddress

from pypsse.common import CASESTUDY_FOLDER, EXPORTS_FOLDER, LOGS_FOLDER
from pypsse.enumerations import (
    AreaProperties,
    BranchProperties,
    BusProperties,
    ChannelTypes,
    DCLineProperties,
    ExportModes,
    FixedShuntProperties,
    HelicsCoreTypes,
    InductionGeneratorProperties,
    LoadProperties,
    LoggingLevels,
    MachinesProperties,
    ModelProperties,
    ModelTypes,
    SimulationModes,
    StationProperties,
    SubscriptionFileRequiredColumns,
    SwitchedShuntProperties,
    TransformerProperties,
    UseModes,
    ZoneProperties,
)


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
