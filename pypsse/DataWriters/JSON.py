# -*- coding: utf-8 -*-
# Standard libraries
#from common import DTYPE_MAPPING
import pandas as pd
import numpy as np
import logging
import json
import os

logger = logging.getLogger('pyPSSE')

class jsonWriter:
    """ Class that handles writing simulation results to arrow
        files.
    """

    def __init__(self, log_dir, columnLength):
        """ Constructor """
        self.columnLength = columnLength
        self.log_dir = log_dir 
        self.chunkRows = 1
        self.handles = {}
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
        
        
        for obj_type in powerflow_output:
            fpath = os.path.join(self.log_dir, f'{obj_type}.json')
            if self.step == 0:
                f = open(fpath, "w")
                f.close()
                self.handles[obj_type] =  open(fpath, "a")
            Data = powerflow_output[obj_type]
            if obj_type not in self.dfs:
                self.dfs[obj_type] = {str(currenttime): Data}
            else:
                if self.dfs[obj_type] is None:
                    self.dfs[obj_type] = {str(currenttime): Data}
                else:
                    self.dfs[obj_type][currenttime] = Data
            if self.step % self.chunkRows == self.chunkRows - 1:
                try:
                    json.dump(self.dfs[obj_type], self.handles[obj_type], indent=4)
                    self.handles[obj_type].flush()
                    self.dfs[obj_type] = None
                except Exception as E:
                    logger.warning(f"Unable to write property {obj_type} to file: {str(E)}" )

                
        self.step += 1

