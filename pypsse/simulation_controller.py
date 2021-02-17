from pypsse.Modes.Dynamic import Dynamic
from pypsse.Modes.Static import Static
from pypsse.Modes.Snap import Snap
import numpy as np
import os

def sim_controller(psse, dyntools, settings, export_settings, logger, subsystem_buses):
    sim_modes = {
        'Dynamic': Dynamic,
        'Steady-state': Static,
        'Snap': Snap
    }
    sim_mode = settings["Simulation"]["Simulation mode"]
    assert (sim_mode in sim_modes), ("Invalid 'Simulation mode' entered. Possible values are: {}".format(
        ','.join(sim_modes.keys())
    ))
    sim = sim_modes[settings["Simulation"]["Simulation mode"]](psse, dyntools, settings, export_settings, logger, subsystem_buses)
    return sim


