from PyDSS.dssInstance import OpenDSS
from PyDSS.valiate_settings import validate_settings
from PyDSS.api.src.web.parser import restructure_dictionary
from PyDSS.api.src.app.DataWriter import DataWriter
import toml
import time
import os

def run_test(tomlpath):
    pydss_obj = OpenDSS()
    with open(tomlpath) as f_in:
        args = toml.load(f_in)

    try:
        validate_settings(args)
        print(f'Parameter validation a success')
    except Exception as e:
        print(f"Invalid simulation settings passed, {e}")
        return

    pydss_obj.init(args)
    export_path = os.path.join(pydss_obj._dssPath['Export'], args['Project']['Active Scenario'])
    Steps, sTime, eTime = pydss_obj._dssSolver.SimulationSteps()
    writer = DataWriter(export_path, format="arrow", columnLength=Steps)

    st = time.time()
    for i in range(Steps):
        results = pydss_obj.RunStep(i)
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
        writer.write(
            pydss_obj._Options["Helics"]["Federate name"],
            pydss_obj._dssSolver.GetTotalSeconds(),
            restructured_results,
            i
        )
    print("{} seconds".format(time.time() - st))

run_test(r"C:\Users\alatif\Desktop\PyDSS_tests\IEEE123\simulation.toml")