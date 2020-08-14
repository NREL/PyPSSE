from PyDSS.api.src.app.arrow_writer import ArrowWriter
from PyDSS.api.src.app.HDF5 import hdf5Writer

class DataWriter:
    modes = {
        'arrow': ArrowWriter,
        'h5': hdf5Writer,
        # 'feather': featherWriter,
        # 'parquet': parquetWriter,
        # "pickle": pickleWriter,
    }

    def __init__(self, log_dir, format, columnLength):
        self.writer = self.modes[format](log_dir, columnLength)

    def write(self, fed_name, currenttime, powerflow_output, index):
        self.writer.write(fed_name, currenttime, powerflow_output, index)