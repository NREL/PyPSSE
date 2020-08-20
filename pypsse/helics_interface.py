import pandas as pd
import helics as h
import os
class helics_interface:

    n_states = 5
    init_state = 1

    def __init__(self, PSSE, sim, settings, logger):
        self.bus_pubs = ['bus_id', 'bus_Vmag', 'bus_Vang', 'bus_dev']
        self.PSSE = PSSE
        self.logger = logger
        self.settings = settings
        self.sim = sim
        self.itr = 0
        self.c_seconds = 0
        self.c_seconds_old = -1

        self._co_convergance_error_tolerance = settings['HELICS']['Error tolerance']
        self._co_convergance_max_iterations = settings['HELICS']['Max co-iterations']
        self.create_federate()

        return

    def enter_execution_mode(self):
        h.helicsFederateEnterExecutingMode(self.PSSEfederate)
        return

    def create_federate(self):
        self.fedinfo = h.helicsCreateFederateInfo()
        h.helicsFederateInfoSetCoreName(self.fedinfo, self.settings["HELICS"]['Federate name'])
        h.helicsFederateInfoSetCoreTypeFromString(self.fedinfo, self.settings["HELICS"]['Core type'])
        h.helicsFederateInfoSetCoreInitString(self.fedinfo, "--federates=1")
        h.helicsFederateInfoSetTimeProperty(
            self.fedinfo,
            h.helics_property_time_delta,
            self.settings["Simulation"]["Step resolution (sec)"]
        )
        h.helicsFederateInfoSetIntegerProperty(self.fedinfo, h.helics_property_int_log_level,
                                               self.settings["HELICS"]['Helics logging level'])
        h.helicsFederateInfoSetFlagOption(self.fedinfo, h.helics_flag_uninterruptible, True)
        self.PSSEfederate = h.helicsCreateValueFederate(self.settings["HELICS"]['Federate name'], self.fedinfo)
        return


    def register_publications(self, bus_subsystems):
        self.publications = {}
        for bus_subsystem_id in self.settings['bus_subsystems']["publish_subsystems"]:
            if bus_subsystem_id in bus_subsystems:
                buses = bus_subsystems[bus_subsystem_id]
                for bus_id in buses:
                    self.publications[bus_id] = {}
                    for bus_p in self.bus_pubs:
                        pub =  "{}.bus-{}.{}".format(self.settings["HELICS"]['Federate name'], bus_id, bus_p)
                        self.publications[bus_id][pub] = h.helicsFederateRegisterGlobalTypePublication(
                            self.PSSEfederate, pub, 'double', ''
                        )
                        self.logger.debug("Publication registered: {}".format(pub))
        return

    def register_subscriptions(self, bus_subsystem_dict):
        self.subscriptions = {}
        sub_data = pd.read_csv(
            os.path.join(
                self.settings["HELICS"]["Project Path"], 'Case_study', self.settings["HELICS"]["Subscriptions file"]
            )
        )
        sub_data = sub_data.values
        r,c = sub_data.shape

        for row in range(r):
            bus_subsystem_id = sub_data[row,0]
            bus_id = sub_data[row, 1]
            load_id = sub_data[row, 2]
            load_type = sub_data[row, 3]
            sub_tag = sub_data[row, 4]
            scaler = sub_data[row, 5]
            for subsystem_id, buses in bus_subsystem_dict.iteritems():
                if subsystem_id == bus_subsystem_id:
                    for bus in buses:
                        if bus == bus_id:
                            self.subscriptions[sub_tag] = {
                                'bus_subsystem_id' : bus_subsystem_id,
                                'bus_id': bus_id,
                                'load_id': load_id,
                                'load_type': load_type,
                                'scaler' : scaler,
                                'dStates': [self.init_state] * self.n_states,
                                'subscription':  h.helicsFederateRegisterSubscription(self.PSSEfederate, sub_tag, ""),
                            }
                            self.logger.debug("Bus subsystems {}'s bus {}'s load {} has subscribed to {}".format(
                                bus_subsystem_id,  bus_id, load_id, sub_tag
                            ))
        return

    def request_time(self, t):
        error = max([abs(x["dStates"][0] - x["dStates"][1]) for k, x in self.subscriptions.items()])
        r_seconds = self.sim.GetTotalSeconds()  # - self._dss_solver.GetStepResolutionSeconds()
        if not self.settings['HELICS']['Iterative Mode']:
            while self.c_seconds < r_seconds:
                self.c_seconds = h.helicsFederateRequestTime(self.PSSEfederate, r_seconds)
            self.logger.info('Time requested: {} - time granted: {} '.format(r_seconds, self.c_seconds))
            return True, self.c_seconds
        else:
            self.c_seconds, iteration_state = h.helicsFederateRequestTimeIterative(
                self.PSSEfederate,
                r_seconds,
                h.helics_iteration_request_iterate_if_needed
            )
            self.logger.info('Time requested: {} - time granted: {} error: {} it: {}'.format(
                r_seconds, self.c_seconds, error, self.itr))
            if error > -1 and self.itr < self._co_convergance_max_iterations:
                self.itr += 1
                return False, self.c_seconds
            else:
                self.itr = 0
                return True, self.c_seconds
        return currenttime

    def publish(self, all_bus_data):
        all_bus_data = pd.DataFrame(all_bus_data, columns=self.bus_pubs)
        for r in all_bus_data.index:
            bus_data = all_bus_data.loc[r]
            bus_id = bus_data['bus_id']
            for c in bus_data.index:
                data = bus_data[c]
                bus_property_names = self.publications[bus_id].keys()
                check = [True if c in x else False for x in bus_property_names]
                pub_id = check.index(True)
                pub_id = bus_property_names[pub_id]
                pub = self.publications[bus_id][pub_id]
                h.helicsPublicationPublishDouble(pub, data)
                self.logger.debug('pyPSSE: published "{}" for tag: {}'.format(data, pub_id))
        return

    def subscribe(self):
        for sub_tag, sub_data in self.subscriptions.items():
            sub_data['value'] = h.helicsInputGetDouble(sub_data['subscription'])
            self.logger.debug('pyPSSE: Data received {} for tag {}'.format(sub_data['value'], sub_tag))
            if self.settings['HELICS']['Iterative Mode']:
                if self.c_seconds != self.c_seconds_old:
                    sub_data['dStates'] = [self.init_state] * self.n_states
                else:
                    sub_data['dStates'].insert(0, sub_data['dStates'].pop())
        self.c_seconds_old = self.c_seconds
        return self.subscriptions

    def __del__(self):
        h.helicsFederateFinalize(self.PSSEfederate)
        state = h.helicsFederateGetState(self.PSSEfederate)
        h.helicsFederateInfoFree(self.fedinfo)
        h.helicsFederateFree(self.PSSEfederate)
        self.logger.info('HELICS federate for PyDSS destroyed')