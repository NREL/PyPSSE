import time
import helics as h
from math import pi
import random
import time
import random
initstring = "-f 2 --name=mainbroker --port=23404"
fedinitstring = "--broker=mainbroker --federates=1"
deltat = 0.01

helicsversion = h.helicsGetVersion()

print("PI SENDER: Helics version = {}".format(helicsversion))

# Create broker #
print("Creating Broker")
broker = h.helicsCreateBroker("zmq", "", initstring)
#print(broker.port)
print("Created Broker: ", broker)
print("Checking if Broker is connected")
isconnected = h.helicsBrokerIsConnected(broker)
print("Checked if Broker is connected")

if isconnected == 1:
    print("Broker created and connected")

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
h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, 60 * 60)
#h.helicsFederateInfoSetIntegerProperty(fedinfo, h.helics_property_int_log_level, 20)
# Create value federate #
vfed = h.helicsCreateValueFederate("Test Federate", fedinfo)
print("PI SENDER: Value federate created")
pubA = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load1.P", "double", "")
pubB = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load1.Q", "double", "")
pubC = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load2.P", "double", "")
pubD = h.helicsFederateRegisterGlobalTypePublication(vfed, "test.load2.Q", "double", "")
print("PI SENDER: Publication registered")
sub1 = h.helicsFederateRegisterSubscription(vfed, "psse.Buses.153.PU", "")
sub2 = h.helicsFederateRegisterSubscription(vfed, "psse.Buses.154.PU", "")
#h.helicsInputSetMinimumChange(sub1, 0.1)

# Enter execution mode #
h.helicsFederateEnterExecutingMode(vfed)

basevolt = 2.40
X = 20.0
currenttime = 0
for t in range(0, 25):
    time_requested = t * 60 * 60 
    
    iteration_state = h.helics_iteration_result_iterating
    for i in range(5):
        if i == 0:
            while currenttime < time_requested:
                    currenttime = h.helicsFederateRequestTime(vfed, time_requested)
        else:
            currenttime, iteration_state = h.helicsFederateRequestTimeIterative(
                vfed,
                time_requested,
                h.helics_iteration_request_force_iteration #helics_iteration_request_force_iteration, helics_iteration_request_iterate_if_needed
            )
        A = 200 + random.random() * X
        B = 100 + random.random() * X
        C = 400 + random.random() * X
        D = 350 + random.random() * X
        h.helicsPublicationPublishDouble(pubA, A)
        h.helicsPublicationPublishDouble(pubB, B)
        h.helicsPublicationPublishDouble(pubC, C)
        h.helicsPublicationPublishDouble(pubD, D)
        print(f"Powers  published: {A}, {B}, {C}, {D}")
        value1 = h.helicsInputGetDouble(sub1)
        value2 = h.helicsInputGetDouble(sub2)
        print("PSS/E voltages: bus 153 {} p.u., bus 154 {} p.u.".format(value1, value2))
        print(f"Current time: {time_requested}, Granted time: {currenttime}")
        #i+=1
    


h.helicsFederateFinalize(vfed)
print("PI SENDER: Federate finalized")

while h.helicsBrokerIsConnected(broker):
    time.sleep(1)

h.helicsFederateFree(vfed)
h.helicsCloseLibrary()

print("PI SENDER: Broker disconnected")