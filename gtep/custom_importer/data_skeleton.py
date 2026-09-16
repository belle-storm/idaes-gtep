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

"""GTEP Data Skeleton.

This module provides helper functions for a GTEP-friendly data skeleton 
to support expandable data importers.

:module: data_skeleton
:author: bstorm
"""

import egret.data.model_data as md
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
from math import isnan



class CustomImporter(ABC):
    def __init__(self, options: dict[str, any] = None) -> None:
        """Initialize the provider."""
        # check for the NC data files
        if not os.path.exists(options["data_path"]):
            raise ValueError(
                f'NC Data directory "{options["data_path"]}" does not exist'
            )
    
        # grab the start and end data times
        self.metadata_df = self._read_simulation_obj(options["data_path"])
        self._start_time, end_time = self._get_data_date_range(self.metadata_df)
    
        # check if there is a num_days key
        if "num_days" in options.keys():
            end_time = self._start_time + timedelta(days=options["num_days"])
        self._end_time = end_time
    
        self._cache = self.parse_to_cache(
            options["data_path"],
            self._start_time,
            self._end_time,
        )

    @abstractmethod
    def _read_simulation_obj(self, dir: str) -> pd.DataFrame:
        """Read simulation object metadata to contain the metadata about
        the data

        :param dir: Directory containing simulation object or metadata file.
        :type dir: str
        :return: Simulation object metadata.
        :rtype: pandas.DataFrame
        """

        pass

    def _get_data_date_range(
        self, metadata_df: pd.DataFrame, time_type:str="REAL TIME",
    ) -> tuple[datetime, datetime]:
        """Get the start and end datetimes from metadata.

        :param metadata_df: Metadata dataframe.
        :type metadata_df: pandas.DataFrame
        :return: Start and end datetimes.
        :rtype: tuple[datetime, datetime]
        """
        data_start = pd.to_datetime(metadata_df.loc["Date_From", time_type])
        data_end = pd.to_datetime(metadata_df.loc["Date_To", time_type])

        return data_start, data_end

    @staticmethod
    def _build_system(system: dict[str, any], name=None) -> None:
        """Populate the system section of the skeleton."""
        system["name"] = name
        system["baseMVA"] = None
        system["reference_bus"] = None
        system["reference_bus_angle"] = None
        system["time_period_length_minutes"] = None
        system["time_keys"] = []
        system["min_operating_reserve"] = None
        system["min_spinning_reserve"] = None

    @staticmethod
    def _build_elements(elements: dict[str, any]) -> None:
        """Populate the elements section of the skeleton."""
        elements["bus"] = {}
        elements["load"] = {}
        elements["shunt"] = {}

        elements["branch"] = {}
        elements["dc_branch"] = {}

        elements["generator"] = {}

        elements["storage"] = {}


    def create_skeleton(self, data_type_name) -> dict[str, any]:
        """Create an empty model data skeleton.

        :return: Empty model data dictionary.
        :rtype: dict[str, Any]
        """
        model_data = md.ModelData.empty_model_data_dict()
        elements = model_data["elements"]
        system = model_data["system"]

        self._build_elements(elements)
        self._build_system(system, data_type_name)

        return model_data

    @abstractmethod
    def _read_buses(
        self, base_dir: str, elements: dict[str, any], system: dict[str, any]
    ) -> None:
        """Read bus and loads data and save that data to the model elements."""

        """
        BUS DATA

        While you can add additional fields under each bus dictionary, 
        GTEP requires the following minimum key-value pairs:
        bus_dict = {
            "id": , #str
            "base_kv": , #float >0
            "matpower_bustype": , #str
            "vm": , #float
            "va": , #float
            "v_min": , #float
            "v_max": , #float
            "area": , #str
            "zone": , #str
            }

        Each bus should have the must have the same size of bus dictionary. 
        Each area will be saved to the areas section of the model elements

        Suggested workflow for this method: 

        #look for the target bus data file
        file_path = os.path.join(base_dir, "bus.csv")
        if not os.path.exists(file_path):
            raise ValueError(f'NC Data File "{file_path}" does not exist')
        bus_df = pd.read_csv(file_path)
        
        #iterate through the bus data
        bus_areas = set()
        for idx, row in bus_df.iterrows():
        
            bus_name = str(row["Bus Name"])
            area = row["Area"]
            if pd.isna(area):
                area = bus_name.split(' ')[0]
            bus_dict = {
                "id": str(row["Bus ID"]),
                "base_kv": float(row["BaseKV"]),
                "matpower_bustype": row["Bus Type"],
                "vm": float(row["V Mag"]),
                "va": float(row["V Angle"]),
                "v_min": 0.95,
                "v_max": 1.05,
                "area": area,
                "zone": str(row["Zone"]),
                # extra data
                "carrier": str(row["Carrier"]),
            }
            #check the base_kv follows rules
            if bus_dict["base_kv"] <= 0:
                raise ValueError(
                    f'BaseKV value for bus "{bus_name}" is <= 0. Not supported.'
                )
        
            #save this bus
            bus_areas.add(bus_dict["area"])
            elements["bus"][bus_name] = bus_dict

        # add filler values for reference buses
        system["reference_bus"] = None
        system["reference_bus_angle"] = 0
    
        # add the areas
        elements["area"] = {name: dict() for name in bus_areas}
        """
        """
        LOAD DATA

        GTEP requires the following minimum format for each load:
        load_dict = {
            "bus": bus_name, #str
            "in_service":  #bool
            "p_load": PD, #dict
            "q_load": QD, #dict
            "area": , #str
            "zone": , #str
        }

        GTEP requires that p_load and q_load are dictionaries with the following structure:
        {"data_type": "time_series", "values": []}

        Each load is saved in the model elements under the bus name for that load:
        elements["load"][bus_name] = load_dict
        """
        pass

    @abstractmethod
    def _read_branches(self, base_dir: str, elements: dict[str, any]) -> None:
        """Read AC and DC branch data."""
        """
        BRANCH DATA
        
        While you can add additional fields under each branch dictionary, 
        GTEP requires the following minimum key-value pairs:
        branch_dict = {
            "from_bus": , #str
            "to_bus": , #str
            "in_service": , #bool
            "resistance": ,  #float
            "reactance": ,  #float
            "charging_susceptance": , #float
            "rating_long_term": , #float
            "rating_short_term": , #float
            "rating_emergency": , #float
            "angle_diff_min": , #float
            "angle_diff_max": , #float
            "pf": None, #can be None
            "qf": None, #can be None
            "pt": None, #can be None
            "qt": None, #can be None
            "branch_type": , #str
            "capital_cost": , #float
            "distance": , #float
            "loss_rate": , #float
        }
        
        Each branch should have the must have the same size of branch dictionary. 
        Then should be saved to the model elements under the branch name.
        
        Suggested workflow for this method: 

        #look for the branch data file needed
        file_path = os.path.join(base_dir, "branch.csv")
        if not os.path.exists(file_path):
            raise ValueError(f'NC Data File "{file_path}" does not exist')
        branch_df = pd.read_csv(file_path)
        
        #iterate through branches
        for idx, row in branch_df.iterrows():
        
            branch_dict = {
                "from_bus": , #str
                "to_bus": , #str
                "in_service": , #bool
                "resistance": ,  #float
                "reactance": ,  #float
                "charging_susceptance": , #float
                "rating_long_term": , #float
                "rating_short_term": , #float
                "rating_emergency": , #float
                "angle_diff_min": , #float
                "angle_diff_max": , #float
                "pf": None, #can be None
                "qf": None, #can be None
                "pt": None, #can be None
                "qt": None, #can be None
                "branch_type": , #str
                "capital_cost": , #float
                "distance": , #float
                "loss_rate": , #float
                # extra columns
                "carrier": , #Any
            }
        
            name = str(row["UID"])
            elements["branch"][name] = branch_dict #or elements["dc_branch"][name] = dc_branch_dict
        """
        pass

    @abstractmethod
    def _read_generators(self, base_dir: str, elements: dict[str, any]) -> None:
        """Read generator data."""
        """
        GENERATOR DATA
        
        While you can add additional fields under each generator dictionary, 
        GTEP requires the following minimum key-value pairs:
        gen_dict = {
            "bus": bus_name, #str
            "in_service": , #bool
            "mbase": , #float
            "pg": , #float
            "qg": , #float
            "p_min": , #float
            "p_max": , #float
            "q_min": , #float
            "q_max": , #float
            "ramp_q": , #float
            "fuel": , #str
            "unit_type": , #str
            "area": elements["bus"][bus_name]["area"], #str match with bus area
            "zone": elements["bus"][bus_name]["zone"], #str match with bus zone
            "p_fuel": , #dict
            "p_cost": ,#dict
            "Unit Type": , #str - should match one of the expected type abbreviations (see below)
            "generator_type": , #str - renewable or thermal
            "ramp_agc": , #float
            "ramp_up_60min": , #float
            "ramp_down_60min": , #float
            "fuel_cost": , #float

            #the keys below are required but these are defaults
            "spinning_reserve_frac" : 0.1,
            "quickstart_reserve_frac" : 0.1,
            "capital_multiplier" : 1,
            "extension_multiplier" : 0,
            "max_operating_reserve" : 1,
            "max_spinning_reserve" : 1,
            "max_quickstart_reserve" : 1,
            "ramp_up_rate" : 0.1,
            "ramp_down_rate" : 0.1,
            "start_fuel" : 1,
            "heat_rate" : 1,
            "non_fuel_startup_cost": 0,
            "startup_fuel" : 0,
            "shutdown_cost": 0.0,
            "agc_capable": True, 
            "p_min_agc": gen_dict["p_min"], #default to the same as p_min
            "p_max_agc": gen_dict["p_max"], #default to the same as p_max
            "startup_capacity": gen_dict["p_min"], #default to the same as p_min
            "shutdown_capacity": gen_dict["p_min"], #default to the same as p_min
            "min_up_time": 1,
            "min_down_time": 1,
        }

        GTEP requires that p_fuel and p_cost are dictionaries with the following structure:
        p_fuel = {"data_type": "fuel_curve", "values": []}
        p_cost = {"data_type": "cost_data", "values": []}

        Note:
        # ROR is treated as HYDRO by Egret
        if UNIT_TYPE == "ROR":
            gen_dict["unit_type"] = "HYDRO"

        Suggested workflow example:
        
        RENEWABLE_TYPES = ["GEO", "PV", "WIND", "ROR", "HYDRO", "RTPV"]

        file_path = os.path.join(base_dir, "gen.csv")
        if os.path.exists(file_path):

            gen_df = pd.read_csv(file_path)

            for idx, row in gen_df.iterrows():

                name = str(row["GEN UID"])
                bus_name = str(row["Bus ID"])
                in_service_flag = True
                if "-c" in name:
                    in_service_flag = False
                gen_dict = {
                    "bus": bus_name,
                    "in_service": in_service_flag,
                    "mbase": 100.0,
                    "pg": float(row["MW Inj"]),
                    "qg": float(row["MVAR Inj"]),
                    "p_min": float(row["PMin MW"]),
                    "p_max": float(row["PMax MW"]),
                    "q_min": float(row["QMin MVAR"]),
                    "q_max": float(row["QMax MVAR"]),
                    "ramp_q": float(row["Ramp Rate MW/Min"]),
                    "fuel": str(row["Fuel"]),
                    "unit_type": str(row["Unit Type"]),
                    "area": elements["bus"][bus_name]["area"],
                    "zone": elements["bus"][bus_name]["zone"],
                    # extra
                    "investment_cost": float(row["capital_cost"]),
                }

                gen_dict["p_fuel"] = {}
                gen_dict["p_cost"] = {}

                UNIT_TYPE = str(row["Unit Type"])
                if UNIT_TYPE in RENEWABLE_TYPES:
                    gen_dict["generator_type"] = "renewable"
                    if p_fuel_df is not None:
                        gen_dict["p_fuel"] = {
                            "data_type": "fuel_curve",
                            "values": p_fuel_df.get(name, []),
                        }
                    # ROR is treated as HYDRO by Egret
                    if UNIT_TYPE == "ROR":
                        gen_dict["unit_type"] = "HYDRO"
                else:
                    gen_dict["generator_type"] = "thermal"
                    if p_cost_df is not None:
                        gen_name = name
                        if "-c" in name:
                            gen_name = name[:-2]
                        gen_dict["p_cost"] = {
                            "data_type": "cost_data",
                            "values": p_cost_df.get(gen_name, []),
                        }

                # set defaults
                gen_dict["spinning_reserve_frac"] = 0.1
                gen_dict["quickstart_reserve_frac"] = 0.1
                gen_dict["capital_multiplier"] = 1
                gen_dict["extension_multiplier"] = 0
                gen_dict["max_operating_reserve"] = 1
                gen_dict["max_spinning_reserve"] = 1
                gen_dict["max_quickstart_reserve"] = 1
                gen_dict["ramp_up_rate"] = 0.1
                gen_dict["ramp_down_rate"] = 0.1
                gen_dict["start_fuel"] = 1
                gen_dict["heat_rate"] = 1

                fixed_startup_cost = float(row["Non Fuel Start Cost $"])
                if not isnan(fixed_startup_cost):
                    gen_dict["non_fuel_startup_cost"] = fixed_startup_cost
                else:
                    gen_dict["non_fuel_startup_cost"] = 0

                elements["generator"][name] = gen_dict

                # after this is only really needed for thermal units
                if UNIT_TYPE in RENEWABLE_TYPES:
                    continue

                # Gen cost
                gen_dict["startup_fuel"] = [0]
                fixed_startup_cost = float(row["Non Fuel Start Cost $"])
                if not isnan(fixed_startup_cost):
                    gen_dict["non_fuel_startup_cost"] = fixed_startup_cost
                gen_dict["shutdown_cost"] = 0.0

                gen_dict["agc_capable"] = True
                gen_dict["p_min_agc"] = gen_dict["p_min"]
                gen_dict["p_max_agc"] = gen_dict["p_max"]

                ramp_q = gen_dict["ramp_q"]
                gen_dict["ramp_agc"] = ramp_q
                gen_dict["ramp_up_60min"] = ramp_q
                gen_dict["ramp_down_60min"] = ramp_q

                gen_dict["fuel_cost"] = float(row["Fuel Price $/MMBTU"])

                # these assumptions are the same as prescient-rtsgmlc
                gen_dict["startup_capacity"] = gen_dict["p_min"]
                gen_dict["shutdown_capacity"] = gen_dict["p_min"]
                gen_dict["min_up_time"] = 1
                gen_dict["min_down_time"] = 1

                elements["generator"][name] = gen_dict
        """
        pass

    @abstractmethod
    def _read_storage(self, base_dir: str, elements: dict[str, any]) -> None:
        """Read storage data."""
        """
        STORAGE DATA
        
        While you can add additional fields under each storage unit dictionary, 
        GTEP requires the following minimum key-value pairs:

        storage_dict = {
            "bus": row["bus"], #str
            "generator_type": row["generator"], #str
            "storage_type": row["storage_type"], #str
            "energy_capacity": row["energy_capacity"], #float
            "initial_state_of_charge": row["initial_state_of_charge"], #float
            "end_state_of_charge": row["end_state_of_charge"], #float
            "minimum_state_of_charge": row["minimum_state_of_charge"], #float
            "charge_efficiency": row["charge_efficiency"], #float
            "discharge_efficiency": row["discharge_efficiency"], #float
            "max_discharge_rate": row["max_discharge_rate"], #float
            "min_discharge_rate": row["min_discharge_rate"], #float
            "max_charge_rate": row["max_charge_rate"], #float
            "min_charge_rate": row["min_charge_rate"], #float
            "initial_charge_rate": row["initial_charge_rate"], #float
            "initial_discharge_rate": row["initial_discharge_rate"], #float
            "charge_cost": row["charge_cost"], #float
            "discharge_cost": row["discharge_cost"], #float
            "retention_rate_60min": row["retention_rate_60min"], #float
            "ramp_up_input_60min": row["ramp_up_input_60min"], #float
            "ramp_down_input_60min": row["ramp_down_input_60min"], #float
            "ramp_up_output_60min": row["ramp_up_output_60min"], #float
            "ramp_down_output_60min": row["ramp_down_output_60min"], #float
            "in_service": row["in_service"], #bool
            "capital_multiplier": 1,  # default value available
            "extension_multiplier": 1,  # default value available 
            "investment_cost": row["investment_cost"], #float
            "investment_cost_kwh": row["investment_cost_kwh"], #float
        }
        each storage unit is saved to the model elements as a storage name:
        elements["storage"][row["name"]] = storage_dict
        """
        pass

    @abstractmethod
    def _read_timeseries_data(
        self,
        system: dict[str, any],
        data_dir: str,
        start_time: datetime,
        end_time: datetime,
        minutes_per_period: int,
    ) -> list[str]:
        """Read and filter time-series keys.

        :return: Filtered list of time keys.
        :rtype: list[str]
        """
        """
        Take in time series data file for this data source to
        format into the system time key array.

        Suggested workflow example:
        
        time_series_df = pd.read_csv(os.path.join(data_dir, "time_series.csv"))
        time_series_df["datetime"] = pd.to_datetime(
            time_series_df[["Year", "Month", "Day", "Hour"]]
        )
        time_keys = []
        for idx, row in time_series_df.iterrows():
            # only append if it is within the target time range
            if start_time <= row["datetime"] <= end_time:
                time = f"{row['Year']}-{row['Month']:02d}-{row['Day']:02d} {row['Hour']:02d}:00"
                time_keys.append(time)

        system["time_keys"] = time_keys
        system["time_period_length_minutes"] = minutes_per_period

        return time_keys
        """
        pass

    def parse_to_cache(
        self,
        data_dir: str,
        begin_time: datetime,
        end_time: datetime,
    ) -> dict[str, any]:
        """Parse data in GTEP-friendly format.

        Only the portions between ``begin_time`` and ``end_time`` are retained.

        :param data_dir: Directory containing the NC data files.
        :type data_dir: str
        :param begin_time: Start of the desired time window.
        :type begin_time: datetime.datetime
        :param end_time: End of the desired time window.
        :type end_time: datetime.datetime
        :return: Parsed model data cache.
        :rtype: dict[str, Any]
        """

        # Create the skeleton with data
        model_data = self.create_skeleton(data_dir)

        # Save the data frequencies
        metadata_df = self._read_simulation_obj(data_dir)
        minutes_per_period = {
            "REAL TIME": int(metadata_df.loc["Period Resolution", "REAL TIME"]) // 60,
        }

        self._read_timeseries_data(
            model_data["system"], data_dir, begin_time, end_time, minutes_per_period
        )
        # add defaults
        model_data["system"]["min_operating_reserve"] = 0.1
        model_data["system"]["min_spinning_reserve"] = 0.1

        return model_data
