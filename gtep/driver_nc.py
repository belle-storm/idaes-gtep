#################################################################################
# The Institute for the Design of Advanced Energy Systems Integrated Platform
# Framework (IDAES IP) was produced under the DOE Institute for the
# Design of Advanced Energy Systems (IDAES).
#
# Copyright (c) 2018-2026 by the software owners: The Regents of the
# University of California, through Lawrence Berkeley National Laboratory,
# National Technology & Engineering Solutions of Sandia, LLC, Carnegie Mellon
# University, West Virginia University Research Corporation, et al.
# All rights reserved.  Please see the files COPYRIGHT.md and LICENSE.md
# for full copyright and license information.
#################################################################################
import logging
import pyomo.environ as pyo
from pyomo.contrib.appsi.solvers.highs import Highs
from pyomo.contrib.appsi.solvers.gurobi import Gurobi

from gtep.gtep_model import ExpansionPlanningModel
from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
from gtep.gtep_solution import ExpansionPlanningSolution

logger = logging.getLogger("gtep.driver_nc")
logger.setLevel(logging.INFO)

# Add data
data_path = "./gtep/data/nc_data/"
data_object = NCExpansionPlanningData(
    stages=2,
    num_reps=2,
    len_reps=1,
    num_commit=6,
    num_dispatch=4,
    duration_dispatch=15,
)
data_object.load_nc_data(data_path)

# Populate and create GTEP model
mod_object = ExpansionPlanningModel(data=data_object)

mod_object.config["include_investment"] = True
mod_object.config["include_commitment"] = False
mod_object.config["include_redispatch"] = True
mod_object.config["scale_loads"] = False
mod_object.config["transmission"] = True
mod_object.config["storage"] = True
mod_object.config["flow_model"] = "DC"
mod_object.config["advanced_hydro"] = False

mod_object.create_model()

# Apply transformations to logical terms
# pyo.TransformationFactory("gdp.bound_pretransformation").apply_to(mod_object.model)
pyo.TransformationFactory("gdp.bigm").apply_to(mod_object.model)

# Add solver
opt = pyo.SolverFactory("gurobi")
# opt = pyo.SolverFactory("highs")

mod_object.results = opt.solve(mod_object.model, tee=True)
print(mod_object.results)

quit()

sol_object = ExpansionPlanningSolution()
sol_object.load_from_model(mod_object)
sol_object.dump_json("./gtep_solution.json")
sol_object.import_data_object(data_object)

sol_object.plot_levels(save_dir="./plots/")

pass
