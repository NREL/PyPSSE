# Standard imports
import os

# Third-party library imports
import pandas as pd
import numpy as np
import datetime
# Internal imports
from pypsse.Modes.abstract_mode import AbstractMode

class Static(AbstractMode):
    def __init__(self,psse, dyntools, settings, export_settings, logger):
        super().__init__(psse, dyntools, settings, export_settings, logger)
        self.time = datetime.datetime.strptime(settings["Start time"], "%m/%d/%Y %H:%M:%S")
        self.incTime = settings["Step resolution (sec)"]
        return

    def init(self, bussubsystems):

        super().init(bussubsystems)

        # get_baseload data
        self.get_basloadinfo()

        # Read loadprofiles
        self.read_input_data()
        self.counter = 0
        self.initialization_complete = True
        return


    def step(self,dt):

        # convert loads
        self.convert_load(self.counter)

        ierr = self.PSSE.fnsl()

        # check if powerflow completed successfully
        if ierr == 0:
            pass
            self.time = self.time + datetime.timedelta(seconds=self.incTime)
        else:
            raise Exception(f'Error code {ierr} returned from PSSE while running powerflow, please follow \
                            PSSE doumentation to know more about error')

        self.counter += 1

    def getTime(self):
        return self.time

    def read_input_data(self):

        self.input_data_path = os.path.join(self.settings['Project Path'],'Load_profile_data')
        self.profile_data = {}

        if os.path.exists(self.input_data_path):
            if 'loadprofilemapping.csv' in os.listdir(self.input_data_path):
                self.load_profile_mapper = pd.read_csv(os.path.join(self.input_data_path, 'loadprofilemapping.csv'))
            else:
                raise Exception("'loadprofilemapping.csv' can not be found")
            if set(['BusNumbers', 'LoadIDs']).issubset(set(self.load_profile_mapper.columns)):
                self.logger.info(f"Sucessfully read {'loadprofilemapping.csv'}")
            else:
                raise Exception("Incorrect column names in 'loadprofilemapping.csv'")
        else:
            raise Exception(f"{self.input_data_path} does not exists")
        self.profilelist = np.unique(self.load_profile_mapper['ProfileNames'].tolist())

        for profilename in self.profilelist:

            if profilename + '.csv' in os.listdir(self.input_data_path):
                self.logger.info(f"Successfully read {profilename + '.csv'}")
                self.profile_data[profilename] = pd.read_csv(os.path.join(self.input_data_path, profilename + '.csv'))
            else:
                raise Exception(f"{profilename + '.csv'} does not exists!")

    def get_basloadinfo(self):

        self.baseload = pd.DataFrame()

        # get all load bus numbers
        ierr, loadbusnumbers = self.PSSE.aloadint(sid=-1, flag=4, string="NUMBER")
        assert (ierr == 0), f"Error code {ierr}, while running function 'aloadint'"
        self.baseload['BusNumbers'] = [x for array in loadbusnumbers for x in array]

        # get all load id numbers
        ierr, loadids = self.PSSE.aloadchar(sid=-1, flag=4, string="ID")
        assert (ierr == 0), f"Error code {ierr}, while running function 'aloadchar'"
        self.baseload['LoadIDs'] = [x for array in loadids for x in array]

        # Read loads
        load_strings = {'MVAACT': ['CPAL', 'CPRL'], 'ILACT': ['CCAL', 'CCRL'], 'YLACT': ['CAAL', 'CARL']}

        for load_string, array in load_strings.items():
            ierr, loads = self.PSSE.aloadcplx(sid=-1, flag=4, string=load_string)
            assert (ierr == 0), f"Error code {ierr}, while running function 'aloadcplx'"
            loads = [x for array in loads for x in array]
            self.baseload[array[0]] = [np.real(x) for x in loads]
            self.baseload[array[1]] = [np.imag(x) for x in loads]

        self.baseload = self.baseload.set_index(['BusNumbers', 'LoadIDs'])

    def export(self):


        self.logger.debug('Starting export process. Can take a few minutes for large files')
        excelpath = os.path.join(self.export_path, self.settings["Excel file"])
        achnf = self.dyntools.CHNF(self.outx_path)
        achnf.xlsout(channels='', show=False, xlsfile=excelpath, outfile='', sheet='Sheet1', overwritesheet=True)
        self.logger.debug('{} export to {}'.format(self.settings["Excel file"], self.export_path))

    def convert_load(self, counter):


        for index in range(len(self.load_profile_mapper)):

            rwo_data = self.load_profile_mapper.loc[index]
            busnumber, loadid, profile = rwo_data['BusNumbers'], rwo_data['LoadIDs'], rwo_data['ProfileNames']

            if counter > len(self.profile_data[profile])-1:
                self.counter, counter = 0,0

            multiplier_row = self.profile_data[profile].loc[counter]

            list_of_loads = ['CPAL', 'CPRL', 'CCAL', 'CCRL', 'CAAL', 'CARL']
            multipliers = []
            for load_type in list_of_loads:
                multipliers.append(self.baseload[load_type][busnumber][loadid] * multiplier_row[load_type])

            self.PSSE.load_data_5(busnumber, loadid,
                                  realar1=multipliers[0], realar2=multipliers[1], realar3=multipliers[2],
                                  realar4=multipliers[3], realar5=multipliers[4], realar6=multipliers[5])



