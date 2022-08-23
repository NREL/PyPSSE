"""
CLI to run a PyDSS project
"""


import os
import click
from pypsse.pypsse_instance import pyPSSE_instance
from pypsse.common import SIMULATION_SETTINGS_FILENAME

@click.argument(
    "project-path",
)
@click.option(
    "-o", "--options",
    help="dict-formatted simulation settings that override the config file. " \
            "Example:  pypsse run ./project ",
)

@click.option(
    "-s", "--simulations-file",
    required=False,
    default=SIMULATION_SETTINGS_FILENAME,
    show_default=True,
    help="scenario toml file to run (over rides default)",
)

@click.command()

def run(project_path, options=None, simulations_file=None):
    """Run a PyPSSE simulation."""
    path = os.path.join(project_path, "Settings", simulations_file)
    if os.path.exists(path):
        x = pyPSSE_instance(path)
        #x.init()
        x.run()
    else:
        raise Exception (f"'{path}' is not a valid path.")
    return