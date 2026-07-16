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

"""NC data provider.

This module provides a parser for NC-converted RTS-GMLC-like data files and
converts them into an internal model data structure.

:module: nc_data_provider
:author: BStorm
"""

import egret.data.model_data as md
from datetime import datetime, timedelta
import os
import pandas as pd
import numpy as np
from math import isnan


class NCDataProvider:
    """Provides data for RTS-GMLC-like NC files that have been converted into CSV's.

    :param options: Configuration options used to locate and parse the data.
    :type options: dict[str, Any] | None
    :raises ValueError: If the data directory does not exist.
    """

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

    def _read_simulation_obj(self, dir: str) -> pd.DataFrame:
        """Read simulation object metadata.

        :param dir: Directory containing ``simulation_objects.csv``.
        :type dir: str
        :return: Simulation object metadata.
        :rtype: pandas.DataFrame
        """

        file_path = os.path.join(dir, "simulation_objects.csv")
        if not os.path.exists(file_path):
            raise ValueError(f'NC Data File "{file_path}" does not exist')
        sim_df = pd.read_csv(file_path)
        sim_df = sim_df.set_index("Parameters")

        return sim_df

    def _get_data_date_range(
        self, metadata_df: pd.DataFrame
    ) -> tuple[datetime, datetime]:
        """Get the start and end datetimes from metadata.

        :param metadata_df: Metadata dataframe.
        :type metadata_df: pandas.DataFrame
        :return: Start and end datetimes.
        :rtype: tuple[datetime, datetime]
        """
        data_start = pd.to_datetime(metadata_df.loc["Date_From", "REAL TIME"])
        data_end = pd.to_datetime(metadata_df.loc["Date_To", "REAL TIME"])

        return data_start, data_end

    def create_skeleton(self) -> dict[str, any]:
        """Create an empty model data skeleton.

        :return: Empty model data dictionary.
        :rtype: dict[str, Any]
        """
        model_data = md.ModelData.empty_model_data_dict()
        elements = model_data["elements"]
        system = model_data["system"]

        self._build_elements(elements)
        self._build_system(system)

        return model_data

    def _build_system(self, system: dict[str, any]) -> None:
        """Populate the system section of the skeleton."""
        system["name"] = "NC"
        system["baseMVA"] = None
        system["reference_bus"] = None
        system["reference_bus_angle"] = None
        system["time_period_length_minutes"] = None
        system["time_keys"] = []
        system["min_operating_reserve"] = None
        system["min_spinning_reserve"] = None

    def _build_elements(self, elements: dict[str, any]) -> None:
        """Populate the elements section of the skeleton."""
        elements["bus"] = {}
        elements["load"] = {}
        elements["shunt"] = {}

        elements["branch"] = {}
        elements["dc_branch"] = {}

        elements["generator"] = {}

        elements["storage"] = {}

    def _create_nc_skeleton(self, data_dir: str) -> dict[str, any]:
        """Create a populated NC model skeleton."""
        model_data = self.create_skeleton()

        system = model_data["system"]
        system["name"] = "nc_data"

        elements = model_data["elements"]
        system = model_data["system"]

        self._read_buses(data_dir, elements, system)
        self._read_branches(data_dir, elements)
        self._read_generators(data_dir, elements)
        self._read_storage(data_dir, elements)

        return model_data

    def _read_buses(
        self, base_dir: str, elements: dict[str, any], system: dict[str, any]
    ) -> None:
        """Read bus and load data."""
        bus_areas = set()
        file_path = os.path.join(base_dir, "bus.csv")
        if not os.path.exists(file_path):
            raise ValueError(f'NC Data File "{file_path}" does not exist')
        bus_df = pd.read_csv(file_path)

        for idx, row in bus_df.iterrows():

            bus_name = str(row["Bus Name"])
            area = row["area"]
            if np.isnan(area):
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
                "x": float(row["x"]),
                "y": float(row["y"]),
                "sub_network": float(row["sub_network"]),
                "substation_lv": float(row["substation_lv"]),
                "substation_off": float(row["substation_off"]),
            }

            if bus_dict["base_kv"] <= 0:
                raise ValueError(
                    f'BaseKV value for bus "{bus_name}" is <= 0. Not supported.'
                )

            bus_areas.add(bus_dict["area"])
            elements["bus"][bus_name] = bus_dict

        # add loads to elements
        load_file = os.path.join(base_dir, "bus_load.csv")
        p_load_file = os.path.join(base_dir, "p_load.csv")
        q_load_file = os.path.join(base_dir, "q_load.csv")

        if os.path.exists(load_file):
            load_df = pd.read_csv(load_file)

            p_load_df = None
            q_load_df = None
            if os.path.exists(p_load_file):
                p_load_df = pd.read_csv(p_load_file)
            if os.path.exists(q_load_file):
                q_load_df = pd.read_csv(q_load_file)

            for idx, row in load_df.iterrows():
                bus_name = str(row["bus"])
                area = row["area"]
                if np.isnan(area):
                    area = bus_name.split(' ')[0]
                    bus_areas.add(area) #make sure this is in the areas list
                # format load dictionaries
                PD = {}
                QD = {}
                if p_load_df is not None:
                    PD = {"data_type": "time_series", "values": p_load_df[bus_name]}
                if q_load_df is not None:
                    QD = {"data_type": "time_series", "values": q_load_df[bus_name]}

                load_dict = {
                    "bus": bus_name,
                    "in_service": row["in_service"],
                    "p_load": PD,
                    "q_load": QD,
                    "area": area,
                    "zone": row["zone"],
                }
                elements["load"][bus_name] = load_dict

        # add filler valyes for reference buses
        system["reference_bus"] = None
        system["reference_bus_angle"] = 0

        # add the areas
        elements["area"] = {name: dict() for name in bus_areas}

    def _read_branches(self, base_dir: str, elements: dict[str, any]) -> None:
        """Read AC and DC branch data."""
        file_path = os.path.join(base_dir, "branch.csv")
        if not os.path.exists(file_path):
            raise ValueError(f'NC Data File "{file_path}" does not exist')
        branch_df = pd.read_csv(file_path)

        for idx, row in branch_df.iterrows():

            branch_dict = {
                "from_bus": str(row["From Bus"]),
                "to_bus": str(row["To Bus"]),
                "in_service": True,
                "resistance": float(row["R"]),
                "reactance": float(row["X"]),
                "charging_susceptance": float(row["B"]),
                "rating_long_term": float(row["LTE Rating"]),
                "rating_short_term": float(row["STE Rating"]),
                "rating_emergency": float(row["Cont Rating"]),
                "angle_diff_min": -90,
                "angle_diff_max": 90,
                "pf": None,
                "qf": None,
                "pt": None,
                "qt": None,
                "branch_type": "line",
                "capital_cost": float(row["capital_cost"]),
                "distance": float(row["length"]),
                "loss_rate": float(row["loss_rate"]),
                # extra columns
                "carrier": str(row["Carrier"]),
                "s_max_pu": float(row["s_max_pu"]),
                "num_parallel": float(row["num_parallel"]),
                "sub_network": float(row["sub_network"]),
                "v_nom": float(row["v_nom"]),
                "i_nom": float(row["i_nom"]),
            }

            name = str(row["UID"])
            elements["branch"][name] = branch_dict

        # add the DC branches
        if os.path.exists(os.path.join(base_dir, "dc_branch.csv")):
            dc_branch_df = pd.read_csv(os.path.join(base_dir, "dc_branch.csv"))

            for idx, row in dc_branch_df.iterrows():
                dc_branch_dict = {
                    "from_bus": str(row["From Bus"]),
                    "to_bus": str(row["To Bus"]),
                    "rating_long_term": float(row["LTE Rating"]),
                    "rating_short_term": float(row["STE Rating"]),
                    "rating_emergency": float(row["Cont Rating"]),
                    "capital_cost": str(row["capital_cost"]),
                    "distance": str(row["length"]),
                    "loss_rate": float(row["loss_rate"]),
                    # extra columns
                    "carrier": str(row["Carrier"]),
                    "lifetime": str(row["lifetime"]),
                    "underground": str(row["underground"]),
                    "under_construction": bool(row["under_construction"]),
                    "tags": row["tags"],
                    "geometry": row["geometry"],
                    "underwater_fraction": float(row["underwater_fraction"]),
                    "p_nom_extendable": bool(row["p_nom_extendable"]),
                    "p_min_pu": float(row["p_min_pu"]),
                }
                name = str(row["UID"])
                elements["dc_branch"][name] = dc_branch_dict

    def _read_generators(self, base_dir: str, elements: dict[str, any]) -> None:
        """Read generator data."""
        RENEWABLE_TYPES = ["GEO", "PV", "WIND", "ROR", "HYDRO", "RTPV"]

        file_path = os.path.join(base_dir, "gen.csv")
        p_fuel_file = os.path.join(base_dir, "p_fuel.csv")
        p_cost_file = os.path.join(base_dir, "p_cost.csv")
        if os.path.exists(file_path):

            gen_df = pd.read_csv(file_path)

            p_fuel_df = None
            p_cost_df = None
            if os.path.exists(file_path):
                p_fuel_df = pd.read_csv(p_fuel_file)
            if os.path.exists(file_path):
                p_cost_df = pd.read_csv(p_cost_file)

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
                    "emissions_factor": float(row["emissions_factor"]),
                    "lifetime": float(row["lifetime"]),
                    "efficiency": float(row["efficiency"]),
                    "weight": row["weight"],
                    "p_nom_min": float(row["p_nom_min"]),
                    "p_nom_max": row["p_nom_max"],
                    "p_max_pu": float(row["p_max_pu"]),
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

    def _read_storage(self, base_dir: str, elements: dict[str, any]) -> None:
        """Read storage data."""
        file_path = os.path.join(base_dir, "storage.csv")
        if not os.path.exists(file_path):
            raise ValueError(f'NC Data File "{file_path}" does not exist')
        store_df = pd.read_csv(file_path)

        for idx, row in store_df.iterrows():

            storage_dict = {
                "bus": row["bus"],
                "generator_type": row["generator"],
                "storage_type": row["storage_type"],
                "energy_capacity": row["energy_capacity"],
                "initial_state_of_charge": row["initial_state_of_charge"],
                "end_state_of_charge": row["end_state_of_charge"],
                "minimum_state_of_charge": row["minimum_state_of_charge"],
                "charge_efficiency": row["charge_efficiency"],
                "discharge_efficiency": row["discharge_efficiency"],
                "max_discharge_rate": row["max_discharge_rate"],
                "min_discharge_rate": row["min_discharge_rate"],
                "max_charge_rate": row["max_charge_rate"],
                "min_charge_rate": row["min_charge_rate"],
                "initial_charge_rate": row["initial_charge_rate"],
                "initial_discharge_rate": row["initial_discharge_rate"],
                "charge_cost": row["charge_cost"],
                "discharge_cost": row["discharge_cost"],
                "retention_rate_60min": row["retention_rate_60min"],
                "ramp_up_input_60min": row["ramp_up_input_60min"],
                "ramp_down_input_60min": row["ramp_down_input_60min"],
                "ramp_up_output_60min": row["ramp_up_output_60min"],
                "ramp_down_output_60min": row["ramp_down_output_60min"],
                "in_service": row["in_service"],
                "capital_multiplier": 1,  # default value for now
                "extension_multiplier": 1,  # default value for now
                "investment_cost": row["investment_cost"],
                "investment_cost_kwh": row["investment_cost_kwh"],
            }
            if "hydro" in row["name"]:
                continue
            else:
                elements["storage"][row["name"]] = storage_dict

    def _read_timeseries_data(
        self,
        system: dict[str, any],
        nc_data_dir: str,
        start_time: datetime,
        end_time: datetime,
        minutes_per_period: int,
    ) -> list[str]:
        """Read and filter time-series keys.

        :return: Filtered list of time keys.
        :rtype: list[str]
        """
        time_series_df = pd.read_csv(os.path.join(nc_data_dir, "time_series.csv"))
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

    def parse_to_cache(
        self,
        nc_data_dir: str,
        begin_time: datetime,
        end_time: datetime,
    ) -> dict[str, any]:
        """Parse data in NC-converted format.

        Only the portions between ``begin_time`` and ``end_time`` are retained.

        :param nc_data_dir: Directory containing the NC data files.
        :type nc_data_dir: str
        :param begin_time: Start of the desired time window.
        :type begin_time: datetime.datetime
        :param end_time: End of the desired time window.
        :type end_time: datetime.datetime
        :return: Parsed model data cache.
        :rtype: dict[str, Any]
        """

        # Create the skeleton with data
        model_data = self._create_nc_skeleton(nc_data_dir)

        # Save the data frequencies
        metadata_df = self._read_simulation_obj(nc_data_dir)
        minutes_per_period = {
            "REAL TIME": int(metadata_df.loc["Period Resolution", "REAL TIME"]) // 60,
        }

        # TODO maybe check if start and end are within the data start and data end

        self._read_timeseries_data(
            model_data["system"], nc_data_dir, begin_time, end_time, minutes_per_period
        )
        # add defaults
        model_data["system"]["min_operating_reserve"] = 0.1
        model_data["system"]["min_spinning_reserve"] = 0.1

        return model_data
