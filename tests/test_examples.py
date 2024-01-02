from pathlib import Path

from examples import dynamic_example, static_example

from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.simulator import Simulator
from pypsse.utils.utils import load_settings


# def test_dynamic_example():
#     example_path = dynamic_example.__path__.__dict__["_path"][0]
#     sim_file = Path(example_path) / SIMULATION_SETTINGS_FILENAME
#     settings = load_settings(sim_file, example_path)
#     sim = Simulator(settings)
#     sim.run()


# def test_static_example():
#     example_path = static_example.__path__.__dict__["_path"][0]
#     sim_file = Path(example_path) / SIMULATION_SETTINGS_FILENAME
#     settings = load_settings(sim_file, example_path)
#     settings.helics.cosimulation_mode = False
#     sim = Simulator(settings)
#     sim.run()
