from pypsse.modes.constants import dyn_only_options
import pandas as pd
import os

class DynamicUtils:
    
    dynamic_params = ['FmA', 'FmB', 'FmC', 'FmD', 'Fel']
    
    def break_loads(self, loads=None, components_to_replace=["FmD"]):
        components_to_stay = [x for x in self.dynamic_params if x not in components_to_replace]
        if loads is None:
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
            self.logger.info(f"Dynamic model parameters for load {load['id']} at bus 'XX' changed.")

    def _get_load_dynamic_properties(self, load):
        settings = {}
        for i in range(133):
            irr, con_index = self.PSSE.lmodind(load["bus"], str(load['id']), 'CHARAC', 'CON')
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
                load['bus'], str(load['id']), 
                realar=[total_distribution_load.real, total_distribution_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp='original'
                )   
            #ierr, cmpval = self.PSSE.loddt2(load["bus"], load["id"] ,"MVA" , "ACT")    
            self.logger.info(f"Original load {load['id']} @ bus {load['bus']}: {total_load}")
            self.logger.info(f"New load 'XX' @ bus {load['bus']} created successfully: {total_transmission_load}")
            self.logger.info(f"Load {load['id']} @ bus {load['bus']} updated : {total_distribution_load}")
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
                        "id":  row["element_id"],
                        "bus":  row["bus"],
                    }
                )
        return load
    
    def _get_load_static_data(self, loads):
        values = ["MVA", "IL", "YL", "TOTAL"]
        for load in loads:
            for v in values:
                ierr, cmpval = self.PSSE.loddt2(load["bus"], str(load["id"]) ,v, "ACT")
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