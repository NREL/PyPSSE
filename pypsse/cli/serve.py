"""
CLI to run the PyDSS server
"""
import click

from pypsse.api.server import run_server


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
    run_server(host_ip, port)
