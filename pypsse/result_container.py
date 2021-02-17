from pypsse.DataWriters.DataWriter import DataWriter
import pandas as pd
import os
class container:

    BULK_WRITE_MODES = ["csv", "pkl"]
    STREAMED_WRITE_MODES = ["h5"]
    def __init__(self, settings, export_settings):
        export__list = ['Buses', 'Branches', 'Loads', 'Induction_generators', 'Machines', 'Fixed_shunts',
                        'Switched_shunts', 'Transformers',"Areas", "Zones", "DCtransmissionlines", "Stations"]
        export__dict = export_settings
        self.export_path = os.path.join(settings["Simulation"]["Project Path"], 'Exports')
        self.export_settings = export_settings
        self.settings = settings
        self.results = {}
        self.export_vars = {}
        for class_name in export__list:
            variable_dict = export_settings[class_name]
            if isinstance(variable_dict, dict):
                for variable_name, is_exporting in variable_dict.items():
                    if is_exporting:
                        self.results['{}_{}'.format(class_name, variable_name)] = None
                        if class_name not in self.export_vars:
                            self.export_vars[class_name] = []
                        self.export_vars[class_name].append(variable_name)

        timeSteps = int(self.settings["Simulation"]["Simulation time (sec)"] /
                        self.settings["Simulation"]["Step resolution (sec)"])
        if self.export_settings["Write format"] not in self.BULK_WRITE_MODES:
            self.dataWriter = DataWriter(self.export_path, export_settings["Write format"], timeSteps)
        return

    def update_export_variables(self, params):
        export__list = ['Buses', 'Branches', 'Loads', 'Induction_generators', 'Machines', 'Fixed_shunts',
                        'Switched_shunts', 'Transformers', "Areas", "Zones", "DCtransmissionlines", "Stations"]
        self.results = {}
        self.export_vars = {}
        for class_name in export__list:
            if class_name in params:
                variable_dict = params[class_name]
                if isinstance(variable_dict, dict):
                    for variable_name, is_exporting in variable_dict.items():
                        if is_exporting:
                            self.results['{}_{}'.format(class_name, variable_name)] = None
                            if class_name not in self.export_vars:
                                self.export_vars[class_name] = []
                            self.export_vars[class_name].append(variable_name)
        return self.export_vars

    def get_export_variables(self):
        return self.export_vars

    def Update(self, bus_data, line_data, index, time):
        if self.export_settings["Write format"] not in self.BULK_WRITE_MODES:
            self.dataWriter.write(self.settings["HELICS"]["Federate name"], time, bus_data, index)
        else:
            for variable_name, bus_dict in bus_data.items():
                if not isinstance(self.results['{}'.format(variable_name)], pd.DataFrame):
                    self.results['{}'.format(variable_name)] = pd.DataFrame(bus_data[variable_name], index=[0])
                else:
                    self.results['{}'.format(variable_name)] = self.results['{}'.format(variable_name)].append(
                        bus_data[variable_name], ignore_index=True)
        return

    def export_results(self):
        if self.export_settings["Write format"] in self.BULK_WRITE_MODES:
            for df_name, df in self.results.items():
                export_path = os.path.join(
                    self.settings["Simulation"]["Project Path"],
                    'Exports',
                    '{}.{}'.format(df_name, self.export_settings["Write format"])
                )
                if self.export_settings["Write format"] == 'csv':
                    df.to_csv(export_path)
                elif self.export_settings["Write format"] == "pkl":
                    df.to_pickle(export_path)
        return