# Standard libraries
# from common import dtype_MAPPING
import logging
import os

import h5py
import numpy as np
import pandas as pd

from pypsse.common import DEFAULT_RESULTS_FILENAME


class HDF5Writer:
    """Class that handles writing simulation results to hdf5 files."""

    def __init__(self, log_dir, column_length):
        """Constructor"""
        self.log_dir = log_dir
        self.store = h5py.File(os.path.join(log_dir, DEFAULT_RESULTS_FILENAME), "w")
        self.store_groups = {}
        self.store_datasets = {}
        self.row = {}
        self.column_length = column_length

        self.chunkRows = 1
        self.step = 0
        self.dfs = {}
        self.convergence = self.store.create_dataset(
            "Convergence",
            shape=(self.column_length,),
            maxshape=(None,),
            chunks=True,
            compression="gzip",
            compression_opts=4,
            shuffle=True,
            dtype=np.int16,
        )
        self.Timestamp = self.store.create_dataset(
            "Time stamp",
            shape=(self.column_length,),
            maxshape=(None,),
            chunks=True,
            compression="gzip",
            compression_opts=4,
            shuffle=True,
            dtype="S30",
        )
        # Create arrow writer for each object type

    def write(self, currenttime, powerflow_output, convergence):
        """
        Writes the status of BES assets at a particular timestep to an
            arrow file.

        :param currenttime: simulation timestep
        :param powerflow_output: Powerflow solver timestep output as a dict
        """
        # Iterate through each object type
        for obj_type in powerflow_output:
            data = pd.DataFrame(powerflow_output[obj_type], index=[self.step])
            data = data.fillna(0)

            if obj_type not in self.row:
                self.row[obj_type] = 0
                self.store_groups[obj_type] = self.store.create_group(obj_type)
                self.store_datasets[obj_type] = {}
                for col_name in powerflow_output[obj_type].keys():
                    dtype = data[col_name].dtype
                    if dtype == object:
                        dtype = "S30"

                    self.store_datasets[obj_type][col_name] = self.store_groups[obj_type].create_dataset(
                        str(col_name),
                        shape=(self.column_length,),
                        maxshape=(None,),
                        chunks=True,
                        compression="gzip",
                        compression_opts=4,
                        shuffle=True,
                        dtype=dtype,
                    )

            if obj_type not in self.dfs:
                self.dfs[obj_type] = data
            else:
                if self.dfs[obj_type] is None:
                    self.dfs[obj_type] = data
                else:
                    self.dfs[obj_type] = self.dfs[obj_type].append(data, ignore_index=True)

            if self.step % self.chunkRows == self.chunkRows - 1:
                si = int(self.step / self.chunkRows) * self.chunkRows
                ei = si + self.chunkRows
                for col_name in powerflow_output[obj_type].keys():
                    r = self.store_datasets[obj_type][col_name].shape[0]
                    if ei >= r:
                        self.store_datasets[obj_type][col_name].resize((ei,))
                    self.store_datasets[obj_type][col_name][si:ei] = self.dfs[obj_type][col_name]
                self.dfs[obj_type] = None
            if self.step >= len(self.Timestamp):
                self.Timestamp.resize((len(self.Timestamp) + 1,))
                self.convergence.resize((len(self.convergence) + 1,))
            self.Timestamp[self.step - 1] = np.string_(str(currenttime))
            self.convergence[self.step - 1] = convergence
            # Add object status data to a DataFrame
            self.store.flush()
        self.step += 1

    def __del__(self):
        try:
            k = next(self.dfs.keys())
            length = len(self.dfs[k])
            if self.dfs[k] is not None:
                for obj_type in self.dfs.keys():
                    for col_name in self.dfs[k].columns:
                        self.store_datasets[obj_type][col_name][self.column_length - length :] = self.dfs[obj_type][
                            col_name
                        ]

            self.store.flush()
            self.store.close()
        except Exception as e:
            logging.info(str(e))
