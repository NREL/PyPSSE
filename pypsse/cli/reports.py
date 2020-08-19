"""
CLI to run a PyDSS project
"""

import click

from terminaltables import SingleTable

@click.argument(
    "project-path",
)

@click.option(
    "-l", "--list",
    help="List all reports for a given project path",
    is_flag=True,
    default=False,
    show_default=True,
)

@click.option(
    "-p", "--project",
    required=False,
    help="PyPSSE project name.",
)

@click.option(
    "-i", "--index",
    help="View report by index (use -l flag to see list of available reports)",
    default=0,
    show_default=True,
)

@click.option(
    "-r", "--report",
    required=False,
    help="PyPSSE report name.",
)
@click.command()

def reports(project_path, list=False, project=None, report=None, index=0):
    """Explore and print PyPSSE reports."""
    return