# Standard libraries
# from common import dtype_MAPPING
import json
import os
from datetime import datetime
from pathlib import Path

from loguru import logger


class JSONWriter:
    """Class that handles writing simulation results to json
    files.
    """

    def __init__(self, log_dir: Path, column_length: int):
        """Constructor for json writer

        Args:
            log_dir (Path): output path (dirctory)
            column_length (int): number of data columns
        """
        self.column_length = column_length
        self.log_dir = log_dir
        self.chunk_rows = 1
        self.handles = {}
        self.dfs = {}
        self.step = 0
        # Create arrow writer for each object type

    def write(self, currenttime: datetime, powerflow_output: dict):
        """Writes the status of assets at a particular timestep to a json file.

        Args:
            currenttime (datetime): simulator time step
            powerflow_output (dict): simulation results
        """
        # Iterate through each object type

        for obj_type in powerflow_output:
            fpath = os.path.join(self.log_dir, f"{obj_type}.json")
            if self.step == 0:
                f = open(fpath, "w")
                f.close()
                self.handles[obj_type] = open(fpath, "a")
            data = powerflow_output[obj_type]
            if obj_type not in self.dfs:
                self.dfs[obj_type] = {str(currenttime): data}
            else:
                if self.dfs[obj_type] is None:
                    self.dfs[obj_type] = {str(currenttime): data}
                else:
                    self.dfs[obj_type][currenttime] = data
            if self.step % self.chunk_rows == self.chunk_rows - 1:
                try:
                    json.dump(self.dfs[obj_type], self.handles[obj_type], indent=4)
                    self.handles[obj_type].flush()
                    self.dfs[obj_type] = None
                except Exception as E:
                    logger.warning(f"Unable to write property {obj_type} to file: {E!s}")

        self.step += 1
