import toml
from pathlib import Path

from pypsse.models import SimulationSettings

def load_settings(file_path:Path, example_path=None):
    settings = toml.load(file_path)
    if example_path:
        settings['simulation']['project_path']= example_path
    settings = SimulationSettings(**settings)
    return settings