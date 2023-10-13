from pypsse.modes.pcm import ProductionCostModel
from pypsse.modes.dynamic import Dynamic
from pypsse.modes.static import Static
from pypsse.modes.snap import Snap
import numpy as np
import os

from pypsse.models import SimulationSettings

def sim_controller(psse, dyntools, settings: SimulationSettings, export_settings, logger , subsystem_buses, raw_data):
    sim_modes = {
        'Dynamic': Dynamic,
        'Steady-state': Static,
        'Snap': Snap,
        'ProductionCostModel': ProductionCostModel
    }

    sim = sim_modes[settings.simulation.simulation_mode.value](psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data)
    return sim


