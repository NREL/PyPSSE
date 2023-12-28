"""
CLI to run a PyDSS project
"""

from pathlib import Path

import click
import toml

from pypsse.common import EXPORTS_SETTINGS_FILENAME, SIMULATION_SETTINGS_FILENAME
from pypsse.models import ExportFileOptions, SimulationSettings
from pypsse.simulator import Simulator


@click.argument(
    "project-path",
)
@click.option(
    "-s",
    "--simulations-file",
    required=False,
    default=SIMULATION_SETTINGS_FILENAME,
    show_default=True,
    help="scenario toml file to run (over rides default)",
)
@click.command()
def run(project_path, simulations_file=None):
    """Runs a valid PyPSSE simulation."""
    file_path = Path(project_path) / simulations_file
    msg = "Simulation file not found. Use -s to choose a valid settings file"
    "if its name differs from the default file name."
    assert file_path.exists(), msg
    x = Simulator.from_setting_files(file_path)
    x.run()
