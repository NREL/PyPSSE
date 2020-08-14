"""
CLI to run the PyDSS server
"""
#
# from PyDSS.api.server import pydss_server
# from aiohttp import web
import logging
import click

logger = logging.getLogger(__name__)

@click.option(
    "-p", "--port",
    default=9090,
    show_default=True,
    help="Socket port for the server",
)

@click.command()
def serve(port=9090):
    """Run a PyPSSE RESTful API server."""
    return
    # FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    # logging.basicConfig(level=logging.INFO, format=FORMAT)
    # pydss = pydss_server(port)
    # web.run_app(pydss.app, port=port)


