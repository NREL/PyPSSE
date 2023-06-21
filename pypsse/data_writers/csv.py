# -*- coding: utf-8 -*-
# Standard libraries
#from common import DTYPE_MAPPING
import pandas as pd
import numpy as np
import os

class csvWriter:
    """ Class that handles writing simulation results to arrow
        files.
    """

    def __init__(self, log_dir, columnLength):
        """ Constructor """
        self.columnLength = columnLength
        self.log_dir = log_dir 
        self.timestamps = []
        self.chunkRows = 1
        self.dfs = {}
        self.step = 0
        # Create arrow writer for each object type

    def write(self, fed_name, currenttime, powerflow_output, index):
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
            Data = powerflow_output[obj_type]
            if obj_type not in self.dfs:
                self.dfs[obj_type] = [Data]
            else:
                if self.dfs[obj_type] is None:
                    self.dfs[obj_type] = [Data]
                else:
                    self.dfs[obj_type].append(Data)

            if self.step % self.chunkRows == self.chunkRows - 1:
                fpath = os.path.join(self.log_dir, f'{obj_type}.csv')
                self.dfs[obj_type] =  pd.DataFrame(self.dfs[obj_type], index=self.timestamps)
                self.dfs[obj_type].to_csv(fpath, mode='a')
                
                self.dfs[obj_type] = None
            self.Timestamp[self.step-1] = np.string_(str(currenttime))
        self.step += 1

