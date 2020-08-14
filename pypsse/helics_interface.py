import pandas as pd
import helics as h
import os
class helics_interface:
    def __init__(self, PSSE, settings, logger):
        self.bus_pubs = ['bus_id', 'bus_Vmag', 'bus_Vang', 'bus_dev']

        self.PSSE = PSSE
        self.logger = logger
        self.settings = settings
        return

    def enter_execution_mode(self):
        h.helicsFederateEnterExecutingMode(self.PSSEfederate)
        return

    def create_federate(self):
        fedinfo = h.helicsCreateFederateInfo()
        h.helicsFederateInfoSetCoreName(fedinfo, self.settings['Federate name'])
        h.helicsFederateInfoSetCoreTypeFromString(fedinfo, self.settings['Core type'])
        h.helicsFederateInfoSetCoreInitString(fedinfo, "--federates=1")
        h.helicsFederateInfoSetTimeProperty(
            fedinfo,
            h.helics_property_time_delta,
            self.settings["Step resolution (sec)"]
        )
        h.helicsFederateInfoSetIntegerProperty(fedinfo, h.helics_property_int_log_level,
                                               self.settings['Helics logging level'])
        h.helicsFederateInfoSetFlagOption(fedinfo, h.helics_flag_uninterruptible, True)
        self.PSSEfederate = h.helicsCreateValueFederate(self.settings['Federate name'], fedinfo)
        return


    def register_publications(self, bus_subsystems):
        self.publications = {}
        for bus_subsystem_id in self.settings['bus_subsystems']["publish_subsystems"]:
            if bus_subsystem_id in bus_subsystems:
                buses = bus_subsystems[bus_subsystem_id]
                for bus_id in buses:
                    self.publications[bus_id] = {}
                    for bus_p in self.bus_pubs:
                        pub =  "{}.bus-{}.{}".format(self.settings['Federate name'], bus_id, bus_p)
                        self.publications[bus_id][pub] = h.helicsFederateRegisterGlobalTypePublication(
                            self.PSSEfederate, pub, 'double', ''
                        )
                        self.logger.debug("Publication registered: {}".format(pub))
        return

    def register_subscriptions(self, bus_subsystem_dict):
        self.subscriptions = {}
        sub_data = pd.read_csv(
            os.path.join(self.settings["Project Path"], 'Case_study', self.settings["Subscriptions file"])
        )
        sub_data = sub_data.values
        r,c = sub_data.shape

        for row in range(r):
            bus_subsystem_id =  sub_data[row,0]
            bus_id = sub_data[row, 1]
            load_id = sub_data[row, 2]
            load_type = sub_data[row, 3]
            sub_tag = sub_data[row, 4]
            scaler = sub_data[row, 5]
            for subsystem_id, buses in bus_subsystem_dict.iteritems():
                if subsystem_id == bus_subsystem_id:
                    for bus in buses:
                        if bus == bus_id:
                            self.subscriptions[sub_tag] = {
                                'bus_subsystem_id' : bus_subsystem_id,
                                'bus_id': bus_id,
                                'load_id': load_id,
                                'load_type': load_type,
                                'scaler' : scaler,
                                'subscription':  h.helicsFederateRegisterSubscription(self.PSSEfederate, sub_tag, ""),
                            }
                            self.logger.debug("Bus subsystems {}'s bus {}'s load {} has subscribed to {}".format(
                                bus_subsystem_id,  bus_id, load_id, sub_tag
                            ))

        return

    def request_time(self, t):
        currenttime = h.helicsFederateRequestTime(self.PSSEfederate, t)
        self.logger.debug('pyPSSE: helics time requested (sec): {}'.format(t))
        self.logger.debug('pyPSSE: helics time granted (sec): {}'.format(currenttime))
        return currenttime

    def publish(self, all_bus_data):
        all_bus_data = pd.DataFrame(all_bus_data, columns=self.bus_pubs)
        for r in all_bus_data.index:
            bus_data = all_bus_data.loc[r]
            bus_id = bus_data['bus_id']
            for c in bus_data.index:
                data = bus_data[c]
                bus_property_names = self.publications[bus_id].keys()
                check = [True if c in x else False for x in bus_property_names]
                pub_id = check.index(True)
                pub_id = bus_property_names[pub_id]
                pub = self.publications[bus_id][pub_id]
                h.helicsPublicationPublishDouble(pub, data)
                self.logger.debug('pyPSSE: published "{}" for tag: {}'.format(data, pub_id))
        return

    def subscribe(self):
        for sub_tag, sub_data in self.subscriptions.iteritems():
            sub_data['value'] = h.helicsInputGetDouble(sub_data['subscription'])
            self.logger.debug('pyPSSE: Data recieved {} for tag {}'.format(sub_data['value'], sub_tag))
        return self.subscriptions