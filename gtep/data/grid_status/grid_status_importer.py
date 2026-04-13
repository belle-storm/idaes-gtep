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
from prescient.data.providers.gmlc_data_provider import GmlcDataProvider
import datetime
import pandas as pd

Options = PrescientConfig


def get_data_provider(options: Options) -> DataProvider:
    """Get a CustomDataProvider instance"""
    return CustomDataProvider(options)


class CustomDataProvider(GmlcDataProvider):
    def __init__(self, options: Options):
        pass
