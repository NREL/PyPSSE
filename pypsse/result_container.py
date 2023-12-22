import pandas as pd

from pypsse.common import EXPORTS_FOLDER, MAPPED_CLASS_NAMES
from pypsse.data_writers.data_writer import DataWriter
from pypsse.enumerations import BulkWriteModes, StreamedWriteModes
from pypsse.models import ExportAssetTypes, ModelTypes, SimulationSettings


class Container:
    "Class defination for the simulation result container"

    BULK_WRITE_MODES = [m.value for m in BulkWriteModes]
    STREAMED_WRITE_MODES = [m.value for m in StreamedWriteModes]

    def __init__(self, settings: SimulationSettings, export_settings: ExportAssetTypes):
        "Sets up the result container object"

        export__list = [m.value for m in ModelTypes]
        self.export_path = settings.simulation.project_path / EXPORTS_FOLDER
        self.export_settings = export_settings
        self.settings = settings
        self.results = {}
        self.export_vars = {}
        for class_name in export__list:
            mapped_name = MAPPED_CLASS_NAMES[class_name.lower()]
            variables = getattr(export_settings, class_name.lower())
            if variables:
                for variable in variables:
                    self.results[f"{mapped_name}_{variable.value}"] = None
                    if mapped_name not in self.export_vars:
                        self.export_vars[mapped_name] = []
                    self.export_vars[mapped_name].append(variable.value)

        time_steps = int(
            self.settings.simulation.simulation_time.total_seconds()
            / self.settings.simulation.simulation_step_resolution.total_seconds()
        )
        if self.export_settings.file_format not in self.BULK_WRITE_MODES:
            self.dataWriter = DataWriter(self.export_path, export_settings.file_format.value, time_steps)

    def update_export_variables(self, params):
        """Updates the container with current system state.
        Method is called iteratively to store results as a simulation executes"""

        export__list = [m.value for m in ModelTypes]
        self.results = {}
        self.export_vars = {}

        class_assets = ExportAssetTypes(**params) if params else self.export_settings

        for class_name in export__list:
            if class_name in params:
                mapped_name = MAPPED_CLASS_NAMES[class_name]
                variables = getattr(class_assets, class_name)
                if variables:
                    for variable in variables:
                        self.results[f"{mapped_name}_{variable.value}"] = None
                        if mapped_name not in self.export_vars:
                            self.export_vars[mapped_name] = []
                        self.export_vars[mapped_name].append(variable.value)

        return self.export_vars

    def get_export_variables(self):
        "Queries and return results from the current timestep"
        return self.export_vars

    def update(self, bus_data, _, time, has_converged):
        "Updates the results cotainer"
        if self.export_settings.file_format not in self.BULK_WRITE_MODES:
            self.dataWriter.write(time, bus_data, has_converged)
        else:
            for variable_name, _ in bus_data.items():
                if not isinstance(self.results[f"{variable_name}"], pd.DataFrame):
                    self.results[f"{variable_name}"] = pd.DataFrame(bus_data[variable_name], index=[0])
                else:
                    df1 = self.results[f"{variable_name}"]
                    df2 = pd.DataFrame.from_dict([bus_data[variable_name]])
                    concatenated = pd.concat([df1, df2])
                    self.results[f"{variable_name}"] = concatenated

    def export_results(self):
        "Exports all results stored to an external file."
        if self.export_settings.file_format in self.BULK_WRITE_MODES:
            for df_name, df in self.results.items():
                export_path = (
                    self.settings.simulation.project_path
                    / EXPORTS_FOLDER
                    / f'{df_name}.{self.export_settings["Write format"]}'
                )
                if self.export_settings.file_format == BulkWriteModes.CSV:
                    if isinstance(df, pd.DataFrame):
                        df.to_csv(export_path)
                elif self.export_settings.file_format == BulkWriteModes.PKL:
                    df.to_pickle(export_path)
