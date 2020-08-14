import pandas as pd
import os
class container:
    def __init__(self, settings, export_settings):
        export__list = ['Buses', 'Branches', 'Loads', 'Induction_generators', 'Machines', 'Fixed_shunts',
                        'Switched_shunts', 'Transformers']
        export__dict = export_settings
        self.settings = settings
        self.results = {}
        self.ext = 'csv' if not export__dict["Compress exports"] else 'pkl'

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
        return

    def get_export_variables(self):
        return self.export_vars

    def Update(self, bus_data, line_data):
        for variable_name, bus_dict in bus_data.items():
            if not isinstance(self.results['{}'.format(variable_name)], pd.DataFrame):
                self.results['{}'.format(variable_name)] = pd.DataFrame(bus_data[variable_name], index=[0])
            else:
                self.results['{}'.format(variable_name)] = self.results['{}'.format(variable_name)].append(
                    bus_data[variable_name], ignore_index=True)
        return

    def export_results(self):
        for df_name, df in self.results.items():
            export_path = os.path.join(self.settings["Project Path"], 'Exports', '{}.{}'.format(df_name, self.ext))
            if self.ext == 'csv':
                df.to_csv(export_path)
            else:
                df.to_pickle(export_path)
        return