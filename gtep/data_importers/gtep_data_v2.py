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
# author: Kyle Skolfield
# date: 01/04/2024
# Model available at http://www.optimization-online.org/DB_FILE/2017/08/6162.pdf
import logging
from pathlib import Path
import csv
import pandas as pd
import os
import random
import importlib
import numpy as np

from prescient.simulator.config import PrescientConfig
from prescient.data.providers import gmlc_data_provider

logger = logging.getLogger("gtep.gtep_data")


SUPPORTED_IMPORTERS = {
    "prescient": "gtep.data_importers.prescient_importer:PrescientImporter",
    "ERCOT": "gtep.data_importers.ercot_importer:ERCOTimporter",
    "CAISO": "gtep.data_importers.caiso_importer:CAISOimporter",
}


class ExpansionPlanningData:
    """Standard data storage class for the IDAES GTEP model."""

    def __init__(
        self,
        stages=2,
        num_reps=4,
        num_commit=24,
        num_dispatch=1,
        duration_representative_period=24,
        save_period_structure_file=False,
        period_structure_json_file=None,
    ):
        """Initialize generation & expansion planning data object.

        :param: stages: integer number of investment periods
        :param: num_reps: integer number of representative periods per investment period
        :param: num_commit: integer number of commitment periods per representative period
        :param: num_dispatch: integer number of dispatch periods per commitment period
        :param: duration_representative_period: duration of each representative period
                (in hours)
        :param: save_period_structure_file: (optional) If True, saves the generated
                period structure as a JSON file in the data directory. Default is False.
        :param: period_structure_json_file: (optional) Path to a JSON file in the data
                directory specifying the period structure. Overrides scalar/list arguments
                if provided. Default is None.

        """
        self.stages = stages
        self.num_reps = num_reps
        self.num_commit = num_commit
        self.num_dispatch = num_dispatch
        self.duration_representative_period = duration_representative_period
        self.save_period_structure_file = save_period_structure_file
        self.period_structure_json_file = period_structure_json_file

    @staticmethod
    def _get_importer(label: str = "prescient"):
        try:
            module_path, class_name = SUPPORTED_IMPORTERS[label].split(":")
        except KeyError:
            raise ValueError(f"Unsupported importer label: {label}")

        module = importlib.import_module(module_path)
        importer_class = getattr(module, class_name)
        return importer_class

    def _configure_options(
        self,
        importer_class,
        data_path,
        start_date,
        options_dict=None,
    ):
        # set up options dictionary with default values
        if options_dict is None:
            options_dict = {}

        # Set basic configurations
        default_options_dict = {
            "num_days": 365,
            "ruc_horizon": 36,
            "data_path": data_path,
            "start_date": start_date,
        }
        for k, v in default_options_dict.items():
            if k not in options_dict:
                options_dict[k] = v

        if self.data_type.lower() == "prescient":
            return importer_class().configure_options(options_dict)
        else:
            # set default period steps
            for name, value in {"minutes_per_step": 60, "periods_per_step": 24}:
                if name not in options_dict:
                    options_dict[name] = value
            if "total_num_steps" not in options_dict.keys():
                options_dict["total_num_steps"] = (
                    options_dict["num_days"] * options_dict["periods_per_step"]
                )

        return options_dict

    def set_candidate_service_flag(self):
        for gen in self.md.data["elements"]["generator"]:
            if "-c" in gen:  # key/Gen UID in csv file; -c = candidate?
                self.md.data["elements"]["generator"][gen]["in_service"] = False

        # JSC addn
        for branch in self.md.data["elements"]["branch"]:
            if "-c" in branch:  # key/Branch UID
                self.md.data["elements"]["branch"][branch]["in_service"] = False

        for stor in self.md.data["elements"]["storage"]:
            if "-c" in stor:  # key/Branch UID
                self.md.data["elements"]["storage"][stor]["in_service"] = False

    def _set_representative_dates(self, representative_dates, period_per_step):
        # Get the timestamps in the loaded day-ahead data. Default
        # representative_dates are selected from this list to ensure
        # they correspond to valid input data timestamps. if
        # representative_dates are provided by the user, those values
        # are used instead.
        time_keys = self.md.data["system"]["time_keys"]

        if representative_dates is None:
            available_day_starts = time_keys[::period_per_step]

            if len(available_day_starts) < self.num_reps:
                raise ValueError(
                    "Not enough available day-start timestamps to select default representative dates. Please provide a custom list of representative_dates in the driver or reduce num_reps."
                )

            # Pick 4 default representative dates from the loaded
            # data: winter, spring, summer, and fall. If self.num_reps
            # < 4, use only the first self.num_reps default dates. If
            # more than 4 representative periods are requested, keep
            # these 4 defaults and randomly select the remaining dates
            # from the available day-start timestamps.
            default_representative_dates = [
                available_day_starts[27],  # 2020-01-28
                available_day_starts[113],  # 2020-04-23
                available_day_starts[186],  # 2020-07-05
                available_day_starts[287],  # 2020-10-14
            ]

            if self.num_reps <= 4:
                representative_dates = default_representative_dates[: self.num_reps + 1]
            else:
                if len(available_day_starts) < self.num_reps:
                    raise ValueError(
                        "Not enough available day-start timestamps to select default representative dates. "
                        "Please provide a custom list of representative_dates in the driver or reduce num_reps."
                    )

                random_seed = 42
                rng = random.Random(random_seed)
                remaining_dates = [
                    date
                    for date in available_day_starts
                    if date not in default_representative_dates
                ]
                additional_dates = rng.sample(
                    remaining_dates,
                    self.num_reps - len(default_representative_dates),
                )
                representative_dates = sorted(
                    default_representative_dates + additional_dates,
                    key=lambda date: time_keys.index(date),
                )
        else:
            # Validate that the user-provided representative_dates
            # match the requested number of representative periods.
            if len(representative_dates) != self.num_reps:
                raise ValueError(
                    f"The number of provided representative_dates must match num_reps. "
                    f"Received len(representative_dates)={len(representative_dates)}, "
                    f"but num_reps={self.num_reps}."
                )

            # Validate that all user-provided representative dates
            # exist in the loaded day-ahead timestamps.
            missing_dates = [
                date for date in representative_dates if date not in time_keys
            ]

            if missing_dates:
                raise ValueError(
                    "The following representative_dates are not valid timestamps in the "
                    f"loaded day-ahead input data: {missing_dates}"
                )

        self.representative_dates = representative_dates

    def _set_representative_weights(self, representative_weights, num_days):
        if representative_weights:

            if len(self.representative_dates) != len(representative_weights):
                raise ValueError(
                    (
                        f"Number of representative dates ({len(self.representative_dates)})"
                        + f" and representative_weights ({len(representative_weights)})"
                        + " must match."
                    )
                )

            missing_dates = [
                date
                for date in self.representative_dates
                if date not in representative_weights
            ]
            if missing_dates:
                raise ValueError(
                    (
                        "Every representative date must be a key in representative_weights,"
                        f" but {missing_dates} are missing."
                    )
                )

            total_weight = sum(representative_weights.values())
            if total_weight != 365:  # leap year...?
                raise ValueError(
                    "The values of representative_weights must sum to 365,"
                    + f" but got {total_weight}"
                )

            logger.info(
                (
                    "representative_dates and representative_weights are aligned. "
                    + "Continue building the data modeling object..."
                )
            )

            # Store as a dictionary
            self.representative_weights_dict = representative_weights

        else:

            # Set weight for each representative day to default value
            # of 1. The other option is to set the weight for each day
            # to the total weight divided by the number of
            # representative dates.
            set_default_weight = True
            if set_default_weight:
                weight_per_date = 1
            else:
                total_weight = num_days * self.stages
                weight_per_date = int(total_weight / len(self.representative_dates))

            # Store weights as a dictionary by representative date
            self.representative_weights_dict = {
                date: weight_per_date for date in self.representative_dates
            }

    def check_heat_rates(self, data_provider, data_path):
        data_provider.set_heat_rates(self.md, data_path)

        thermal_heat_rates = [
            self.md.data["elements"]["generator"][gen].get("heat_rate", 0)
            for gen in self.md.data["elements"]["generator"]
            if self.md.data["elements"]["generator"][gen].get("generator_type")
            == "thermal"
        ]

        if thermal_heat_rates and all(hr == 0 for hr in thermal_heat_rates):
            logger.info(
                "All thermal generators have heat_rate values equal to 0. "
                "Please re-check the input data. Fuel costs are multiplied by "
                "heat_rate, so resulting fuel costs will all be 0."
            )

    def load_data(
        self,
        data_path: Path | str,
        representative_dates: list[str] | None = None,
        representative_weights: dict | None = None,
        options_dict: dict | None = None,
        start_date=None,
        importer_type: str = "prescient",
    ):
        self.data_type = importer_type

        # If start_date is not provided, ideally this would be set from the start of the data_files,
        # the importer will also get the start date of the data. This is a way of cropping the data
        # to a user-configured start. If prescient importer, this will be taken from simulations_objects.csv.
        # custom importers will just assign by the start of the data
        if start_date is None:
            pass

        # grab requested importer options and class
        importer_class = self._get_importer(importer_type)
        options = self._configure_options(
            importer_class,
            data_path,
            start_date,
            options_dict,
        )

        # initialize importer instance
        data_provider = importer_class(options=options)

        # Populate an egret model data with the basic stuff
        self.md = data_provider.populate_model(
            options=options,
        )
        # Populate model with actuals
        data_provider.populate_with_actuals(
            options=options,
            model=self.md,
        )

        self.load_default_data_settings()

        if self.data_type == "prescient":
            data_provider.load_storage_csv(data_path, self.md)

        self.set_candidate_service_flag()

        self._set_representative_dates(
            representative_dates, data_provider.periods_per_step
        )
        self._set_representative_weights(representative_weights, data_provider.num_days)

        self.check_heat_rates(data_provider, data_path)

        # IMPORTANT TO READ: Always add or modify any new elements in
        # self.md.data (such as new time series or parameters) BEFORE
        # creating representative_data using clone_at_time_keys. This
        # ensures all representative ModelData objects will have the
        # new elements.
        data_list = []
        time_keys = self.md.data["system"]["time_keys"]
        for date in self.representative_dates:
            key_idx = time_keys.index(date)
            time_key_set = time_keys[key_idx : key_idx + data_provider.period_per_step]
            data_list.append(self.md.clone_at_time_keys(time_key_set))

        self.representative_data = data_list

    # WAYS OF ALTERING DATA
    def import_load_scaling(self, load_file_name, forecast_years=None):
        """Imports load scaling data for forecast years.

        :param load_file_name: filepath for adjusted forecast excel file
        :param forecast_years: list of years to forecast, defaults to [2025, 2030, 2035]

        """
        adjusted_forecast = pd.read_excel(load_file_name)

        if forecast_years is None:
            forecast_years = [2025, 2030, 2035]

        # check years are valid
        if len(forecast_years) < self.stages:
            raise ValueError(
                "Not enough forecast years for the number of stages of investment"
            )
        elif any(year < 2020 or year > 2050 for year in forecast_years):
            raise ValueError(
                "The list of years includes a year before 2020 or after 2050."
            )

        adjusted_forecast_by_period = adjusted_forecast[
            adjusted_forecast["year"].isin(forecast_years)
        ].copy()

        base_zones = [
            "base_economic_coast",
            "base_economic_east",
            "base_economic_fwest",
            "base_economic_ncent",
            "base_economic_north",
            "base_economic_scent",
            "base_economic_south",
            "base_economic_west",
        ]
        scaled_zones = [
            "coast_net",
            "east_net",
            "fwest_net",
            "ncent_net",
            "north_net",
            "scent_net",
            "south_net",
            "west_net",
        ]
        # zones = ["coast", "east", "fwest", "ncent", "north", "scent", "south", "west"]
        # cap_zones = [zone.upper() for zone in zones]
        zones = ["1", "2", "3", "4", "5", "6", "7", "8"]
        cap_zones = ["1", "2", "3", "4", "5", "6", "7", "8"]
        for i, zone in enumerate(zones):
            adjusted_forecast_by_period["scaled_" + zone] = (
                adjusted_forecast_by_period[scaled_zones[i]]
                / adjusted_forecast_by_period[base_zones[i]]
            )
        column_list = [
            "year",
            "month",
            "day",
            "hour",
            "scaled_1",
            "scaled_2",
            "scaled_3",
            "scaled_4",
            "scaled_5",
            "scaled_6",
            "scaled_7",
            "scaled_8",
        ]
        load_scaling_df = adjusted_forecast_by_period[column_list]
        scaled_names = ["scaled_" + zone for zone in zones]
        name_conversion_dict = dict(zip(scaled_names, cap_zones))
        load_scaling_df = load_scaling_df.rename(columns=name_conversion_dict)
        self.load_scaling = load_scaling_df

    def import_outage_data(self, load_file_name, save_mapped_outage_csv=False):
        """This method imports outage data and maps high-probability
        outages to buses.

        :param load_file_name:         Path to the outage data CSV file.
        :param save_mapped_outage_csv: If True, save the mapped
                                       outage-to-bus records to a CSV
                                       file for inspection.  Defaults
                                       to False.

        """

        # Read the outage probability data from the input CSV file.
        outage_list = pd.read_csv(load_file_name)

        # Select the percentile threshold used to identify
        # high-probability outage events and calculate the outage
        # probability value at that percentile.
        percentile_threshold = 0.9
        threshold_value = outage_list["case_4b_prob"].quantile(percentile_threshold)

        # Keep outage events with probability greater than or equal to
        # the threshold and extract the hour from the timestamp
        # string. Keep only the county FIPS code and extracted hour.
        filtered_outages = outage_list[
            outage_list["case_4b_prob"] >= threshold_value
        ].copy()
        filtered_outages["hour"] = filtered_outages["lim_timestamp"].str.extract(
            r" (\d+):"
        )
        filtered_outages = filtered_outages[["fips_code", "hour"]]

        # Use the directory containing the outage file as the base
        # directory and define paths to the county-to-FIPS and
        # bus-to-county mapping files.
        base_dir = Path(load_file_name).parent
        county_fips_path = base_dir / "county_fips_match.csv"
        bus_to_county_path = base_dir / "Bus_data_gen_weights_mappings.csv"
        county_to_fips = pd.read_csv(county_fips_path)
        bus_to_county = pd.read_csv(bus_to_county_path)

        # Keep the columns needed for mapping counties to FIPS codes
        # and buses to counties. Also, add FIPS codes to the
        # bus-to-county mapping.
        county_to_fips = county_to_fips[["County", "FIPS"]]
        bus_to_county = bus_to_county[["Bus Number", "County"]]
        bus_to_county = bus_to_county.merge(county_to_fips, how="inner", on="County")

        # Map outage FIPS codes to buses using the FIPS code and
        # remove outage records that could not be mapped to a bus.
        bus_hours = pd.merge(
            filtered_outages,
            bus_to_county,
            left_on="fips_code",
            right_on="FIPS",
            how="left",
        )
        bus_hours = bus_hours[bus_hours["Bus Number"].notna()]

        # Optionally save the mapped outage records to a new CSV file.
        if save_mapped_outage_csv:
            csv_path = base_dir / "mapped_outage_bus_hours.csv"
            bus_hours.to_csv(csv_path, index=False)

        # Store the hour and bus number columns and convert them to
        # integers.
        self.bus_hours = bus_hours[["hour", "Bus Number"]]
        self.bus_hours = self.bus_hours.astype(int)

    def load_default_data_settings(self):
        """This method fills in required data fields that are not
        specified in the inputs.

        Many of these values are currently hard-coded because they are
        not set elsewhere in the workflow.

        """

        if "elements" in self.md.data.keys():
            if "generator" in self.md.data["elements"].keys():
                for gen in self.md.data["elements"]["generator"]:

                    # Set lifetime value to default first
                    self.md.data["elements"]["generator"][gen]["lifetime"] = 3

                    if "fuel" in self.md.data["elements"]["generator"][gen].keys():
                        if self.md.data["elements"]["generator"][gen]["fuel"] == "C":
                            if (
                                self.md.data["elements"]["generator"][gen]["in_service"]
                                == False
                            ):
                                self.md.data["elements"]["generator"][gen][
                                    "lifetime"
                                ] = 1
                            else:
                                self.md.data["elements"]["generator"][gen][
                                    "lifetime"
                                ] = 2

                    self.md.data["elements"]["generator"][gen][
                        "spinning_reserve_frac"
                    ] = 0.1
                    self.md.data["elements"]["generator"][gen][
                        "quickstart_reserve_frac"
                    ] = 0.1
                    self.md.data["elements"]["generator"][gen]["capital_multiplier"] = 1
                    self.md.data["elements"]["generator"][gen][
                        "extension_multiplier"
                    ] = 0
                    self.md.data["elements"]["generator"][gen][
                        "max_operating_reserve"
                    ] = 1
                    self.md.data["elements"]["generator"][gen][
                        "max_spinning_reserve"
                    ] = 1
                    self.md.data["elements"]["generator"][gen][
                        "max_quickstart_reserve"
                    ] = 1
                    self.md.data["elements"]["generator"][gen]["ramp_up_rate"] = 0.1
                    self.md.data["elements"]["generator"][gen]["ramp_down_rate"] = 0.1
                    self.md.data["elements"]["generator"][gen]["emissions_factor"] = 1
                    self.md.data["elements"]["generator"][gen]["start_fuel"] = 1
                    self.md.data["elements"]["generator"][gen]["investment_cost"] = 1
                    self.md.data["elements"]["generator"][gen].setdefault(
                        "non_fuel_startup_cost", 0
                    )

            if "branch" in self.md.data["elements"].keys():
                for branch in self.md.data["elements"]["branch"]:
                    self.md.data["elements"]["branch"][branch]["loss_rate"] = 0
                    self.md.data["elements"]["branch"][branch]["distance"] = 1
                    self.md.data["elements"]["branch"][branch][
                        "capital_cost"
                    ] = 10000000

        if "system" in self.md.data.keys():
            self.md.data["system"]["min_operating_reserve"] = 0.1
            self.md.data["system"]["min_spinning_reserve"] = 0.1

    def texas_case_study_updates(self, data_path):
        """Imports generator data for texas case study.

        :param data_path: filepath for generator data csv file
        """

        # Check that datapath is coming from a texas case study
        # directory
        if (
            ("Texas" not in str(data_path))
            and ("Coal" not in str(data_path))
            and ("Resil_Week" not in str(data_path))
        ):
            raise ValueError("The data path provided is not a Texas case study")

        # Enforce pathlib object
        if not isinstance(data_path, Path):
            data_path = Path(data_path)

        generator_update_path = data_path / "gen.csv"
        generator_df = pd.read_csv(generator_update_path)
        bonus_feature_list = [
            "capex1",
            "capex2",
            "capex3",
            "fuel_cost1",
            "fuel_cost2",
            "fuel_cost3",
            "fixed_ops1",
            "fixed_ops2",
            "fixed_ops3",
            "var_ops1",
            "var_ops2",
            "var_ops3",
        ]
        for data_point in self.representative_data:
            for col in bonus_feature_list:
                for gen in data_point.data["elements"]["generator"]:
                    if not data_point.data["elements"]["generator"][gen].get(col):
                        matching_rows = generator_df[generator_df["GEN UID"] == gen]
                        if not matching_rows.empty:
                            data_point.data["elements"]["generator"][gen][col] = float(
                                matching_rows[col].iloc[0]
                            )

    def scale_load_by_region(self, region_dict: dict[str, float]) -> None:
        """
        Scale the load of every bus in a region by a set percentage.

        :param region_dict: Mapping of region name to scaling factor.
        :type region_dict: dict[str, float]
        :returns: None
        :rtype: None
        """
        # grab relevant data pieces
        areas = self.md["elements"]["area"]
        loads = self.md["elements"]["load"]
        # iterate through regions in input
        for region, val in region_dict.items():
            # check that the region is one of the accepted regions
            if region not in areas:
                print(f"{region} not in matching region list for the data. Skipping")
                continue
            # iterate through load buses
            for load_dict in loads.values():
                # check that the region matches this load bus area
                if region == load_dict["area"]:
                    # convert load values to numpy array
                    load_vals = np.array(load_dict["p_load"]["values"])
                    # scale by region amount
                    load_vals_scaled = load_vals * val
                    # reassign the scaled version to the bus load values
                    load_dict["p_load"]["values"] = list(load_vals_scaled)

    def scale_load_by_bus(
        self, bus_dict: dict[str, float | list[float]], add_new_bus: bool = True
    ) -> None:
        """
        Scale the loads of a bus.

        :param bus_dict: Mapping of bus name to either a scalar value to add
                        or a list of load values.
        :type bus_dict: dict[str, float | list[float]]
        :param add_new_bus: If True, create a new load entry for a matching bus
                            that does not already have load data.
        :type add_new_bus: bool
        :returns: None
        :rtype: None
        """
        loads = self.md["elements"]["load"]
        buses = self.md["elements"]["bus"]

        for bus_name, val in bus_dict.items():
            if bus_name not in loads.keys():
                if add_new_bus:
                    if bus_name not in buses.keys():
                        logger.info(
                            f"{bus_name} not in loads or full bus list. Skipping"
                        )
                        print(f"{bus_name} not in loads or full bus list. Skipping")
                        continue
                    else:
                        # add a new load bus
                        # if value is a single item
                        if isinstance(val, float):
                            # get an idea of the number of p_load values we need
                            first_key = next(iter(loads))
                            num_load_vals = len(loads[first_key]["p_load"]["values"])
                            # get a full list of new values
                            new_vals = [val] * num_load_vals
                        else:
                            new_vals = val
                        load_dict = {
                            "bus": bus_name,
                            "in_service": True,
                            "p_load": {"data_type": "time_series", "values": new_vals},
                            "q_load": {},
                            "area": buses[bus_name]["area"],
                            "zone": buses[bus_name]["zone"],
                        }
                        self.md["elements"]["load"][bus_name] = load_dict
                logger.info(f"{bus_name} not in loads. Skipping")
                print(f"{bus_name} not in loads. Skipping")
                continue
            else:
                load_vals = np.array(loads[bus_name]["p_load"]["values"])
                load_vals_scaled = load_vals + val
                loads[bus_name]["p_load"]["values"] = load_vals_scaled

    def replace_load_by_bus(self, bus_dict: dict[str, list[float]]) -> None:
        """
        Replace the loads of a bus.

        :param bus_dict: Mapping of bus name to the new list of load values.
        :type bus_dict: dict[str, list[float]]
        :returns: None
        :rtype: None
        """
        loads = self.md["elements"]["load"]

        for bus_name, val in bus_dict.items():
            if bus_name not in loads.keys():
                logger.info(f"{bus_name} not in loads. Skipping")
                print(f"{bus_name} not in loads. Skipping")
                continue
            loads[bus_name]["p_load"]["values"] = val

    def scale_reactance(
        self,
        func: callable,
        lines: dict[str, float],
        **kwargs,
    ) -> None:
        """
        Scale the reactance of lines based on the distance between line end points.

        :param func: Function used to apply the scaling.
        :type func: Callable[..., float]
        :param lines: Mapping of branch name to scaling value.
        :type lines: dict[str, float]
        :param kwargs: Additional keyword arguments passed to ``func``.
        :returns: None
        :rtype: None
        """
        branch = self.md["elements"]["branch"]
        # iterate through target lines to apply scaling function
        for line, val in lines.items():
            if line not in branch.keys():
                logger.info(
                    f"{line} is not matching any of the existing branches. Skipping"
                )
                print(f"{line} is not matching any of the existing branches. Skipping")
                continue
            branch[line]["reactance"] = func(
                reactance=branch[line]["reactance"],
                distance=branch[line]["distance"],
                value=val**kwargs,
            )

    def scale_line_capacity_by_region(self, region_dict: dict[str, float]) -> None:
        """
        Scale the capacity of the branch by the from-bus region.

        :param region_dict: Mapping of region name to capacity scaling value.
        :type region_dict: dict[str, float]
        :returns: None
        :rtype: None
        """
        branch = self.md["elements"]["branch"]
        # iterate through target regions to apply scaling function
        for region, val in region_dict.items():
            for br_data in branch.items():
                if region in br_data["from_bus"]:
                    # add scaling value to this branch's value
                    br_data["rating_long_term"] += val

    def change_generation(self, func: callable, gen_type: str, **kwargs) -> None:
        """
        Change generation values for generators of a given type.

        :param func: Function used to transform generator values.
        :type func: Callable[..., float]
        :param gen_type: Generator type to modify. Should be 'thermal' or 'renewable'
        :type gen_type: str
        :param kwargs: Additional keyword arguments passed to ``func``.
        :returns: None
        :rtype: None
        """
        gens = self.md["elements"]["generator"]
        for g_data in gens.values():
            if g_data["generator_type"] == gen_type:
                g_data["p_max"] = func(
                    gen_val=g_data["p_max"], **kwargs
                )  # renewables should be time series
