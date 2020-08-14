"""Main CLI command for PyDSS."""

import logging


import click

from pypsse.cli.create_project import create_project
from pypsse.cli.run import run
from pypsse.cli.serve import serve
from pypsse.cli.reports import reports

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """PyPSSE commands"""

cli.add_command(create_project)
cli.add_command(run)
cli.add_command(serve)
cli.add_command(reports)