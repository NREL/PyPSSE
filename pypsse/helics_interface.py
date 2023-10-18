from re import I
from pypsse.modes.constants import DYNAMIC_ONLY_PPTY, dyn_only_options
from pypsse.profile_manager.common import PROFILE_VALIDATION
import pandas as pd
import helics as h
import time
import ast
import os

class helics_interface:

    all_sub_results = {}
    all_pub_results = {}
    
    dynamic_iter_const = 1000.0
    n_states = 5
    init_state = 1
    dynamic_params = ['FmA', 'FmB', 'FmC', 'FmD', 'Fel']

    def __init__(self, PSSE, sim, settings, export_settings, bus_subsystems, logger):
        self.bus_pubs = ['bus_id', 'bus_Vmag', 'bus_Vang', 'bus_dev']
        self.PSSE = PSSE
        self.logger = logger
        self.settings = settings
        self.export_settings = export_settings
        self.bus_subsystems = bus_subsystems
        self.sim = sim
        self.c_seconds = 0
        self.c_seconds_old = -1

        if self.settings["Simulation"]["Simulation mode"] in ["Dynamic", "Snap"]:
            self.create_replica_model_for_coupled_loads(['FmD'])
            
        self._co_convergance_error_tolerance = settings['HELICS']['Error tolerance']
        self._co_convergance_max_iterations = settings['HELICS']['Max co-iterations']
        self.create_federate()
        self.subsystem_info = []
        self.publications = {}
        self.subscriptions = {}
       
        return
    
    def create_replica_model_for_coupled_loads(self, components_to_replace):
        components_to_stay = [x for x in self.dynamic_params if x not in components_to_replace]
        loads = self._get_coupled_loads()
        loads = self._get_load_static_data(loads)
        loads = self._get_load_dynamic_data(loads)
        loads = self._replicate_coupled_load(loads, components_to_replace)
        self._update_dynamic_parameters(loads, components_to_stay, components_to_replace)
        return 

    def _update_dynamic_parameters(self, loads, components_to_stay, components_to_replace):
        new_percentages = {}
        for load in loads:
            count = 0
            for comp in components_to_stay:
                count += load[comp]
            for comp in components_to_stay:
                new_percentages[comp] = load[comp] / count
            for comp in components_to_replace:
                new_percentages[comp] = 0.0
            
            settings = self._get_load_dynamic_properties(load)
            #
            for k, v in new_percentages.items():
                idx = dyn_only_options["Loads"]["lmodind"][k]
                settings[idx] =  v
                #self.PSSE.change_ldmod_con(load['bus'], 'XX' ,r"""CMLDBLU2""" ,idx ,v)
            values = list(settings.values())
            self.PSSE.add_load_model(load['bus'], 'XX', 0, 1, r"""CMLDBLU2""", 2, [0,0], ["",""], 133, values)
            self.logger.info(f"Dynamic model parameters for load {load['name']} at bus 'XX' changed.")

    def _get_load_dynamic_properties(self, load):
        settings = {}
        for i in range(133):
            irr, con_index = self.PSSE.lmodind(load["bus"], str(load['name']), 'CHARAC', 'CON')
            if con_index is not None:
                act_con_index = con_index + i
                irr, value = self.PSSE.dsrval('CON', act_con_index)
                settings[i] = value
        return settings

    def _replicate_coupled_load(self, loads, components_to_replace):
        for load in loads:
            dynamic_percentage = (load['FmA'] + load['FmB'] + load['FmC'] + load['FmD'] + load['Fel']) 
            static_percentage = 1.0 - dynamic_percentage
            for comp in components_to_replace:
                static_percentage += load[comp]
            remaining_load = 1 - static_percentage
            total_load = load['MVA'] 
            total_distribution_load = total_load * static_percentage
            total_transmission_load = total_load * remaining_load
            #ceate new load
            self.PSSE.load_data_5(
                load['bus'], "XX", 
                realar=[total_transmission_load.real, total_transmission_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp='replica'
                )
            #ierr, cmpval = self.PSSE.loddt2(load["bus"], "XX" ,"MVA" , "ACT")
            #modify old load     
            self.PSSE.load_data_5(
                load['bus'], str(load['name']), 
                realar=[total_distribution_load.real, total_distribution_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp='original'
                )   
            #ierr, cmpval = self.PSSE.loddt2(load["bus"], load["name"] ,"MVA" , "ACT")    
            self.logger.info(f"Original load {load['name']} @ bus {load['bus']}: {total_load}")
            self.logger.info(f"New load 'XX' @ bus {load['bus']} created successfully: {total_transmission_load}")
            self.logger.info(f"Load {load['name']} @ bus {load['bus']} updated : {total_distribution_load}")
            load["distribution"] = total_distribution_load
            load["transmission"] = total_transmission_load
        return loads

    def _get_coupled_loads(self):
        sub_data = pd.read_csv(
            os.path.join(
                self.settings["Simulation"]["Project Path"], 'Settings', self.settings["HELICS"]["Subscriptions file"]
            )
        )
        load = []
        for ix, row in sub_data.iterrows():
            if row["element_type"] == "Load":
                load.append(
                    {
                        "type":  row["element_type"],
                        "name":  row["element_id"],
                        "bus":  row["bus"],
                    }
                )
        return load
    
    def _get_load_static_data(self, loads):
        values = ["MVA", "IL", "YL", "TOTAL"]
        for load in loads:
            for v in values:
                ierr, cmpval = self.PSSE.loddt2(load["bus"], str(load["name"]) ,v, "ACT")
                load[v] = cmpval
        return loads
       
    def _get_load_dynamic_data(self, loads):
        values = dyn_only_options["Loads"]["lmodind"]
        for load in loads:
            for v, con_ind in values.items():
                ierr = self.PSSE.inilod(load["bus"])
                ierr, ld_id = self.PSSE.nxtlod(load["bus"])
                if ld_id is not None:
                    irr, con_index = self.PSSE.lmodind(load["bus"], ld_id, 'CHARAC', 'CON')
                    if con_index is not None:
                        act_con_index = con_index + con_ind
                        irr, value = self.PSSE.dsrval('CON', act_con_index)
                        load[v] = value
        return loads

    def enter_execution_mode(self):
        itr = 0
        itr_flag = h.helics_iteration_request_iterate_if_needed
        while True:
            itr_status = h.helicsFederateEnterExecutingModeIterative(
                self.PSSEfederate, 
                itr_flag
                ) 
            self.logger.debug(f"--- Iter {itr}: Iteration Status = {itr_status}, Passed Iteration Requestion = {itr_flag}")
            if itr_status == h.helics_iteration_result_next_step:
                break
        
        return

    def create_federate(self):
        self.fedinfo = h.helicsCreateFederateInfo()
        h.helicsFederateInfoSetCoreName(self.fedinfo, self.settings["HELICS"]['Federate name'])
        h.helicsFederateInfoSetCoreTypeFromString(self.fedinfo, self.settings["HELICS"]['Core type'])
        h.helicsFederateInfoSetCoreInitString(self.fedinfo, "--federates=1")
        if self.settings['HELICS']['Broker']:
            h.helicsFederateInfoSetBroker(self.fedinfo, self.settings['HELICS']['Broker'])
        if self.settings['HELICS']['Broker port']:
            h.helicsFederateInfoSetBrokerPort(self.fedinfo, self.settings['HELICS']['Broker port'])

        if self.settings['HELICS']["Iterative Mode"]:
            h.helicsFederateInfoSetTimeProperty(
                self.fedinfo,
                h.helics_property_time_delta,
                self.settings["Simulation"]["Step resolution (sec)"] / self.dynamic_iter_const
            )
        else:
            h.helicsFederateInfoSetTimeProperty(
                self.fedinfo,
                h.helics_property_time_delta,
                self.settings["Simulation"]["Step resolution (sec)"]
            )
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
            print(temp_res)
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
                        print(pub_tag)
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

            try:
                row['property'] = ast.literal_eval(row['property'])
            except:
                pass
            try:
                row['scaler'] = ast.literal_eval(row['scaler'])
            except:
                pass

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
        if self.sim.getTime() not in self.all_sub_results:
            self.all_sub_results[self.sim.getTime()] = {}
            self.all_pub_results[self.sim.getTime()] = {}
        
        if not self.settings['HELICS']['Iterative Mode']:
            while self.c_seconds < r_seconds:
                self.c_seconds = h.helicsFederateRequestTime(self.PSSEfederate, r_seconds)
            self.logger.info('Time requested: {} - time granted: {} '.format(r_seconds, self.c_seconds))
            return True, self.c_seconds
        else:
            itr = 0
            epsilon = 1e-6
            while True:
                
                self.c_seconds, itr_state = h.helicsFederateRequestTimeIterative(
                    self.PSSEfederate,
                    r_seconds,
                    h.helics_iteration_request_iterate_if_needed
                )
                if (itr_state == h.helics_iteration_result_next_step):
                    self.logger.debug("\tIteration complete!")
                    break
                
                error = max([abs(x["dStates"][0] - x["dStates"][1]) for k, x in self.subscriptions.items()])                
                
                subscriptions = self.subscribe() 
                for sub_name, sub_value in subscriptions.items():
                    if sub_name not in self.all_sub_results[self.sim.getTime()]:
                        self.all_sub_results[self.sim.getTime()][sub_name] = []
                    self.all_sub_results[self.sim.getTime()][sub_name].append(sub_value)
             
                self.sim.resolveStep(r_seconds)       
                
                publications = self.publish()
                for pub_name, pub_value in publications.items():
                    if pub_name not in self.all_pub_results[self.sim.getTime()]:
                        self.all_pub_results[self.sim.getTime()][pub_name] = []
                    self.all_pub_results[self.sim.getTime()][pub_name].append(pub_value)
                
                itr += 1
                self.logger.debug(f"\titr = {itr}")
                
                if itr > self.settings['HELICS']['Max co-iterations']:
                    self.c_seconds, itr_state = h.helicsFederateRequestTimeIterative(
                        self.PSSEfederate,
                        r_seconds,
                        h.helics_iteration_request_no_iteration
                    )
                else:
                    pass
                
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
                else:
                    n = str(n)
                if n not in results_dict[c]:
                    results_dict[c][n] = {p:v}
                results_dict[c][n].update({p:v})
        return results_dict

    def publish(self):
        pub_results = {}
        for quantities, subsystem_buses in self.pub_struc:
            temp_res = self.sim.read_subsystems(quantities, subsystem_buses)
            temp_res = self.get_restructured_results(temp_res)
            for cName, elmInfo in temp_res.items():
                for Name, vInfo in elmInfo.items():
                    for pName, val in vInfo.items():
                        pub_tag = "{}.{}.{}.{}".format(self.settings["HELICS"]['Federate name'], cName, Name, pName)
                        pub_tag_reduced = f"{cName}.{Name}.{pName}" 
                        pub = self.publications[pub_tag]
                        dtype_matched = True
                        pub_results[pub_tag_reduced] = val
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
        return pub_results

    def subscribe(self):
        for sub_tag, sub_data in self.subscriptions.items():
            if isinstance(sub_data["property"], str):
                sub_data['value'] = h.helicsInputGetDouble(sub_data['subscription'])
                self.psse_dict[sub_data['bus']][sub_data['element_type']][sub_data['element_id']][sub_data["property"]] = (sub_data['value'], sub_data['scaler'])
            elif isinstance(sub_data["property"], list):
                sub_data['value'] = h.helicsInputGetVector(sub_data['subscription'])
                if isinstance(sub_data['value'], list) and len(sub_data['value']) == len(sub_data["property"]):
                    for i, p in enumerate(sub_data["property"]):
                        self.psse_dict[sub_data['bus']][sub_data['element_type']][sub_data['element_id']][p] = (sub_data['value'][i], sub_data['scaler'][i])

            self.logger.debug('Data received {} for tag {}'.format(sub_data['value'], sub_tag))
            if self.settings['HELICS']['Iterative Mode']:
                if self.c_seconds != self.c_seconds_old:
                    sub_data['dStates'] = [self.init_state] * self.n_states
                else:
                    sub_data['dStates'].insert(0, sub_data['dStates'].pop())
        all_values = {}
        for b, bInfo in self.psse_dict.items():
            for t, tInfo in bInfo.items():
                for i, vDict in tInfo.items():
                    values = {}
                    j = 0
                    for p, v in vDict.items():
                        if isinstance(v, tuple):
                            v , scale = v
                            all_values[f'{t}.{b}.{i}.{p}'] = v
                            if isinstance(p, str):
                                ppty = f'realar{PROFILE_VALIDATION[t].index(p) + 1}'
                                values[ppty] = v * scale
                            elif isinstance(p, list):
                                for alpha, ppt in enumerate(p):
                                    ppty = f'realar{PROFILE_VALIDATION[t].index(ppt) + 1}'
                                    values[ppty] = v * scale
                        j += 1

                    isEmpty = [0 if not vx else 1 for vx in values.values()]
                    if sum(isEmpty) != 0 and sum(values.values()) < 1e6 and sum(values.values()) > -1e6:
                        self.sim.update_object(t, b, i, values)
                        self.logger.debug(f'{t}.{b}.{i} = {values}')
                        
                    else:
                        self.logger.debug('write failed')

        self.c_seconds_old = self.c_seconds
        return all_values

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