
import time
import helics as h
from math import pi
import random
import time
import os
initstring = "-f 2 --name=mainbroker"
fedinitstring = "--broker=mainbroker --federates=1"
deltat = 0.01

helicsversion = h.helicsGetVersion()

# Create broker #
broker = h.helicsCreateBroker("zmq", "", initstring)
isconnected = h.helicsBrokerIsConnected(broker)

# Create Federate Info object that describes the federate properties #
fedinfo = h.helicsCreateFederateInfo()

# Set Federate name #
h.helicsFederateInfoSetCoreName(fedinfo, "Test Federate")

# Set core type from string #
h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "zmq")

# Federate init string #
h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring)

# Set the message interval (timedelta) for federate. Note th#
# HELICS minimum message time interval is 1 ns and by default
# it uses a time delta of 1 second. What is provided to the
# setTimedelta routine is a multiplier for the default timedelta.

# Set one second message interval #
h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, deltat)
#h.helicsFederateInfoSetIntegerProperty(fedinfo, h.helics_property_int_log_level, 20)
# Create value federate #
vfed = h.helicsCreateValueFederate("Test Federate", fedinfo)

# Register the publication #
pub1 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load1.P", "double", "")
pub2 = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load1.Q", "double", "")
sub1 = h.helicsFederateRegisterSubscription(vfed, "psse.Buses.154.PU", "")
#h.helicsInputSetMinimumChange(sub1, 0.1)

# Enter execution mode #

h.helicsFederateEnterExecutingModeIterative(
            vfed, 
             h.helics_iteration_request_iterate_if_needed
            )

for t in range(1, 30):
    time_requested = t 
    #currenttime = h.helicsFederateRequestTime(vfed, time_requested)
    iteration_state = h.helics_iteration_result_iterating
    for i in range(15):
        currenttime, iteration_state = h.helicsFederateRequestTimeIterative(
            vfed,
            time_requested,
            h.helics_iteration_request_iterate_if_needed
        )
        print(f"currenttime={currenttime} , time_requested={time_requested}")
        kW = 5000
        kVAR  = 4000 + 1000. / (1.0 + i)
        h.helicsPublicationPublishDouble(pub1, kW)
        print(f"kW={kW} , kVAR={kVAR}")
        h.helicsPublicationPublishDouble(pub2, kVAR)
        value = h.helicsInputGetVector(sub1)
        print(value)

h.helicsFederateFinalize(vfed)

while h.helicsBrokerIsConnected(broker):
    time.sleep(1)

h.helicsFederateFree(vfed)
h.helicsCloseLibrary()
