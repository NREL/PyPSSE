"""
CLI to run the PyDSS server
"""

from pypsse.api.server import PSSEServer
from aiohttp import web
import logging
import click

logger = logging.getLogger(__name__)

@click.option(
    "-p", "--port",
    default=9090,
    show_default=True,
    help="Socket port for the server",
)

@click.option(
    "-h", "--host-ip",
    default="127.0.0.1",
    show_default=True,
    help="IP for the server",
)

@click.command()
def serve(host_ip="127.0.0.1", port=9090):
    """Run a PyPSSE RESTful API server."""
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    pydss = PSSEServer(host_ip, port)
    web.run_app(host=host_ip, port=port, app=pydss.app)
    return



