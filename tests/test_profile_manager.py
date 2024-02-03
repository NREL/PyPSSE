from datetime import datetime as dt
from pathlib import Path
import datetime

from pypsse.profile_manager.common import PROFILE_VALIDATION, ProfileTypes
from pypsse.profile_manager.profile_store import ProfileManager


from examples import static_example, dynamic_example
from pypsse.utils.utils import load_project_settings

from utils import TESTING_BASE_FOLDER


from utils import remove_temp_project, build_temp_project


class Solver:
    def __init__(self):
        self.Time = dt.strptime("09/19/2018 13:55:26", "%m/%d/%Y %H:%M:%S").astimezone(None)

    def get_time(self):
        return self.Time

    def get_step_size_cec(self):
        return 1.0

    def update_time(self):
        self.Time = self.Time + datetime.timedelta(seconds=1)

    def update_object(self, *_):
        pass


def test_profile_manager_import():
    project_path = build_temp_project()
    sim_settings, _ = load_project_settings(project_path)

    solver = Solver()
    a = ProfileManager(solver, sim_settings)
    profile_file =  Path(TESTING_BASE_FOLDER) / "data" / "test_profiles" / "machine.csv"
    assert profile_file.exists(), f"The profile file does not exist - {profile_file}"
    a.add_profiles_from_csv(
        csv_file= profile_file,
        name="test2",
        p_type=ProfileTypes.MACHINE,
        start_time=dt.strptime("2018-09-19 13:55:26.001", "%Y-%m-%d %H:%M:%S.%f").astimezone(None),
        resolution_sec=1,
        units="MW",
    )

def test_profile_manager():
    example_path = dynamic_example.__path__.__dict__["_path"][0]
    sim_settings, _ = load_project_settings(example_path)
    solver = Solver()
    a = ProfileManager(solver, sim_settings)
    a.setup_profiles()
    for i in range(30):
        a.update()
        solver.update_time()
        
