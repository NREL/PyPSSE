from pathlib import Path

import toml

from pypsse.common import SIMULATION_SETTINGS_FILENAME, EXPORTS_SETTINGS_FILENAME
from pypsse.models import SimulationSettings, ExportFileOptions


def load_settings(file_path: Path, example_path=None) -> SimulationSettings:
    """utility function to load the simulation file

    Args:
        file_path (Path): simulation file path
        example_path (_type_, optional): project path. Defaults to None.

    Returns:
        SimulationSettings: simulation settings
    """
    settings = toml.load(file_path)
    if example_path:
        settings["simulation"]["project_path"] = example_path
    settings = SimulationSettings(**settings)
    return settings


def load_project_settings(project_path: Path) -> tuple[SimulationSettings, ExportFileOptions]:
    """utility function to load the simulation file

    Args:
        file_path (Path): simulation file path
        example_path (_type_, optional): project path. Defaults to None.

    Returns:
        SimulationSettings: simulation settings
        ExportFileOptions: export settings
    """
    
    sim_file = Path(project_path) / SIMULATION_SETTINGS_FILENAME
    ext_file = Path(project_path) / EXPORTS_SETTINGS_FILENAME
    settings = toml.load(sim_file)
    settings["simulation"]["project_path"] = project_path
    sim_settings = SimulationSettings(**settings)
    settings = toml.load(ext_file)
    exp_settings = ExportFileOptions(**settings)
    return sim_settings, exp_settings
