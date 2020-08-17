from pypsse.DataWriters.HDF5 import hdf5Writer

class dummyWriter:
    def __init__(self, log_dir, columnLength):
        return

    def write(self, fed_name, currenttime, powerflow_output, index):
        return

class DataWriter:
    modes = {
        'h5': hdf5Writer,
        'none': dummyWriter,
    }

    def __init__(self, log_dir, format, columnLength):
        self.writer = self.modes[format](log_dir, columnLength)

    def write(self, fed_name, currenttime, powerflow_output, index):
        self.writer.write(fed_name, currenttime, powerflow_output, index)