from pypsse.Modes.Dynamic import Dynamic
from pypsse.Modes.Static import Static
import numpy as np
import os

def sim_controller(psse, dyntools, settings, export_settings, logger):
    sim_modes = {
        'Dynamic': Dynamic,
        'Steady-state': Static
    }
    sim_mode = settings["Simulation mode"]
    assert (sim_mode in sim_modes), ("Invalid 'Simulation mode' entered. Possible values are: {}".format(
        ','.join(sim_modes.keys())
    ))
    sim = sim_modes[settings["Simulation mode"]](psse, dyntools, settings, export_settings, logger)
    return sim

