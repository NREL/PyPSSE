"""
author:Kapil Duwadi
Date: June 8, 2020
"""

# Standard imports

# Third-party imports
import os

# Internal imports

class Reader:

    def __init__(self, psse_instance, logger):

        self.psse = psse_instance
        self.logger = logger
        self.buses = self.get_data('abus', tails=['int'], strings=["NUMBER"], flags=[2])
        self.loads = self.get_data('aload', tails=['int','char'], strings=["NUMBER","ID"], flags=[4,4])
        self.fixed_stunts = self.get_data('afxshunt',tails=['int','char'], strings=["NUMBER","ID"], flags=[4,4])
        self.generators = self.get_data('amach',tails=['int','char'], strings=["NUMBER","ID"], flags=[4,4])
        self.branches = self.get_data('abrn',tails=['int','int'], strings=["FROMNUMBER","TONUMBER"], flags=[2,2])
        self.transformers = self.get_data('atr3',tails=['int','int','int'], strings=["WIND1NUMBER","WIND2NUMBER","WIND3NUMBER"], flags=[2,2,2])
        self.Area = self.get_data('aarea',tails=['int','char'], strings=["NUMBER","AREANAME"], flags=[2,2])  # Talk to Aadil
        self.DC_branch = self.get_data('a2trmdc',tails=['int','int'], strings=["FROMNUMBER","TONUMBER"], flags=[2,2])  # three terminal dc lines not implemented
        self.multi_term_dc = self.get_data('amultitrmdc',tails=['int','int'], strings=["VCNPOSNUMBER","VCNNEGNUMBER"], flags=[2,2])
        self.switched_shunt = self.get_data('aswsh', tails=['int','char'], strings=["NUMBER","DEVICENAME"], flags=[4,4])
        self.zones = self.get_data('azone',tails=['int','char'], strings=["NUMBER","ZONENAME"], flags=[2,2])
        self.owners = self.get_data('aowner',tails=['int','char'], strings=["NUMBER","OWNERNAME"], flags=[2,2])

        return


    def get_data(self, func_name, tails = [], strings= [], flags = []):

        array_list = []
        for tail, string, flag in zip(tails,strings,flags):
            self.logger.info(f'Executing self.psse.{func_name.lower() + tail}(sid=-1, flag={flag}, string="{string}")')
            ierr, array_1 = eval(f'self.psse.{func_name.lower() + tail}(sid=-1, flag={flag}, string="{string}")')
            assert (ierr == 0), f"Error code {ierr}, while running function '{func_name.lower() + tail}'"
            array_list.append([x for array in array_1 for x in array])

        self.logger.info(f"{func_name} count - {len(array_1)}")
        if len(array_list) == 1:
            return array_list[0]
        return list(zip(*array_list))
