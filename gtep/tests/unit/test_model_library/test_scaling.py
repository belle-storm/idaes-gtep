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

"""
Unit tests for the scaling function for Generation and Transmission Expansion Planning (GTEP)
Model
"""

import pytest
from os.path import abspath, join, dirname
from gtep.model_library.scaling import add_load_scaling
from gtep.gtep_model import ExpansionPlanningModel, create_stages
from gtep.gtep_data import ExpansionPlanningData


@pytest.fixture
def create_test_model():
    # create the ConcreteModel
    curr_dir = dirname(abspath(__file__))
    debug_data_path = abspath(join(curr_dir, "..", "..", "data", "5bus"))
    dataObject = ExpansionPlanningData()
    dataObject.load_prescient(debug_data_path)
    modObject = ExpansionPlanningModel(data=dataObject)
    m = modObject.create_model()
    return modObject


# m is the model
# b is the representative period
@pytest.fixture
def create_rep(m):
    pass


def test_add_load_scaling():
    pass
