from pypsse.modes.pcm import ProductionCostModel
from pypsse.modes.dynamic import Dynamic
from pypsse.modes.static import Static
from pypsse.modes.snap import Snap
import numpy as np
import os


def sim_controller(psse, dyntools, settings, export_settings, logger , subsystem_buses, raw_data):
    sim_modes = {
        'Dynamic': Dynamic,
        'Steady-state': Static,
        'Snap': Snap,
        'ProductionCostModel': ProductionCostModel
    }
    sim_mode = settings["Simulation"]["Simulation mode"]
    assert (sim_mode in sim_modes), ("Invalid 'Simulation mode' entered. Possible values are: {}".format(
        ','.join(sim_modes.keys())
    ))
    sim = sim_modes[settings["Simulation"]["Simulation mode"]](psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
    return sim


