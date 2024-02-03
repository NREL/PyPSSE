from uuid import uuid4

from examples import dynamic_example, static_example

from pypsse.simulator import Simulator
from pypsse.utils.utils import load_project_settings


def test_dynamic_example():
    example_path = dynamic_example.__path__.__dict__["_path"][0]
    sim_settings, exp_settings = load_project_settings(example_path)
    if sim_settings.helics:
        sim_settings.helics.cosimulation_mode = False
    exp_settings.filename_prefix = str(uuid4())
    sim = Simulator(sim_settings, exp_settings)
    sim.run()
    del sim


def test_static_example():
    example_path = static_example.__path__.__dict__["_path"][0]
    sim_settings, exp_settings = load_project_settings(example_path)
    sim_settings.helics.cosimulation_mode = False
    exp_settings.filename_prefix = str(uuid4())
    sim = Simulator(sim_settings, exp_settings)
    sim.run()
    del sim
