# Standard libraries
# from common import dtype_MAPPING
import os

import numpy as np
import pandas as pd


class CSVWriter:
    """Class that handles writing simulation results to arrow
    files.
    """

    def __init__(self, log_dir, column_length):
        """Constructor"""
        self.column_length = column_length
        self.log_dir = log_dir
        self.timestamps = []
        self.chunkRows = 1
        self.dfs = {}
        self.step = 0
        # Create arrow writer for each object type

    def write(self, currenttime, powerflow_output):
        """
        Writes the status of BES assets at a particular timestep to an
            arrow file.

        :param fed_name: name of BES federate
        :param log_fields: list of objects to log
        :param currenttime: simulation timestep
        :param powerflow_output: Powerflow solver timestep output as a dict
        """
        # Iterate through each object type
        self.timestamps.append(currenttime)
        for obj_type in powerflow_output:
            data = powerflow_output[obj_type]
            if obj_type not in self.dfs:
                self.dfs[obj_type] = [data]
            else:
                if self.dfs[obj_type] is None:
                    self.dfs[obj_type] = [data]
                else:
                    self.dfs[obj_type].append(data)

            if self.step % self.chunkRows == self.chunkRows - 1:
                fpath = os.path.join(self.log_dir, f"{obj_type}.csv")
                self.dfs[obj_type] = pd.DataFrame(self.dfs[obj_type], index=self.timestamps)
                self.dfs[obj_type].to_csv(fpath, mode="a")

                self.dfs[obj_type] = None
            self.Timestamp[self.step - 1] = np.string_(str(currenttime))
        self.step += 1
