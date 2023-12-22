# --------------------------------------------------------------------------------------------------
# DC-AC Tool functions
# Bin Wang
# 4/28/2022
#
# Reference:
# Wang, Bin, and Jin Tan. 2022. DC-AC Tool: Fully Automating the Acquisition of AC Power Flow
# Solution. Golden, CO: National Renewable Energy Laboratory. NREL/TP-6A40-80100.
# https://www.nrel.gov/docs/fy22osti/80100.pdf
# --------------------------------------------------------------------------------------------------

import numpy as np


# --------------------------------------------------------------------------------------------------
# power flow data class
class PowerFlowData:
    def __init__(self, psse):
        self.psse = psse
        # bus data
        self.bus_num = []
        self.bus_type = []
        self.bus_Vpu = []

        # load data
        self.load_id = []
        self.load_bus = []
        self.load_Z = []
        self.load_I = []
        self.load_P = []
        self.load_MW = []
        self.load_Mvar = []
        self.load_MW_total = []
        self.load_Mvar_total = []

        # generator data
        self.gen_id = []
        self.gen_bus = []
        self.gen_status = []
        self.gen_S = []
        self.gen_mod = []
        self.gen_MW = []
        self.gen_Mvar = []
        self.gen_MW_total = []
        self.gen_Mvar_total = []

        # branch data
        self.brc_from = []
        self.brc_to = []
        self.brc_id = []
        self.brc_S = []
        self.brc_P = []
        self.brc_Q = []

    def getdata(self):
        # bus data
        self.bus_num = self.psse.abusint(-1, 2, "NUMBER")[1][0]
        self.bus_type = self.psse.abusint(-1, 2, "TYPE")[1][0]
        self.bus_Vpu = self.psse.abusreal(-1, 2, "PU")[1][0]

        # load data
        self.load_id = self.psse.aloadchar(-1, 4, "ID")[1][0]
        self.load_bus = self.psse.aloadint(-1, 4, "NUMBER")[1][0]
        self.load_Z = np.asarray(self.psse.aloadcplx(-1, 4, "YLACT")[1][0])
        self.load_I = np.asarray(self.psse.aloadcplx(-1, 4, "ILACT")[1][0])
        self.load_P = np.asarray(self.psse.aloadcplx(-1, 4, "MVAACT")[1][0])
        self.load_MW = self.load_Z.real + self.load_I.real + self.load_P.real
        self.load_Mvar = self.load_Z.imag + self.load_I.imag + self.load_P.imag
        self.load_MW_total = sum(self.load_MW)
        self.load_Mvar_total = sum(self.load_Mvar)

        # generator data
        self.gen_id = self.psse.amachchar(-1, 4, "ID")[1][0]
        self.gen_bus = self.psse.amachint(-1, 4, "NUMBER")[1][0]
        self.gen_status = self.psse.amachint(-1, 4, "STATUS")[1][0]
        self.gen_S = np.asarray(self.psse.amachcplx(-1, 4, "PQGEN")[1][0])
        self.gen_mod = np.asarray(self.psse.amachint(-1, 4, "WMOD")[1][0])
        self.gen_MW = self.gen_S.real
        self.gen_Mvar = self.gen_S.imag
        self.gen_MW_total = sum(self.gen_MW)
        self.gen_Mvar_total = sum(self.gen_Mvar)

        # branch data
        ierr, iarray = self.psse.abrnint(-1, 0, 0, 3, 2, ["FROMNUMBER", "TONUMBER"])
        self.brc_from = iarray[0][:]
        self.brc_to = iarray[1][:]
        self.brc_id = self.psse.abrnchar(-1, 0, 0, 3, 2, ["ID"])[1][0]
        self.brc_S = np.asarray(self.psse.abrncplx(-1, 1, 1, 3, 2, ["PQ"])[1][0])
        self.brc_P = self.brc_S.real
        self.brc_Q = self.brc_S.imag


# --------------------------------------------------------------------------------------------------
# check power flow solvability by running NR for up to multiple times (without adjusting loading)
# input: option - choose solver, n_flag1_max - maximum number of runs for power flow
# output: solved_flag, 0 - solved, 1 - reach maximum iteration number, 2 - blow up

# The following function was prepared based on this reference: Whit. 2012. 'Silencing PSSE Output,'
# Python for Power Systems. [Online] http://www.whit.com.au/blog/2012/03/silencing-psse-output/
