import datetime
from datetime import datetime as dt

import toml

from pypsse.profile_manager.profile_store import ProfileManager


def test_profile_manager():
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

    settings = toml.load(r"C:\Users\alatif\Desktop\pypsse-usecases\PSSE_WECC_model\Settings\simulation_settings.toml")
    solver = Solver()
    a = ProfileManager(None, solver, settings)
    # a.setup_profiles()
    # for i in range(30):
    #     a.update()
    #     solver.update_time()

    a.add_profiles_from_csv(
        csv_file=r"C:\Users\alatif\Desktop\pypsse-usecases\PSSE_WECC_model\Profiles\machine.csv",
        name="test",
        p_type="Machine",
        start_time=dt.strptime("2018-09-19 13:55:26.001", "%Y-%m-%d %H:%M:%S.%f").astimezone(None),
        resolution_sec=1,
        units="MW",
    )
