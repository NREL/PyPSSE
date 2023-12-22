from pypsse.models import SimulationSettings
from pypsse.modes.dynamic import Dynamic
from pypsse.modes.pcm import ProductionCostModel
from pypsse.modes.snap import Snap
from pypsse.modes.static import Static


def sim_controller(psse, dyntools, settings: SimulationSettings, export_settings, logger, subsystem_buses, raw_data):
    "Sets up an appropriate simualtion controller based on user input"
    sim_modes = {"Dynamic": Dynamic, "Steady-state": Static, "Snap": Snap, "ProductionCostModel": ProductionCostModel}

    sim = sim_modes[settings.simulation.simulation_mode.value](
        psse, dyntools, settings, export_settings, logger, subsystem_buses, raw_data
    )
    return sim
