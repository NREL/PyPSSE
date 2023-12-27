# Standard libraries
# from common import dtype_MAPPING
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


class CSVWriter:
    """Class that handles writing simulation results to csv
    files.
    """

    def __init__(self, log_dir: Path, column_length: int):
        """Constructor for csv writer

        Args:
            log_dir (Path): output path (dirctory)
            column_length (int): number of data columns
        """

        self.column_length = column_length
        self.log_dir = log_dir
        self.timestamps = []
        self.chunkRows = 1
        self.dfs = {}
        self.step = 0
        # Create arrow writer for each object type

    def write(self, currenttime: datetime, powerflow_output: dict):
        """Writes the status of assets at a particular timestep to a csv file.

        Args:
            currenttime (datetime): simulator time step
            powerflow_output (dict): simulation results
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
