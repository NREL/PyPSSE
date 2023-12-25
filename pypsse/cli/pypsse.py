"""Main CLI command for PyDSS."""

import click
from loguru import logger

from pypsse.cli.create_profiles import create_profiles
from pypsse.cli.create_project import create_project
from pypsse.cli.run import run

server_dependencies_installed = True

try:
    from pypsse.cli.serve import serve
except ImportError:
    server_dependencies_installed = False
    logger.warning(
        "Server dependencies not installed. Use 'pip install pssepy[server]' to install additonal dependencies"
    )


@click.group()
def cli():
    """PyPSSE commands"""


cli.add_command(create_project)
cli.add_command(run)
cli.add_command(create_profiles)
if server_dependencies_installed:
    cli.add_command(serve)
