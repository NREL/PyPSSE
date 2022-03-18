from pypsse.DataWriters.HDF5 import hdf5Writer
from pypsse.DataWriters.CSV import csvWriter
from pypsse.DataWriters.JSON import jsonWriter


class dummyWriter:
    def __init__(self, log_dir, columnLength):
        return

    def write(self, fed_name, currenttime, powerflow_output, index):
        return

class DataWriter:
    modes = {
        'h5': hdf5Writer,
        'csv': csvWriter,
        'json': jsonWriter,
        'none': dummyWriter,
    }

    def __init__(self, log_dir, formatnm, columnLength):
        self.writer = self.modes[formatnm](log_dir, columnLength)

    def write(self, fed_name, currenttime, powerflow_output, index):
        self.writer.write(fed_name, currenttime, powerflow_output, index)