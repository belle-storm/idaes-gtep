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
# date: 04/15/2026

from pyomo.environ import *
from prescient.simulator.config import PrescientConfig
from prescient.data.data_provider import DataProvider
import datetime
import pandas as pd
import os
from egret.data.model_data import ModelData as EgretModel

Options = PrescientConfig


def get_options(data_path, options_dict=None):
    data_type = "ercot"

    if options_dict is None:
        options_dict = {
            "data_path": data_path,
            "data_provider": ErcotDataProvider,
            "day_ahead_pricing": "LMP",
            "sced_horizon": 1,
            "sced_frequency_minutes": 60,
        }

    # start date should be grabbed from the data?
    # num days: 365?
    # ruc_horizon - 36

    pass


def create_empty_model(data_path):
    # create the skeleton of the model_data
    model_data = EgretModel.empty_model_data_dict()
    elements = model_data["elements"]
    system = model_data["system"]
    system["name"] = "Ercot"
    bus_id_to_name = _parse_bus(data_path, elements)


def _parse_bus(data_path, elements):
    # set up holders
    elements["bus"] = {}
    elements["load"] = {}
    bus_areas = set()
    bus_id_to_name = {}
    # grab data ercot electrical bus info file
    bus_file = os.path.join(
        data_path, "ercot_settlement_points_electrical_bus_mapping-2_2026.csv"
    )
    if os.path.isfile(bus_file):
        bus_df = pd.read_csv(bus_file)
        for ix, row in bus_df.iterrows():
            bus_name = str(row["electrical_bus"])
            bus_dict = {
                "id": row["psse_bus_number"],
                "bus_label": row["psse_bus_name"],
                "matpower_bustype": "ref",  # TODO confirm
                "base_kv": row["voltage_level"],
                "area": row["substation"],
                "zone": row["settlement_load_zone"],
                "node": row["node_name"],
            }
            elements["bus"][bus_name] = bus_dict
            bus_areas.add(bus_dict["area"])
            bus_id_to_name[bus_dict["id"]] = bus_name
        # add the areas
        elements["area"] = {name: dict() for name in bus_areas}
    else:
        # if the ercot file isn't found at data path
        raise KeyError(
            "File not found: ercot_settlement_points_electrical_bus_mapping-2_2026.csv"
        )

    return bus_id_to_name


def _parse_branches(data_path, elements, bus_id_to_name):
    pass


def _parse_gens(data_path, elements, bus_id_to_name):
    elements["generator"] = {}
    # grab data ercot electrical bus info file
    gen_file = os.path.join(data_path, "ercot_gen_resources.csv")
    if os.path.isfile(gen_file):
        gen_df = pd.read_csv(gen_file)
        for ix, row in gen_df.iterrows():
            gen_name = row["resource_name"]
            gen_dict = {
                "in_service": True,
                "unit_type": str(row["resource_type"]),
                "settlement_point_name": str(row["settlement_point_name"]),
                "qse": str(row["qse"]),
                "dme": str(row["dme"]),
            }

    pass


def get_data_provider(options: Options) -> DataProvider:
    """Get a CustomDataProvider instance"""
    return ErcotDataProvider(options)


class ErcotDataProvider(DataProvider):
    def __init__(self, options: Options):
        pass
