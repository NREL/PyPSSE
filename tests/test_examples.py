
from pypsse.simulator import Simulator
from pypsse.common import SIMULATION_SETTINGS_FILENAME

import examples.static_example as static_example
import examples.dynamic_example as dynamic_example

from pypsse.utils.utils import load_settings

from pathlib import Path

def test_dynamic_example():
    example_path = dynamic_example.__path__.__dict__["_path"][0]
    sim_file = Path(example_path) /  SIMULATION_SETTINGS_FILENAME
    settings = load_settings(sim_file, example_path)
    sim = Simulator(settings)
    sim.run()

def test_static_example():
    example_path = static_example.__path__.__dict__["_path"][0]
    sim_file = Path(example_path) /  SIMULATION_SETTINGS_FILENAME
    settings = load_settings(sim_file, example_path)
    settings.helics.cosimulation_mode = False
    sim = Simulator(settings)
    sim.run()


