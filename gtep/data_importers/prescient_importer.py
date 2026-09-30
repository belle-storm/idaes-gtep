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

from prescient.simulator.config import PrescientConfig
from prescient.data.providers import gmlc_data_provider

logger = logging.getLogger("gtep.gtep_data")


class PrescientImporter:
    """Standard data storage class for the IDAES GTEP model."""

    def __init__(self, options):
        self.prescient_provider = gmlc_data_provider.GmlcDataProvider(options=options)
        return self.prescient_provider

    @staticmethod
    def configure_options(options_dict=None):
        # Create prescient config object with defaults
        prescient_options = PrescientConfig()

        # If start_date is not provided, read it from
        # simulation_objects.csv using Date_From and DAY_AHEAD. Also,
        # verify that the start date year matches the DAY_AHEAD
        # time-series data.
        if options_dict["start_date"] is None:
            options_dict[
                "start_date"
            ] = PrescientImporter().get_start_date_from_simulation_objects(
                options_dict["data_path"]
            )
            PrescientImporter().assert_start_date_matches_day_ahead_files(
                options_dict["data_path"], options_dict["start_date"]
            )

        # Update configuration values based on options dictionary
        prescient_options.set_value(options_dict)

        # Validate required input columns before calling Prescient to
        # provide clearer error messages to avoid parser failures.
        PrescientImporter().validate_required_columns(
            options_dict["data_path"], "gen.csv"
        )
        PrescientImporter().validate_required_columns(
            options_dict["data_path"], "bus.csv"
        )
        PrescientImporter().validate_required_columns(
            options_dict["data_path"], "branch.csv"
        )

        return prescient_options

    def populate_model(self, options):
        # Grab details from simulation objects file (data provider
        # above throws error if no simulation_objects.csv exists)
        metadata_path = os.path.join(options.data_path, "simulation_objects.csv")
        metadata_df = pd.read_csv(metadata_path, index_col=0)

        # Save to variable for easy calling
        sced_freq_min = options.sced_frequency_minutes

        # This step is grabbing DAY_AHEAD information for now (in the
        # future we may want to update to grab the "REAL_TIME" data if
        # the data has reliable data since the actuals model is
        # looking for real time data info)
        self.period_per_step = int(metadata_df.loc["Periods_per_Step"]["DAY_AHEAD"])
        self.total_num_steps = options.num_days * self.period_per_step
        self.num_days = options.num_days

        return self.prescient_provider.get_initial_actuals_model(
            options=options,
            num_time_steps=self.total_num_steps,
            minutes_per_timestep=sced_freq_min,
        )

    def populate_with_actuals(
        self,
        options,
        model,
    ):
        self.prescient_provider.populate_with_actuals(
            options=options,
            num_time_periods=self.total_num_steps,
            time_period_length_minutes=options.sced_frequency_minutes,
            start_time=self.prescient_provider._start_time,
            model=model,
        )

    def set_heat_rates(model, data_path):
        # Read average heat rates from the "HR_avg_0" column in
        # gen.csv and assign them to each generator in self.md. This
        # is done manually because the generator data loaded into
        # self.md does not include heat rate values by default. Units
        # should be in MMBTU/MWh.
        gen_csv_file = os.path.join(data_path, "gen.csv")
        heat_rate_dict = {}
        with open(gen_csv_file, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                gen_uid = row.get("GEN UID")
                heat_rate_str = row.get("HR_avg_0")

                if heat_rate_str not in (None, "", "NA"):
                    heat_rate = float(heat_rate_str)
                else:
                    heat_rate = None

                if gen_uid and heat_rate is not None:
                    heat_rate_dict[gen_uid] = heat_rate

        for gen in model.data["elements"]["generator"]:
            if gen in heat_rate_dict:
                model.data["elements"]["generator"][gen]["heat_rate"] = heat_rate_dict[
                    gen
                ]
            else:
                model.data["elements"]["generator"][gen]["heat_rate"] = 0

    def get_start_date_from_simulation_objects(self, data_path):
        """This method reads the start date from the
        simulation_objects.csv.

        """

        simulation_objects_file = os.path.join(data_path, "simulation_objects.csv")

        if not os.path.exists(simulation_objects_file):
            return None

        simulation_objects_df = pd.read_csv(simulation_objects_file)

        date_from_row = simulation_objects_df[
            simulation_objects_df["Simulation_Parameters"] == "Date_From"
        ]

        if date_from_row.empty:
            return None

        return str(date_from_row["DAY_AHEAD"].iloc[0]).split()[0]

    @staticmethod
    def assert_start_date_matches_day_ahead_files(data_path, start_date):
        """This method checks that the year in start_date matches
        DAY_AHEAD time-series files.

        """

        if start_date is None:
            return

        start_year = pd.to_datetime(start_date).year

        day_ahead_files = [
            "DAY_AHEAD_load.csv",
            "DAY_AHEAD_renewables.csv",
        ]

        for filename in day_ahead_files:
            file_path = os.path.join(data_path, filename)

            if not os.path.exists(file_path):
                continue

            df = pd.read_csv(file_path, usecols=["Year"])
            file_year = int(df["Year"].dropna().iloc[0])

            # Handle possible two-digit years, example 19 to
            # convert to 2019
            if file_year < 100:
                file_year += 2000

            assert file_year == start_year, (
                f"Start date year ({start_year}) does not match the "
                f"first year in {filename} ({file_year}). Please check "
                "simulation_objects.csv and DAY_AHEAD time-series files."
            )

    @staticmethod
    def get_required_columns_from_file(requirements_file, target_file):
        """This method reads required columns for a target input file."""
        required_files_df = pd.read_csv(requirements_file)

        row = required_files_df[required_files_df["file"] == target_file]

        if row.empty:
            raise ValueError(
                f"Could not find required column information for "
                f"{target_file} in {requirements_file}."
            )

        required_columns_str = row["required_columns"].iloc[0]

        return [col.strip() for col in required_columns_str.split(";") if col.strip()]

    @staticmethod
    def validate_required_columns(
        data_path,
        target_file,
        requirements_file=None,
    ):
        """This method validates the required columns and required row
        values before Prescient parsing.

        This method checks that each required column listed in
        required_data_files.csv exists in the target input file and
        that required columns are populated for all rows. For gen.csv,
        ramp-rate data are required only for thermal generators.

        """

        data_path = Path(data_path)
        data_file = data_path / target_file
        if requirements_file is None:
            requirements_file = data_path.parent / "required_data_files.csv"
        else:
            requirements_file = Path(requirements_file)

        if not data_file.exists():
            raise FileNotFoundError(f"Required file not found: {data_file}")

        if not requirements_file.exists():
            raise FileNotFoundError(
                f"Required data-file specification not found: {requirements_file}"
            )

        required_columns = PrescientImporter().get_required_columns_from_file(
            requirements_file,
            target_file,
        )

        df = pd.read_csv(data_file)

        ramp_col = "Ramp Rate MW/Min"
        thermal_unit_types = {"CT", "CC", "STEAM", "COAL", "NUC", "THERMAL"}

        def is_missing(series):
            return (
                series.isna()
                | (series.astype(str).str.strip() == "")
                | (
                    series.astype(str)
                    .str.strip()
                    .str.upper()
                    .isin(["NA", "NAN", "NONE"])
                )
            )

        # For gen.csv, Ramp Rate MW/Min is required only for thermal
        # generators.
        if target_file == "gen.csv" and ramp_col in required_columns:
            required_columns_no_ramp = [
                col for col in required_columns if col != ramp_col
            ]
        else:
            required_columns_no_ramp = required_columns

        missing_columns = [
            col for col in required_columns_no_ramp if col not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"{target_file} is missing required column(s): "
                f"{missing_columns}. Please update {target_file} before "
                "loading data with Prescient."
            )

        # Check that each required column has populated values for all
        # rows.
        for col in required_columns_no_ramp:
            missing_mask = is_missing(df[col])

            if missing_mask.any():
                if "GEN UID" in df.columns:
                    missing_rows = df.loc[missing_mask, "GEN UID"].astype(str).tolist()
                    row_description = f"generator(s): {missing_rows}"
                elif "UID" in df.columns:
                    missing_rows = df.loc[missing_mask, "UID"].astype(str).tolist()
                    row_description = f"row UID(s): {missing_rows}"
                elif "Bus ID" in df.columns:
                    missing_rows = df.loc[missing_mask, "Bus ID"].astype(str).tolist()
                    row_description = f"bus ID(s): {missing_rows}"
                else:
                    missing_rows = df.index[missing_mask].tolist()
                    row_description = f"row index/indices: {missing_rows}"

                raise ValueError(
                    f"{target_file} has missing values in required column "
                    f"'{col}' for {row_description}. Please update the input "
                    "data before loading with Prescient."
                )

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

    def load_storage_csv(self, data_path, model):
        """This method imports storage data.

        :param data_path: filepath for storage data csv file
        """
        data_path = Path(data_path)

        bus_path = data_path / "bus.csv"
        bus_id_to_name = pd.read_csv(bus_path).set_index("Bus ID")["Bus Name"].to_dict()

        try:
            storage_path = data_path / "storage.csv"
            storage_df = pd.read_csv(storage_path)

            storage_data = {}
            for _, row in storage_df.iterrows():
                name = row["name"]
                storage_data[name] = row.drop("name").to_dict()
                storage_data[name]["bus"] = bus_id_to_name[
                    storage_data[name]["bus"]
                ]  # to match egret behavior

            model.data["elements"]["storage"] = storage_data
        except FileNotFoundError:
            print(
                f"Warning: The file '{storage_path}' does not exist. Skipping loading storage data."
            )
            model.data["elements"]["storage"] = {}
