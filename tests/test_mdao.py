import os
from pathlib import Path

import openmdao.api as om

from pypsse.common import SIMULATION_SETTINGS_FILENAME
from pypsse.mdao_interface import PypsseMdaoModel


def test_mdao_example():
    examples_path = Path(__file__).parent
    sim_setting_filepath = examples_path / "examples" / "static_example" / SIMULATION_SETTINGS_FILENAME
    mdao_io_filepath = Path(__file__).parent / "interfaces" / "openmdao_example" / "mdao_settings.toml"

    model_name = "pypsse"
    model = om.Group()

    psse_subsystem = PypsseMdaoModel(sim_setting_filepath, mdao_io_filepath)

    model.add_subsystem(name=model_name, subsys=psse_subsystem, promotes_inputs=psse_subsystem._list_inputs())

    prob = om.Problem(model)

    prob.driver = om.DifferentialEvolutionDriver()
    prob.driver.options["max_gen"] = 3
    prob.driver.options["pop_size"] = 3

    for input_name in psse_subsystem._list_inputs():
        prob.model.add_design_var(input_name, lower=0.0, upper=5.0)

    prob.model.add_objective(f"{model_name}.Buses_153_PU")

    prob.setup()

    # prob.run_model()

    prob.run_driver()
    
