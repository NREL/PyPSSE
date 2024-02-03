from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.enumerations import SimulationModes
from pypsse.simulator import Simulator
from pypsse.utils.utils import load_settings

from utils import build_temp_project, remove_temp_project

def run_sim_dynamic():
    project_path = build_temp_project()
    file_Path = project_path / SIMULATION_SETTINGS_FILENAME

    if file_Path.exists():
        settings = load_settings(file_Path, project_path)
        settings.simulation.simulation_mode = SimulationModes.DYNAMIC
        settings.simulation.use_profile_manager = False
        settings.helics.cosimulation_mode = False
        x = Simulator(settings)
        yield x
        x.init()
        x.run()
        del x
        remove_temp_project(project_path)
    else:
        msg = f"'{file_Path}' is not a valid path."
        raise Exception(msg)

def test_run_sim_dynamic_save_model():
    simulators = run_sim_dynamic()
    simulator = next(simulators)
    files = simulator.sim.save_model()
    for file in files:
        assert file.exists(), f"{file}"

def test_disable_generation():
    simulators = run_sim_dynamic()
    simulator = next(simulators)
    


def test_disbale_load_model():
    simulators = run_sim_dynamic()
    simulator = next(simulators)


def test_channel_setup():
    simulators = run_sim_dynamic()
    simulator = next(simulators)


def test_load_break():
    simulators = run_sim_dynamic()
    simulator = next(simulators)
