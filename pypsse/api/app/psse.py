# Standard imports
from pypsse.pypsse_instance import pyPSSE_instance
from multiprocessing import current_process
from aiohttp import web, WSMsgType
from queue import Empty
import logging
import inspect
import json
import yaml
import sys
import os

logger = logging.getLogger(__name__)
# Make sure to change the PSSE path 
PSSE_PATH = r"C:\Program Files (x86)\PTI\PSSE34\PSSPY37"

dynamic_params = ['FmA', 'FmB', 'FmC', 'FmD', 'Fel']

class PSSE:
    def __init__(self, shutdown_event=None, to_psse_queue=None, from_psse_queue=None, params=None):
        super().__init__()
        self.uuid = current_process().name
        logger.info(f"{self.uuid} - psse uuid init time")
        self.shutdownevent = shutdown_event
        self.to_psse_queue = to_psse_queue
        self.from_psse_queue = from_psse_queue
        self.psse_obj = pyPSSE_instance(settinigs_toml_path=params["filename"])
        if self.psse_obj.initSucess:
            logger.info("{} - psse dispatched".format(self.uuid))
            result = {
                "Status": "Success",
                "Message": "PSSE {} successfully initiallized.".format(self.uuid),
                "UUID": self.uuid
            }
            if from_psse_queue !=None: self.from_psse_queue.put(result)
            self.run()
        else:
            msg = f"Error launching PSSE"
            logger.error(msg)
    
    def run(self):
        logger.info("{} - PSSE simulation starting")
        while not self.shutdownevent.is_set():
            try:
                task = self.to_psse_queue.get()
                if task == 'END':
                    break
                else:
                    try:
                        task = json.loads(task)
                    except Exception as e:
                        msg = f"Error parsing the inputs as dictionary: " \
                            f"{str(e)} > input: {task}"
                        result = {"Status": "Failed", "Message": msg}
                        logger.error(msg)
                        self.from_psse_queue.put(result)
                        continue
                    if "command" not in task:
                        result = {"Status": "Failed",
                                  "Message": f"Valid command not provided"}
                    elif "parameters" not in task:
                        result = {"Status": "Failed",
                                  "Message": f"Valid parameters not provided"}
                    else:
                        command = task["command"]
                        parameters = task["parameters"]
                        if hasattr(self,command):
                            args = inspect.getfullargspec(eval("self.{}".format(command)))[0][1:]
                            if set(args).issubset(parameters.keys()):
                                command_str = ''
                                for arg in args:
                                    parameter = parameters[arg]
                                    if isinstance(parameter,str):
                                        parameter="r\"{}\"".format(parameter)
                                    command_str += f"{arg}={parameter},"
                                command_str = f"self.{command}({command_str[:-1]})"
                                command_return = eval(command_str)
                                result = {"Status":"Success","Data":command_return}
                            else:
                                result = {"Status":"Failed","Message":f"Wrong arguments passed to {command}"}
                        else:
                            result = {"Status":"Failed","Message":f"Command {command} does not exist."}
                self.from_psse_queue.put(result)
            except Empty:
                continue
            except (KeyboardInterrupt, SystemExit):
                break
        logger.info(f"{self.uuid} - finishing PSSE simulation")
        msg = f'Closed PSSE instance'
        result = {"Status": "Success", "Message": msg, "UUID": self.uuid}
        logger.info(msg)
        self.from_psse_queue.put(result)

    def init(self):
        self.time_counter = 0
        self.psse_obj.init()

    def update_settings(self, new_dict: dict):
        for key, value in new_dict.items():
            if key in self.psse_obj.settings:
                self.psse_obj.settings[key].update(value)
            else:
                logger.warning(f"{key} not present in settings.toml file")

    def get_results(self, params):
        # print("\n\nGetting results\n\n")
        # params = {
        #     "Loads": {
        #         "id_fields": ["MVA"]
        #     },
        #     "Buses": {
        #         "id_fields": ["PU", "ANGLE"]
        #     },
        # }
        settings = {}
        for k, v in params.items():
            settings[k] = {}
            ppties = params[k]["id_fields"]
            for p in ppties:
                settings[k][p] = True
        results = self.psse_obj.get_results(settings)
        # TODO: KAPIL you will return the results
        return results


    def solve_step(self):
        self.current_result = self.psse_obj.step(self.time_counter)
        self.time_counter += self.psse_obj.settings['Simulation']["Step resolution (sec)"]
        return self.current_result

    def export_result(self):
        self.psse_obj.PSSE.pssehalt_2()
        if not self.psse_obj.export_settings["Export results using channels"]:
            self.psse_obj.results.export_results()
        else:
            self.psse_obj.sim.export()
    
    def ingest_subscription(self, key_obj: dict, bes_asset_id: list, value):
        if key_obj['asset_type'] == 'bus':
            if key_obj['parameter_name'] == "power_real":
                self.psse_obj.load_chng_5(ibus = bes_asset_id[0], id= bes_asset_id[1],
                realar1=value)
            if key_obj['parameter_name'] == "power_imag":
                self.psse_obj.load_chng_5(ibus = bes_asset_id[0], id= bes_asset_id[1],
                realar2=value)

    def query_param(self, key_obj: dict ={}):
        rval = False
        if  key_obj['asset_type'] == 'bus':
            if  key_obj['parameter_name'] == 'voltage' and key_obj['parameter_unit'] == 'pu':
                rval = self.current_result['Buses_PU'].get(key_obj['asset_name'])
            elif key_obj['parameter_name'] == 'voltage_angle' and key_obj['parameter_unit'] == 'deg':
                rval = self.current_result['Buses_ANGLED'].get(key_obj['asset_name'])
            if key_obj['parameter_name'] == 'power_mismatch' and key_obj['parameter_unit'] == 'mw':
                rval = self.current_result['Buses_MISMATCH'].get(key_obj['asset_name'])
        logger.info(f"Query return value is {rval} for {key_obj['parameter_name']}")
        if rval is None:
            return False
        else:
            return rval
        

    def close_case(self):
        self.psse_obj.PSSE.pssehalt_2()
        del self.psse_obj
        logger.info(f'PSSE case {self.uuid} closed.')

    
    

    def break_load_models(self, components_to_replace=['FmD']):
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

            values = list(settings.values())
            self.psse_obj.add_load_model(load['bus'], 'XX', 0, 1, r"""CMLDBLU2""", 2, [0,0], ["",""], 133, values)
            logger.info(f"Dynamic model parameters for load {load['name']} at bus 'XX' changed.")

    def _get_load_dynamic_properties(self, load):
        settings = {}
        for i in range(133):
            irr, con_index = self.psse_obj.lmodind(load["bus"], load['name'], 'CHARAC', 'CON')
            if con_index is not None:
                act_con_index = con_index + i
                irr, value = self.psse_obj.dsrval('CON', act_con_index)
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
            self.psse_obj.load_data_5(
                load['bus'], "XX", 
                realar=[total_transmission_load.real, total_transmission_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp='replica'
                )
            #modify old load     
            self.psse_obj.load_data_5(
                load['bus'], load['name'], 
                realar=[total_distribution_load.real, total_distribution_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp='original'
                )      
            logger.info(f"Original load {load['name']} @ bus {load['bus']}: {total_load}")
            logger.info(f"New load 'XX' @ bus {load['bus']} created successfully: {total_transmission_load}")
            logger.info(f"Load {load['name']} @ bus {load['bus']} updated : {total_distribution_load}")
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
                ierr, cmpval = self.psse_obj.loddt2(load["bus"], load["name"] ,v, "ACT")
                load[v] = cmpval
        return loads
       
    def _get_load_dynamic_data(self, loads):
        values = dyn_only_options["Loads"]["lmodind"]
        for load in loads:
            for v, con_ind in values.items():
                ierr = self.psse_obj.inilod(load["bus"])
                ierr, ld_id = self.psse_obj.nxtlod(load["bus"])
                if ld_id is not None:
                    irr, con_index = self.psse_obj.lmodind(load["bus"], ld_id, 'CHARAC', 'CON')
                    if con_index is not None:
                        act_con_index = con_index + con_ind
                        irr, value = self.psse_obj.dsrval('CON', act_con_index)
                        load[v] = value
        return loads
    
    
    
    
if __name__ == '__main__':

    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.basicConfig(level=logger.INFO, format=FORMAT)

    a = PSSE()
    del a
