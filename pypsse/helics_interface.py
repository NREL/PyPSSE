from pypsse.ProfileManager.common import PROFILE_VALIDATION
import pandas as pd
import helics as h
import ast
import os

class helics_interface:

    n_states = 5
    init_state = 1

    def __init__(self, PSSE, sim, settings, export_settings, bus_subsystems, logger):
        print("asdasdasdasdasd")
        self.bus_pubs = ['bus_id', 'bus_Vmag', 'bus_Vang', 'bus_dev']
        self.PSSE = PSSE
        self.logger = logger
        self.settings = settings
        self.export_settings = export_settings
        self.bus_subsystems = bus_subsystems
        self.sim = sim
        self.itr = 0
        self.c_seconds = 0
        self.c_seconds_old = -1

        self._co_convergance_error_tolerance = settings['HELICS']['Error tolerance']
        self._co_convergance_max_iterations = settings['HELICS']['Max co-iterations']
        self.create_federate()
        self.subsystem_info = []
        self.publications = {}
        self.subscriptions = {}
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
        self.pub_struc = []
        for publicationDict in self.settings['HELICS']["Publications"]:

            bus_subsystem_ids = publicationDict["bus_subsystems"]
            if not set(bus_subsystem_ids).issubset(self.bus_subsystems):
                raise Exception(f"One or more invalid bus subsystem ID pass in {bus_subsystem_ids}."
                                f"Valid subsystem IDs are  '{list(self.bus_subsystems.keys())}'.")

            elmClass = publicationDict["class"]
            if elmClass not in self.export_settings:
                raise Exception(f"'{elmClass}' is not a valid class of elements. "
                                f"Valid fields are: {list(self.export_settings.keys())}")

            properties = publicationDict["properties"]
            if not set(properties).issubset(self.export_settings[elmClass]):
                raise Exception(
                    f"One or more publication property defined for class '{elmClass}' is invalid. "
                    f"Valid properties for class '{elmClass}' are '{list(self.export_settings[elmClass].keys())}'"
                )

            bus_cluster = []
            for bus_subsystem_id in bus_subsystem_ids:
                bus_cluster.extend([str(x) for x in bus_subsystems[bus_subsystem_id]])
            self.pub_struc.append([{elmClass: properties}, bus_cluster])
            temp_res = self.sim.read_subsystems({elmClass: properties}, bus_cluster)
            temp_res = self.get_restructured_results(temp_res)
            print(temp_res)
            for cName, elmInfo in temp_res.items():
                for Name, vInfo in elmInfo.items():
                    for pName, val in vInfo.items():
                        pub_tag = "{}.{}.{}.{}".format(
                            self.settings["HELICS"]['Federate name'],
                            cName,
                            Name,
                            pName
                        )
                        dtype_matched = True
                        if isinstance(val, float):
                            self.publications[pub_tag] = h.helicsFederateRegisterGlobalTypePublication(
                                self.PSSEfederate, pub_tag, 'double', '')
                        elif isinstance(val, complex):
                            self.publications[pub_tag] = h.helicsFederateRegisterGlobalTypePublication(
                                self.PSSEfederate, pub_tag, 'complex', '')
                        elif isinstance(val, int):
                            self.publications[pub_tag] = h.helicsFederateRegisterGlobalTypePublication(
                                self.PSSEfederate, pub_tag, 'integer', '')
                        elif isinstance(val, list):
                            self.publications[pub_tag] = h.helicsFederateRegisterGlobalTypePublication(
                                self.PSSEfederate, pub_tag, 'vector', '')
                        elif isinstance(val, str):
                            self.publications[pub_tag] = h.helicsFederateRegisterGlobalTypePublication(
                                self.PSSEfederate, pub_tag, 'string', '')
                        else:
                            dtype_matched = False
                            self.logger.warning(f"Publication {pub_tag} could not be registered. Data type not found")
                        if dtype_matched:
                            self.logger.debug("Publication registered: {}".format(pub_tag))
        # self.publications = {}
        # for bus_subsystem_id in self.settings['bus_subsystems']["publish_subsystems"]:
        #     if bus_subsystem_id in bus_subsystems:
        #         buses = bus_subsystems[bus_subsystem_id]
        #         for bus_id in buses:
        #             self.publications[bus_id] = {}
        #             for bus_p in self.bus_pubs:
        #                 pub = "{}.bus-{}.{}".format(self.settings["HELICS"]['Federate name'], bus_id, bus_p)
        #                 self.publications[bus_id][pub] = h.helicsFederateRegisterGlobalTypePublication(
        #                     self.PSSEfederate, pub, 'double', ''
        #                 )
        #                 self.logger.debug("Publication registered: {}".format(pub))
        return

    def register_subscriptions(self, bus_subsystem_dict):
        self.subscriptions = {}
        sub_data = pd.read_csv(
            os.path.join(
                self.settings["Simulation"]["Project Path"], 'Settings', self.settings["HELICS"]["Subscriptions file"]
            )
        )
        self.psse_dict = {}
        for ix, row in sub_data.iterrows():

            row['property'] = ast.literal_eval(row['property'])
            if row["element_type"] not in PROFILE_VALIDATION:
                raise Exception(f"Subscription file error: {row['element_type']} not a valid element_type."
                                f"Valid element_type are: {list(PROFILE_VALIDATION.keys())}")

            if isinstance(row["property"], str) and row['property'] not in PROFILE_VALIDATION[row["element_type"]]:
                raise Exception(
                    f"Subscription file error: {row['property']} is not valid. "
                    f"Valid subtypes for '{row['element_type']}' are: {PROFILE_VALIDATION[row['element_type']]}")

            valisSet = set(PROFILE_VALIDATION[row['element_type']])
            sSet = set(row["property"])
            if isinstance(row["property"], list) and valisSet.issubset(sSet):
                raise Exception(
                    f"Subscription file error: {row['property']} is not a valid subset. "
                    f"Valid subtypes for '{row['element_type']}' are: {PROFILE_VALIDATION[row['element_type']]}")


            element_id = str(row['element_id'])

            self.subscriptions[row['sub_tag']] = {
                'bus': row['bus'],
                'element_id': element_id,
                'element_type': row['element_type'],
                'property': row['property'],
                'scaler' : row['scaler'],
                'dStates': [self.init_state] * self.n_states,
                'subscription': h.helicsFederateRegisterSubscription(self.PSSEfederate, row['sub_tag'], ""),
            }

            self.logger.info("{} property of element {}.{} at bus {} has subscribed to {}".format(
                row['property'], row['element_type'], row['element_id'], row['bus'], row['sub_tag']
            ))

            if row['bus'] not in self.psse_dict:
                self.psse_dict[row['bus']] = {}
            if row['element_type'] not in self.psse_dict[row['bus']]:
                self.psse_dict[row['bus']][row['element_type']] = {}
            if element_id not in self.psse_dict[row['bus']][row['element_type']]:
                self.psse_dict[row['bus']][row['element_type']][element_id] = {}
            if isinstance(row["property"], str):
                if row['property'] not in self.psse_dict[row['bus']][row['element_type']][element_id]:
                    self.psse_dict[row['bus']][row['element_type']][element_id][row['property']] = 0
            elif isinstance(row["property"], list):
                for r in row['property']:
                    if r not in self.psse_dict[row['bus']][row['element_type']][element_id]:
                        self.psse_dict[row['bus']][row['element_type']][element_id][r] = 0

        return

    def request_time(self, t):
        r_seconds = self.sim.GetTotalSeconds()  # - self._dss_solver.GetStepResolutionSeconds()
        if not self.settings['HELICS']['Iterative Mode']:
            while self.c_seconds < r_seconds:
                self.c_seconds = h.helicsFederateRequestTime(self.PSSEfederate, r_seconds)
            self.logger.info('Time requested: {} - time granted: {} '.format(r_seconds, self.c_seconds))
            return True, self.c_seconds
        else:
            error = max([abs(x["dStates"][0] - x["dStates"][1]) for k, x in self.subscriptions.items()])
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

    def get_restructured_results(self, results):
        results_dict = {}
        for k, d in results.items():
            c, p = k.split("_")
            if c not in results_dict:
                results_dict[c] = {}
            for n, v in d.items():
                if isinstance(n, str):
                    n = n.replace(" ", "")
                if n not in results_dict[c]:
                    results_dict[c][n] = {p:v}
        return results_dict

    def publish(self):
        for quantities, subsystem_buses in self.pub_struc:
            temp_res = self.sim.read_subsystems(quantities, subsystem_buses)
            temp_res = self.get_restructured_results(temp_res)
            print(temp_res)
            for cName, elmInfo in temp_res.items():
                for Name, vInfo in elmInfo.items():
                    for pName, val in vInfo.items():
                        pub_tag = "{}.{}.{}.{}".format(self.settings["HELICS"]['Federate name'], cName, Name, pName)
                        pub = self.publications[pub_tag]
                        dtype_matched = True
                        if isinstance(val, float):
                            h.helicsPublicationPublishDouble(pub, val)
                        elif isinstance(val, complex):
                            h.helicsPublicationPublishComplex(pub, val.real, val.imag)
                        elif isinstance(val, int):
                            h.helicsPublicationPublishInteger(pub, val)
                        elif isinstance(val, list):
                            h.helicsPublicationPublishVector(pub, val)
                        elif isinstance(val, str):
                            h.helicsPublicationPublishString(pub, val)
                        else:
                            dtype_matched = False
                            self.logger.warning(f"Publication {pub_tag} not updated")
                        if dtype_matched:
                            self.logger.debug(f"Publication {pub_tag} published: {val}")
        return

    def subscribe(self):
        for sub_tag, sub_data in self.subscriptions.items():
            if isinstance(sub_data["property"], str):
                sub_data['value'] = h.helicsInputGetDouble(sub_data['subscription'])
                self.psse_dict[sub_data['bus']][sub_data['element_type']][sub_data['element_id']][sub_data["property"]] = sub_data['value']
            elif isinstance(sub_data["property"], list):
                sub_data['value'] = h.helicsInputGetVector(sub_data['subscription'])
                print(sub_data['value'] )
                if isinstance(sub_data['value'], list) and len(sub_data['value']) == len(sub_data["property"]):
                    for i, p in enumerate(sub_data["property"]):
                        self.psse_dict[sub_data['bus']][sub_data['element_type']][sub_data['element_id']][p] = sub_data['value'][i]


            self.logger.debug('Data received {} for tag {}'.format(sub_data['value'], sub_tag))
            if self.settings['HELICS']['Iterative Mode']:
                if self.c_seconds != self.c_seconds_old:
                    sub_data['dStates'] = [self.init_state] * self.n_states
                else:
                    sub_data['dStates'].insert(0, sub_data['dStates'].pop())

        for b, bInfo in self.psse_dict.items():
            for t , tInfo in bInfo.items():
                for i , vDict in tInfo.items():
                    values = {}
                    for p, v in vDict.items():
                        if isinstance(p, str):
                            ppty = f'realar{PROFILE_VALIDATION[t].index(p) + 1}'
                            values[ppty] = v
                        elif isinstance(p, list):
                            for ppt in p:
                                ppty = f'realar{PROFILE_VALIDATION[t].index(ppt) + 1}'
                                values[ppty] = v
                    if sum(values.values()) != 0:
                        self.sim.update_object(t, b, i, values)


        self.c_seconds_old = self.c_seconds
        return self.subscriptions

    def fill_missing_values(self, value):
        idx = [f'realar{PROFILE_VALIDATION[self.dType].index(c) + 1}' for c in self.Columns]
        x = dict(zip(idx, list(value)))
        return x

    def __del__(self):
        h.helicsFederateFinalize(self.PSSEfederate)
        state = h.helicsFederateGetState(self.PSSEfederate)
        h.helicsFederateInfoFree(self.fedinfo)
        h.helicsFederateFree(self.PSSEfederate)
        self.logger.info('HELICS federate for PyDSS destroyed')