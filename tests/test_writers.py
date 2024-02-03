from uuid import uuid4

from examples import static_example

from pypsse.utils.utils import load_project_settings
from pypsse.enumerations import ExportModes
from pypsse.simulator import Simulator

def test_writer_csv():
    example_path = static_example.__path__.__dict__["_path"][0]
    sim_settings, exp_settings = load_project_settings(example_path)
    sim_settings.helics.cosimulation_mode = False
    exp_settings.filename_prefix = str(uuid4())
    exp_settings.file_format = ExportModes.CSV
    sim = Simulator(sim_settings, exp_settings)
    sim.run()
    del sim


def test_writer_hdf5():
    example_path = static_example.__path__.__dict__["_path"][0]
    sim_settings, exp_settings = load_project_settings(example_path)
    sim_settings.helics.cosimulation_mode = False
    exp_settings.filename_prefix = str(uuid4())
    exp_settings.file_format = ExportModes.H5
    sim = Simulator(sim_settings, exp_settings)
    sim.run()

def test_writer_json():
    example_path = static_example.__path__.__dict__["_path"][0]
    sim_settings, exp_settings = load_project_settings(example_path)
    sim_settings.helics.cosimulation_mode = False
    exp_settings.filename_prefix = str(uuid4())
    exp_settings.file_format = ExportModes.JSON
    sim = Simulator(sim_settings, exp_settings)
    sim.run()
    # settings.export.
