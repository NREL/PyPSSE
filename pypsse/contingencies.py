from abc import ABCMeta

# from pyPSSE import
from pypsse.models import BusFault, BusTrip, LineFault, LineTrip, MachineTrip, SimulationSettings


def build_contingencies(psse, settings: SimulationSettings, logger):
    system_contingencies = []
    if settings.contingencies:
        for contingency in settings.contingencies:
            contingency_type = contingency.__class__.__name__
            if contingency_type in contingencies:
                system_contingencies.append(
                    contingencies[contingency_type](psse, contingency, logger, contingency_type)
                )
                logger.debug(f'Contingency of type "{contingency_type}" added')
            else:
                logger.warning("Invalid contingency type. Valid values are: {}".format(",".join(contingencies.keys())))
    else:
        logger.debug("No contingencies to build")
    return system_contingencies


def add_contingency(contingency, cont_dict, dt, system_contingencies):
    ontingency_type = contingency.__class__.__name__
    if ontingency_type in contingencies:
        system_contingencies.append(contingencies[ontingency_type](**cont_dict))
    else:
        msg = "Invalid contingency type. Valid values are: {}".format(",".join(contingencies.keys()))
        raise Exception(msg)
    return system_contingencies, dt


class BaseFault:
    __metaclass__ = ABCMeta

    requirements = []
    fault_settings = {}
    fault_method = ""
    element = None

    def __init__(self, psse, settings, logger, contingency_type):
        self.contingency_type = contingency_type
        self.settings = settings
        self.logger = logger
        self.PSSE = psse
        self.enabled = False
        self.tripped = False

    def update(self, t):
        self.t = t
        if hasattr(self.settings, "duration"):
            if self.settings.time + self.settings.duration > t >= self.settings.time and not self.enabled:
                self.enabled = True
                self.enable_fault()
            if t >= self.settings.time + self.settings.duration and self.enabled:
                self.enabled = False
                self.disable_fault()
        elif not hasattr(self.settings, "duration") and t >= self.settings.time and not self.tripped:
            self.enable_fault()
            self.tripped = True

    def enable_fault(self):
        err = getattr(self.PSSE, self.fault_method)(**self.fault_settings)
        if err:
            self.logger.warning(f"Unable to enable {self.fault_method} at element {self.element}")
        else:
            self.logger.debug(f"{self.fault_method} applied to {self.element} at time {self.t} seconds")

    def disable_fault(self):
        err = self.PSSE.dist_clear_fault()
        if err:
            self.logger.warning(f"Unable to clear {self.fault_method} at element {self.element}")
        else:
            self.logger.debug(f"{self.fault_method} cleared at element {self.element} at time {self.t} seconds")

    def is_enabled(self):
        return self.enabled

    def is_tripped(self):
        return self.tripped


class BusFault(BaseFault):
    fault_method = "distBusFault"
    fault_settings = {}

    def __init__(self, psse, settings: BusFault, logger, contingency_type):
        super().__init__(psse, settings, logger, contingency_type)
        self.fault_settings["ibus"] = settings.bus_id
        self.fault_settings["units"] = 3
        self.fault_settings["values"] = settings.fault_impedance
        self.fault_settings["basekv"] = 0.0
        self.element = settings.bus_id


class LineFault(BaseFault):
    fault_method = "dist_branch_fault"
    fault_settings = {}

    def __init__(self, psse, settings: LineFault, logger, contingency_type):
        super().__init__(psse, settings, logger, contingency_type)
        self.fault_settings["ibus"] = settings.bus_ids[0]
        self.fault_settings["jbus"] = settings.bus_ids[1]
        self.fault_settings["id"] = settings.bus_ids[2]
        self.fault_settings["units"] = 3
        self.fault_settings["values"] = settings.fault_impedance
        self.fault_settings["basekv"] = 0.0
        self.element = settings.bus_ids


class LineTrip(BaseFault):
    fault_method = "dist_branch_trip"
    fault_settings = {}

    def __init__(self, psse, settings: LineTrip, logger, contingency_type):
        super().__init__(psse, settings, logger, contingency_type)
        self.fault_settings["ibus"] = settings.bus_ids[0]
        self.fault_settings["jbus"] = settings.bus_ids[1]
        self.element = settings.bus_ids


class BusTrip(BaseFault):
    fault_method = "distBusTrip"
    fault_settings = {}

    def __init__(self, psse, settings: BusTrip, logger, contingency_type):
        super().__init__(psse, settings, logger, contingency_type)
        self.fault_settings["ibus"] = settings.bus_id
        self.element = settings.bus_id


class MachineTrip(BaseFault):
    fault_method = "distMachineTrip"
    fault_settings = {}

    def __init__(self, psse, settings: MachineTrip, logger, contingency_type):
        super().__init__(psse, settings, logger, contingency_type)
        self.fault_settings["ibus"] = settings.bus_id
        self.fault_settings["id"] = settings.machine_id
        self.element = settings.bus_id


contingencies = {
    "BusFault": BusFault,
    "LineFault": LineFault,
    "LineTrip": LineTrip,
    "BusTrip": BusTrip,
    "MachineTrip": MachineTrip,
}
