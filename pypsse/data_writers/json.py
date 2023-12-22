# Standard libraries
# from common import dtype_MAPPING
import json
import logging
import os

logger = logging.getLogger("pyPSSE")


class JSONWriter:
    """Class that handles writing simulation results to arrow
    files.
    """

    def __init__(self, log_dir, column_length):
        """Constructor"""
        self.column_length = column_length
        self.log_dir = log_dir
        self.chunk_rows = 1
        self.handles = {}
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
