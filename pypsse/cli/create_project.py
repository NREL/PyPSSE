"""CLI to create a new PyPSSE project"""

import ast
import sys
import click
import logging

@click.option(
    "-P", "--path",
    required=True,
    help="path in which to create project",
)
@click.option(
    "-p", "--project",
    required=True,
    help="project name",
)
@click.option(
    "-f", "--simulation-file",
    required=False,
    show_default=True,
    default="pyPSSE_settings.toml",
    help="simulation file name",
)
@click.option(
    "-F", "--psse-project-folder",
    default=None,
    required=False,
    type=click.Path(exists=True),
    help="PSS/E project folder path",
)
@click.option(
    "-r", "--raw-file",
    required=False,
    show_default=True,
    default=None,
    help="simulation file name",
)
@click.option(
    "-d", "--dyr-file",
    required=False,
    show_default=True,
    default=None,
    help="simulation file name",
)

@click.option(
    "-e", "--export-settings-file",
    default=None,
    help="comma-delimited list of dynamic visualization types",
)

@click.command()
def create_project(path=None, project=None, simulation_file=None, psse_project_folder=None,
                   raw_file=None, dyr_file=None, export_settings_file=None):
    """Create PyPSSE project."""
    return