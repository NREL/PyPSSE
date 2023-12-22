"""
CLI to run a PyDSS project
"""


import os

import click

from pypsse.common import SIMULATION_SETTINGS_FILENAME
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
    path = os.path.join(project_path, simulations_file)
    if os.path.exists(path):
        x = Simulator(path)
        # x.init()
        x.run()
    else:
        msg = f"'{path}' is not a valid path."
        raise Exception(msg)
