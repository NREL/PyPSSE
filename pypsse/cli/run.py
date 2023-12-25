"""
CLI to run a PyDSS project
"""


import os

import click
import toml

from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.models import SimulationSettings
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
    file_path = os.path.join(project_path, simulations_file)
    if os.path.exists(file_path):
        settings = toml.load(file_path)
        settings = SimulationSettings(**settings)
        x = Simulator(settings)
        x.run()
    else:
        msg = "Simulation file not found. Use -s to choose a valid settings file if its name differs from the default file name."
        raise Exception(msg)
