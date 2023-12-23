"""
CLI to run the PyDSS server
"""

import logging

import click

from pypsse.api.server import run_server

logger = logging.getLogger(__name__)


@click.option(
    "-p",
    "--port",
    default=9090,
    show_default=True,
    help="Socket port for the server",
)
@click.option(
    "-h",
    "--host-ip",
    default="127.0.0.1",
    show_default=True,
    help="IP for the server",
)
@click.command()
def serve(host_ip="127.0.0.1", port=9090):
    """Run a PyPSSE RESTful API server."""
    timestamp_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=timestamp_format)
    run_server(host_ip, port)
