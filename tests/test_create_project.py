from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.enumerations import SimulationModes
from pypsse.utils.utils import load_settings 
from pypsse.simulator import Simulator


from utils import remove_temp_project, build_temp_project


def test_run_sim_static():
    project_path = build_temp_project()
    file_Path = project_path / SIMULATION_SETTINGS_FILENAME

    if file_Path.exists():
        x = Simulator.from_setting_files(file_Path)
        x.init()
        x.run()
        del x
        remove_temp_project(project_path)
    else:
        msg = f"'{file_Path}' is not a valid path."
        raise Exception(msg)


def test_run_sim_dynamic():
    project_path = build_temp_project()
    file_Path = project_path / SIMULATION_SETTINGS_FILENAME

    if file_Path.exists():
        settings = load_settings(file_Path, project_path)
        settings.simulation.simulation_mode = SimulationModes.DYNAMIC
        settings.simulation.use_profile_manager = False
        settings.helics.cosimulation_mode = False
        x = Simulator(settings)
        x.init()
        x.run()
        del x
        remove_temp_project(project_path)
    else:
        msg = f"'{file_Path}' is not a valid path."
        raise Exception(msg)
