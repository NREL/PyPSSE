"""Main CLI command for PyDSS."""

import click
import logging
from pypsse.cli.create_profiles import create_profiles
from pypsse.cli.create_project import create_project
from pypsse.cli.run import run

logger = logging.getLogger(__name__)

try:
    server_dependencies_installed = True
    from pypsse.cli.serve import serve
except ImportError:
    logger.warning("Server dependencies not installed. Use 'pip install pssepy[server]' to install additonal dependencies")


@click.group()
def cli():
    """PyPSSE commands"""

cli.add_command(create_project)
cli.add_command(run)
cli.add_command(create_profiles)
if server_dependencies_installed:
    cli.add_command(serve)
    
