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

"""NC expansion planning data utilities.

This module defines an expansion-planning data wrapper for NC input data.
It loads NC-formatted data, converts it into an Egret model, and builds
representative time periods for expansion planning workflows.

:module: nc_expansion_planning_data
:author: Bstorm
"""

from gtep.gtep_data import ExpansionPlanningData
from gtep.nc_data_importer.nc_data_importer import NCDataProvider
from egret.data.model_data import ModelData as EgretModel
import random
import logging

logger = logging.getLogger("gtep.gtep_data")


class NCExpansionPlanningData(ExpansionPlanningData):
    """Expansion-planning data handler for NC-formatted input.

    :param stages: Number of planning stages.
    :type stages: int
    :param num_reps: Number of representative periods.
    :type num_reps: int
    :param len_reps: Length of each representative period.
    :type len_reps: int
    :param num_commit: Number of commitment periods.
    :type num_commit: int
    :param num_dispatch: Number of dispatch periods.
    :type num_dispatch: int
    :param duration_dispatch: Duration of each dispatch period in minutes.
    :type duration_dispatch: int
    """
    def __init__(
        self,
        stages: int = 2,
        num_reps: int = 4,
        len_reps: int = 1,
        num_commit: int = 24,
        num_dispatch: int = 1,
        duration_dispatch: int = 60,
    ) -> None:
        """Initialize the NC expansion-planning data object."""
        super().__init__(
            stages, num_reps, len_reps, num_commit, num_dispatch, duration_dispatch
        )

        self.data_type = "nc_data"

    def _build_rep_dates(
        self,
        dates: list[str],
        weights: list[float],
        num_days: int = 365,
        period_per_step: int = 24,
    ) -> None:
        """Build representative dates and weights.

        :param dates: User-provided representative dates, if any.
        :type dates: list[str] | None
        :param weights: User-provided representative weights, if any.
        :type weights: list[float] | None
        :param num_days: Number of days in the modeled horizon.
        :type num_days: int
        :param period_per_step: Number of time keys per representative day.
        :type period_per_step: int
        :raises ValueError: If the number of dates or weights is invalid.
        """
        # Get the timestamps in the loaded day-ahead data. Default
        # representative_dates are selected from this list to ensure
        # they correspond to valid input data timestamps. if
        # representative_dates are provided by the user, those values
        # are used instead.
        time_keys = self.md.data["system"]["time_keys"]

        if dates is None:
            available_day_starts = time_keys[::int(period_per_step)]

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
                representative_dates = default_representative_dates[: self.num_reps]
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
            if len(dates) != self.num_reps:
                raise ValueError(
                    f"The number of provided representative_dates must match num_reps. "
                    f"Received len(representative_dates)={len(dates)}, "
                    f"but num_reps={self.num_reps}."
                )

            # Validate that all user-provided representative dates
            # exist in the loaded day-ahead timestamps.
            missing_dates = [
                date for date in dates if date not in time_keys
            ]
            if missing_dates:
                raise ValueError(
                    "The following representative_dates are not valid timestamps in the "
                    f"loaded day-ahead input data: {missing_dates}"
                )
            representative_dates = dates

        self.representative_dates = representative_dates

        if weights is not None:

            if len(dates) != len(weights):
                raise ValueError(
                    "Length of representative_dates and representative_weights must match."
                )
            else:
                print(
                    "INFO: representative_dates and representative_weights are aligned. Continue building the data modeling object..."
                )

            # Store as a dictionary
            self.representative_weights_dict = dict(
                zip(dates, weights)
            )

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
                weight_per_date = int(total_weight / len(representative_dates))

            # Store weights as a dictionary by representative date
            self.representative_weights_dict = {
                date: weight_per_date for date in self.representative_dates
            }

        # IMPORTANT TO READ: Always add or modify any new elements in
        # self.md.data (such as new time series or parameters) BEFORE
        # creating representative_data using clone_at_time_keys. This
        # ensures all representative ModelData objects will have the
        # new elements.
        data_list = []
        time_keys = self.md.data["system"]["time_keys"]
        for date in self.representative_dates:
            key_idx = time_keys.index(date)
            time_key_set = time_keys[key_idx : key_idx + int(period_per_step)]
            data_list.append(self.md.clone_at_time_keys(time_key_set))

        self.representative_data = data_list

    def load_nc_data(
        self,
        nc_file: str,
        representative_dates: list[str] = None,
        representative_weights: list[float] = None,
        options_dict: dict[str, any] = None,
    ) -> None:
        """Load NC data and prepare representative periods.

        :param nc_file: Path to the NC data directory.
        :type nc_file: str
        :param representative_dates: Representative timestamps to use.
        :type representative_dates: list[str] | None
        :param representative_weights: Weights corresponding to representative dates.
        :type representative_weights: list[float] | None
        :param options_dict: Optional loader configuration dictionary.
        :type options_dict: dict[str, Any] | None
        """

        if options_dict is None:
            options_dict = {"data_path": nc_file, 'num_days':365}
        else:
            options_dict["data_path"] = nc_file
            if 'num_days' not in options_dict.keys():
                options_dict["num_days"] = 365

        #import data 
        data_provider = NCDataProvider(options=options_dict)

        #format as egret model
        data = data_provider._cache
        self.md = EgretModel(data)

        periods_per_step = data_provider.metadata_df.loc["Periods_per_Step"]["REAL TIME"]

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

        self._build_rep_dates(representative_dates, representative_weights, options_dict['num_days'], periods_per_step)
        

