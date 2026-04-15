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

# Generation and Transmission Expansion Planning
# IDAES project
# author: Belle Storm
# date: 04/13/2026

from pyomo.environ import *
from prescient.simulator.config import PrescientConfig
from prescient.data.data_provider import DataProvider
import datetime
import pandas as pd
from egret.data.model_data import ModelData as EgretModel

Options = PrescientConfig


def get_options(data_path, options_dict=None):
    data_type = "ercot"

    if options_dict is None:
        options_dict = {
            "data_path": data_path,
            "data_provider": CaisoDataProvider,
            "day_ahead_pricing": "LMP",
            "sced_horizon": 1,
            "sced_frequency_minutes": 60,
        }

    # start date should be grabbed from the data?
    # num days: 365?
    # ruc_horizon - 36

    pass


def create_empty_model():
    # create the skeleton of the model_data
    model_data = EgretModel.empty_model_data_dict()
    elements = model_data["elements"]
    system = model_data["system"]
    system["name"] = "caiso"


def parse_bus():
    # pull in the ercot settlement_points_bus_mapping
    # id = psse_bus_number
    # Bus Name = electrical_bus
    # Bus label = psse_bus_name
    # node = node_name
    # area = substation
    # zone = settlement_load_zone
    # base_kv = voltage_level
    # note: substation = unit substation
    # electrical bus = resource node
    pass


def get_data_provider(options: Options) -> DataProvider:
    """Get a CustomDataProvider instance"""
    return CaisoDataProvider(options)


class CaisoDataProvider(DataProvider):
    def __init__(self, options: Options):
        pass
