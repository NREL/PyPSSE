from pathlib import Path

import toml

from pypsse.models import SimulationSettings


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
