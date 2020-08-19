import os
from multiprocessing import current_process
import inspect
from queue import Empty
from PyDSS.dssInstance import OpenDSS
from PyDSS.valiate_settings import validate_settings
from PyDSS.api.src.web.parser import restructure_dictionary
from PyDSS.api.src.app.arrow_writer import ArrowWriter

class PyDSS:

    commands = {
        "run" : None
    }

    def __init__(self, event=None, queue=None):

        self.initalized = False
        self.uuid = current_process().name

        ''' TODO: work on logging.yaml file'''
        
        logging.info("{} - initialized ".format({self.uuid}))

        self.shutdownevent = event
        self.queue = queue

        try:
            self.pydss_obj = OpenDSS()
        except:
            result = {"Status": 500, "Message": f"Failed to create a pyPSSE instance"}
            self.queue.put(result)
            return

        #self.RunSimulation()
        logger.info("{} - pyPSSE dispatched".format(self.uuid))

        result = {
            "Status": 200,
            "Message": "pyPSSE {} successfully initialized.".format(self.uuid),
            "UUID":self.uuid
        }

        if self.queue != None: self.queue.put(result)

        self.run_process()
    
    def run_process(self):
        logger.info("pyPSSE simulation starting")
        while not self.shutdownevent.is_set():
            try:
                task = self.queue.get()
                if task == 'END':
                    break
                elif "parameters" not in task:
                    result = {
                        "Status": 500,
                        "Message": "No parameters passed"
                    }
                else:
                    command = task["command"]
                    parameters = task["parameters"]
                    if hasattr(self, command):
                        func = getattr(self, command)
                        status, msg = func(parameters)
                        result = {"Status": status, "Message": msg, "UUID": self.uuid}
                    else:
                        logger.info(f"{command} is not a valid PyDSS command")
                        result = {"Status": 500, "Message": f"{command} is not a valid PyDSS command"}
                self.queue.put(result)
            
            except Empty:
                continue

            except (KeyboardInterrupt, SystemExit):
                break
        logger.info(f"pyPSSE subprocess {self.uuid} has ended")


    def close_instance(self):
        del self.pydss_obj
        logger.info(f'pyPSSE case {self.uuid} closed.')

    def init(self, params):
        logger.info(f'Reading pyPSSE project')

        args = restructure_dictionary(params)

        try:
            validate_settings(args)
            logger.info(f'Parameter validation a success')
        except Exception as e:
            return 500, f"Invalid simulation settings passed, {e}"

        try:
            self.pydss_obj.init(args)
            export_path = os.path.join(self.pydss_obj._dssPath['Export'], args['Project']['Active Scenario'])
            Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()
            self.a_writer = ArrowWriter(export_path, Steps)
            self.initalized = True
            return 200, "PyDSS project successfully loaded"
        except Exception as e:
            return 500, f"Failed to load a PyDSS project, {e}"

    def run(self, params):
        if self.initalized:
            try:
                Steps, sTime, eTime = self.pydss_obj._dssSolver.SimulationSteps()
                for i in range(Steps):
                    results = self.pydss_obj.RunStep(i)
                    restructured_results = {}
                    for k, val in results.items():
                        if "." not in k:
                            class_name = "Bus"
                            elem_name = k
                        else:
                            class_name, elem_name = k.split(".")
                        if class_name not in restructured_results:
                            restructured_results[class_name] = {}
                        if not isinstance(val, complex):
                            restructured_results[class_name][elem_name] = val
                    self.a_writer.write(
                        self.pydss_obj._Options["Helics"]["Federate name"],
                        self.pydss_obj._dssSolver.GetTotalSeconds(),
                        restructured_results,
                        i
                    )

                self.initalized = False
                return 200, f"Simulation complete..."
            except Exception as e:
                self.initalized = False
                return 500, f"Simulation crashed at at simulation time step: {self.pydss_obj._dssSolver.GetDateTime()}, {e}"
        else:
            return 500, f"No project initialized. Load a project first using the 'init' command"

    def registerPubSubs(self, params):
        subs = params["Subscriptions"]
        pubs = params["Publications"]
        self.pydss_obj._HI.registerPubSubTags(pubs, subs)
        return 200, f"Publications and subscriptions have been registered; Federate has entered execution mode"




if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    logger.basicConfig(level=logger.INFO, format=FORMAT)
    a = PyDSS()
    del a
