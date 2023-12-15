from pypsse.data_writers.csv import CSVWriter
from pypsse.data_writers.hdf5 import HDF5Writer
from pypsse.data_writers.json import JSONWriter


class DummyWriter:
    def __init__(self, *_, **__):
        return

    def write(self, *_, **__):
        return


class DataWriter:
    modes = {
        "h5": HDF5Writer,
        "csv": CSVWriter,
        "json": JSONWriter,
        "none": DummyWriter,
    }

    def __init__(self, log_dir, formatnm, column_length):
        self.writer = self.modes[formatnm](log_dir, column_length)

    def write(self, currenttime, powerflow_output):
        self.writer.write(currenttime, powerflow_output)
