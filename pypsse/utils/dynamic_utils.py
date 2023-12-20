import os
from typing import ClassVar, List

import pandas as pd

from pypsse.common import MACHINE_CHANNELS
from pypsse.modes.constants import dyn_only_options


class DynamicUtils:
    "Utility functions for dynamic simulations"

    dynamic_params: ClassVar[List[str]] = ["FmA", "FmB", "FmC", "FmD", "Fel"]

    def disable_generation_for_coupled_buses(self):
        "Disables generation of coupled buses (co-simulation mode only)"
        if (
            self.settings.helics
            and self.settings.helics.cosimulation_mode
            and self.settings.helics.disable_generation_on_coupled_buses
        ):
            sub_data = pd.read_csv(self.settings.simulation.subscriptions_file)
            sub_data = sub_data[sub_data["element_type"] == "Load"]
            generators = {}
            generator_list = {}

            for gen_bus, gen_id in self.raw_data.generators:
                if gen_bus not in generator_list:
                    generator_list[gen_bus] = []
                generator_list[gen_bus].append(gen_id)

            for _, row in sub_data.iterrows():
                bus = row["bus"]
                generators[bus] = generator_list[bus]

            for bus_id, machines in generators.items():
                for machine in machines:
                    intgar = [0, self._i, self._i, self._i, self._i, self._i]
                    realar = [
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                        self._f,
                    ]
                    self.psse.machine_chng_2(bus_id, machine, intgar, realar)
                    self.logger.info(f"Machine disabled: {bus_id}_{machine}")

    def disable_load_models_for_coupled_buses(self):
        "Disables loads of coupled buses (co-simulation mode only)"
        if self.settings.helics and self.settings.helics.cosimulation_mode:
            sub_data = pd.read_csv(self.settings.simulation.subscriptions_file)
            sub_data = sub_data[sub_data["element_type"] == "Load"]

            self.psse_dict = {}
            for _, row in sub_data.iterrows():
                bus = row["bus"]
                load = row["element_id"]
                ierr = self.psse.ldmod_status(0, int(bus), str(load), 1, 0)
                assert ierr == 0, f"error={ierr}"
                self.logger.error(f"Dynamic model for load {load} connected to bus {bus} has been disabled")

    def break_loads(self, loads=None, components_to_replace: List[str] = []):
        "Implements the load split logic"
        components_to_stay = [x for x in self.dynamic_params if x not in components_to_replace]
        if loads is None:
            loads = self._get_coupled_loads()
        loads = self._get_load_static_data(loads)
        loads = self._get_load_dynamic_data(loads)
        loads = self._replicate_coupled_load(loads, components_to_replace)
        self._update_dynamic_parameters(loads, components_to_stay, components_to_replace)

    def _update_dynamic_parameters(self, loads, components_to_stay, components_to_replace):
        "Updates dynamic parameters of composite load models"
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
                settings[idx] = v
                # self.psse.change_ldmod_con(load['bus'], 'XX' ,r"""CMLDBLU2""" ,idx ,v)
            values = list(settings.values())
            self.psse.add_load_model(load["bus"], "XX", 0, 1, r"""CMLDBLU2""", 2, [0, 0], ["", ""], 133, values)
            self.logger.info(f"Dynamic model parameters for load {load['id']} at bus 'XX' changed.")

    def _get_load_dynamic_properties(self, load):
        "Returns dynamic parameters of composite load models"
        settings = {}
        for i in range(133):
            ierr, con_index = self.psse.lmodind(load["bus"], str(load["id"]), "CHARAC", "CON")
            if con_index is not None:
                act_con_index = con_index + i
                ierr, value = self.psse.dsrval("CON", act_con_index)
                assert ierr == 0, f"error={ierr}"
                settings[i] = value
        return settings

    def _replicate_coupled_load(self, loads, components_to_replace):
        "Create a replica of composite load model"
        for load in loads:
            dynamic_percentage = load["FmA"] + load["FmB"] + load["FmC"] + load["FmD"] + load["Fel"]
            static_percentage = 1.0 - dynamic_percentage
            for comp in components_to_replace:
                static_percentage += load[comp]
            remaining_load = 1 - static_percentage
            total_load = load["MVA"]
            total_distribution_load = total_load * static_percentage
            total_transmission_load = total_load * remaining_load
            # ceate new load
            self.psse.load_data_5(
                load["bus"],
                "XX",
                realar=[total_transmission_load.real, total_transmission_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp="replica",
            )
            # ierr, cmpval = self.psse.loddt2(load["bus"], "XX" ,"MVA" , "ACT")
            # modify old load
            self.psse.load_data_5(
                load["bus"],
                str(load["id"]),
                realar=[total_distribution_load.real, total_distribution_load.imag, 0.0, 0.0, 0.0, 0.0],
                lodtyp="original",
            )
            # ierr, cmpval = self.psse.loddt2(load["bus"], load["id"] ,"MVA" , "ACT")
            self.logger.info(f"Original load {load['id']} @ bus {load['bus']}: {total_load}")
            self.logger.info(f"New load 'XX' @ bus {load['bus']} created successfully: {total_transmission_load}")
            self.logger.info(f"Load {load['id']} @ bus {load['bus']} updated : {total_distribution_load}")
            load["distribution"] = total_distribution_load
            load["transmission"] = total_transmission_load
        return loads

    def _get_coupled_loads(self):
        "Returns a list of all coupled loads ina give simualtion"

        sub_data = pd.read_csv(
            os.path.join(
                self.settings["Simulation"]["Project Path"], "Settings", self.settings["HELICS"]["Subscriptions file"]
            )
        )
        load = []
        for _, row in sub_data.iterrows():
            if row["element_type"] == "Load":
                load.append(
                    {
                        "type": row["element_type"],
                        "id": row["element_id"],
                        "bus": row["bus"],
                    }
                )
        return load

    def _get_load_static_data(self, loads):
        "Returns static data for load models"

        values = ["MVA", "IL", "YL", "TOTAL"]
        for load in loads:
            for v in values:
                ierr, cmpval = self.psse.loddt2(load["bus"], str(load["id"]), v, "ACT")
                load[v] = cmpval
        return loads

    def _get_load_dynamic_data(self, loads):
        "Returns dynamic data for load models"
        values = dyn_only_options["Loads"]["lmodind"]
        for load in loads:
            for v, con_ind in values.items():
                ierr = self.psse.inilod(load["bus"])
                assert ierr == 0, f"error={ierr}"
                ierr, ld_id = self.psse.nxtlod(load["bus"])
                assert ierr == 0, f"error={ierr}"
                if ld_id is not None:
                    ierr, con_index = self.psse.lmodind(load["bus"], ld_id, "CHARAC", "CON")
                    assert ierr == 0, f"error={ierr}"
                    if con_index is not None:
                        act_con_index = con_index + con_ind
                        ierr, value = self.psse.dsrval("CON", act_con_index)
                        assert ierr == 0, f"error={ierr}"
                        load[v] = value
        return loads

    def setup_machine_channels(self, machines, properties):
        "Sets up machine channels"
        for _, qty in enumerate(properties):
            if qty not in self.channel_map:
                nqty = f"MACHINE_{qty}"
                self.channel_map[nqty] = {}
            for mch, b in machines:
                if qty in MACHINE_CHANNELS:
                    self.channel_map[nqty][f"{b}_{mch}"] = [self.chnl_idx]
                    chnl_id = MACHINE_CHANNELS[qty]
                    self.logger.info(f"{qty} for machine {b}_{mch} added to channel {self.chnl_idx}")
                    self.psse.machine_array_channel([self.chnl_idx, chnl_id, int(b)], mch, "")
                    self.chnl_idx += 1

    def setup_load_channels(self, loads):
        "Sets up load channels"

        if "LOAD_P" not in self.channel_map:
            self.channel_map["LOAD_P"] = {}
            self.channel_map["LOAD_Q"] = {}

        for ld, b in loads:
            self.channel_map["LOAD_P"][f"{b}_{ld}"] = [self.chnl_idx]
            self.channel_map["LOAD_Q"][f"{b}_{ld}"] = [self.chnl_idx + 1]
            self.psse.load_array_channel([self.chnl_idx, 1, int(b)], ld, "")
            self.psse.load_array_channel([self.chnl_idx + 1, 2, int(b)], ld, "")
            self.logger.info(f"P and Q for load {b}_{ld} added to channel {self.chnl_idx} and {self.chnl_idx + 1}")
            self.chnl_idx += 2

    def setup_bus_channels(self, buses, properties):
        "Sets up bus channels"

        for _, qty in enumerate(properties):
            if qty not in self.channel_map:
                self.channel_map[qty] = {}
            for _, b in enumerate(buses):
                if qty == "frequency":
                    self.channel_map[qty][b] = [self.chnl_idx]
                    self.psse.bus_frequency_channel([self.chnl_idx, int(b)], "")
                    self.logger.info(f"Frequency for bus {b} added to channel { self.chnl_idx}")
                    self.chnl_idx += 1
                elif qty == "voltage_and_angle":
                    self.channel_map[qty][b] = [self.chnl_idx, self.chnl_idx + 1]
                    self.psse.voltage_and_angle_channel([self.chnl_idx, -1, -1, int(b)], "")
                    self.logger.info(
                        f"Voltage and angle for bus {b} added to channel {self.chnl_idx} and {self.chnl_idx+1}"
                    )
                    self.chnl_idx += 2

    def poll_channels(self):
        "Polls all channels adde during the setup process"

        results = {}
        for ppty, b_dict in self.channel_map.items():
            ppty_new = ppty.split("_and_")
            for b, indices in b_dict.items():
                for n, idx in zip(ppty_new, indices):
                    if "_" not in n:
                        n_name = f"BUS_{n}"
                    else:
                        n_name = n
                    if n_name not in results:
                        results[n_name] = {}
                    ierr, value = self.psse.chnval(idx)
                    assert ierr == 0, f"error={ierr}"
                    if value is None:
                        value = -1
                    results[n_name][b] = value
        return results

    def setup_all_channels(self):
        "Sets up all user-defined channels for a project"

        self.channel_map = {}
        self.chnl_idx = 1
        if not self.export_settings.channel_setup:
            return

        for channel in self.export_settings.channel_setup:
            method_type = channel.asset_type
            if method_type == "buses":
                self.setup_bus_channels(channel.asset_list, channel.asset_properties)
            elif method_type == "loads":
                load_list = [[x, int(y)] for x, y in channel.asset_list]
                self.setup_load_channels(load_list)
            elif method_type == "machines":
                machine_list = [[x, int(y)] for x, y in channel.asset_list]
                self.setup_machine_channels(machine_list, channel.asset_properties)
