from abc import ABCMeta, abstractmethod
#from pyPSSE import

from pypsse.models import SimulationSettings, BusFault, LineFault, BusTrip, LineTrip, MachineTrip

def build_contingencies(psse, settings:SimulationSettings, logger):
    system_contingencies = []
    if settings.contingencies:
        for contingency in settings.contingencies:
            contingency_type = contingency.__class__.__name__
            if contingency_type in contingencies:
                system_contingencies.append(contingencies[contingency_type](
                    psse, contingency, logger, contingency_type
                ))
                logger.debug('Contingency of type "{}" added'.format(contingency_type))
            else:
                logger.warning('Invalid contingency type. Valid values are: {}'.format(
                    ','.join(contingencies.keys())
                ))
    else:
        logger.debug('No contingencies to build')
    return system_contingencies

def add_contingency(contingency, cont_dict, dt, system_contingencies):
    ontingency_type = contingency.__class__.__name__
    if ontingency_type in contingencies:
        system_contingencies.append(contingencies[ontingency_type](**cont_dict))
    else:
        raise Exception('Invalid contingency type. Valid values are: {}'.format(
            ','.join(contingencies.keys())
        ))
    return system_contingencies, dt


class _base_fault:
    __metaclass__ = ABCMeta

    requirements = []
    fault_settings = {}
    fault_method = ''
    element = None

    def __init__(self, psse, settings, logger, contingency_type):      
        self.contingency_type = contingency_type
        self.settings = settings
        self.logger = logger
        self.PSSE = psse
        self.enabled = False
        self.tripped = False
        return

    def update(self, t):
        self.t = t
        if hasattr(self.settings, 'duration'):
            if self.settings.time + self.settings.duration > t >= self.settings.time and not self.enabled:
                self.enabled = True
                self.enable_fault()
            if t >= self.settings.time + self.settings.duration and self.enabled:
                self.enabled = False
                self.disable_fault()
        else:
            if t >= self.settings.time and not self.tripped:
                self.enable_fault()
                self.tripped = True
        return

    def enable_fault(self):
        err = getattr(self.PSSE, self.fault_method)(**self.fault_settings)
        if err:
            self.logger.warning('Unable to enable {} at element {}'.format(self.fault_method, self.element))
        else:
            self.logger.debug('{} applied to {} at time {} seconds'.format(self.fault_method, self.element, self.t))
        return

    def disable_fault(self):
        err = self.PSSE.dist_clear_fault()
        if err:
            self.logger.warning('Unable to clear {} at element {}'.format(self.fault_method, self.element))
        else:
            self.logger.debug('{} cleared at element {} at time {} seconds'.format(
                self.fault_method, self.element, self.t))
        return

    def is_enabled(self):
        return self.enabled

    def is_tripped(self):
        return self.tripped


class _bus_fault(_base_fault):
    fault_method = 'dist_bus_fault'
    fault_settings = {}

    def __init__(self, psse, settings:BusFault, logger, contingency_type):
        super(_bus_fault, self).__init__(psse, settings, logger, contingency_type)
        self.fault_settings['ibus'] = settings.bus_id
        self.fault_settings['units'] = 3
        self.fault_settings['values'] = settings.fault_impedance
        self.fault_settings['basekv'] = 0.0
        self.element = settings.bus_id
        return


class _line_fault(_base_fault):
    fault_method = 'dist_branch_fault'
    fault_settings = {}

    def __init__(self, psse, settings:LineFault, logger, contingency_type):
        super(_line_fault, self).__init__(psse, settings, logger, contingency_type)
        self.fault_settings['ibus'] = settings.bus_ids[0]
        self.fault_settings['jbus'] = settings.bus_ids[1]
        self.fault_settings['id'] = settings.bus_ids[2]
        self.fault_settings['units'] = 3
        self.fault_settings['values'] = settings.fault_impedance
        self.fault_settings['basekv'] = 0.0
        self.element = settings.bus_ids
        return


class _line_trip(_base_fault):
    fault_method = 'dist_branch_trip'
    fault_settings = {}

    def __init__(self, psse, settings:LineTrip, logger, contingency_type):
        super(_line_trip, self).__init__(psse, settings, logger, contingency_type)
        self.fault_settings['ibus'] = settings.bus_ids[0]
        self.fault_settings['jbus'] = settings.bus_ids[1]
        self.element = settings.bus_ids
        return


class _bus_trip(_base_fault):
    fault_method = 'dist_bus_trip'
    fault_settings = {}

    def __init__(self, psse, settings:BusTrip, logger, contingency_type):
        super(_bus_trip, self).__init__(psse, settings, logger, contingency_type)
        self.fault_settings['ibus'] = settings.bus_id
        self.element =  settings.bus_id
        return


class _machine_trip(_base_fault):
    fault_method = 'dist_machine_trip'
    fault_settings = {}

    def __init__(self, psse, settings:MachineTrip, logger, contingency_type):
        super(_machine_trip, self).__init__(psse, settings, logger, contingency_type)
        self.fault_settings['ibus'] = settings.bus_id
        self.fault_settings['id'] = settings.machine_id
        self.element =  settings.bus_id
        return

contingencies = {
        'BusFault': _bus_fault,
        'LineFault': _line_fault,
        'LineTrip': _line_trip,
        'BusTrip': _bus_trip,
        'MachineTrip': _machine_trip
    }