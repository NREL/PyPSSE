from pypsse.data_writers.csv import CSVWriter
from pypsse.data_writers.hdf5 import HDF5Writer
from pypsse.data_writers.json import JSONWriter


class DummyWriter:
    def __init__(self, *_, **__):
        return

    def write(self, *_, **__):
        return


class DataWriter:
    "Data writer class defination"
    modes = {
        "h5": HDF5Writer,
        "csv": CSVWriter,
        "json": JSONWriter,
        "none": DummyWriter,
    }

    def __init__(self, log_dir, formatnm, column_length):
        "Sets up a data writer as per user input"
        self.writer = self.modes[formatnm](log_dir, column_length)

    def write(self, currenttime, powerflow_output, convergence):
        "Enables incremental write to the data writer object"
        self.writer.write(currenttime, powerflow_output, convergence)

    def close_store(self):
        pass