import gtep.nc_data_importer.data_skeleton as data_skeleton
from egret.parsers.rts_gmlc.parsed_cache import ParsedCache
from egret.parsers.rts_gmlc._reserves import (
    ScalarReserveData,
    ScalarReserveValue,
    reserve_name_map,
)
from datetime import datetime, timedelta
import gtep.nc_data_importer.nc_file_reader as nc_reader
import os
import pandas as pd
import warnings

file = r"./gtep/data/nc_data/base_s_50_elec.nc"


class NCDataProvider:
    """Provides data for RTS-GMLC like files"""

    def __init__(self, options: dict = None):
        # read the nc file
        self.data_groups, self.metadata = self._load_data_file(
            options["data_path"]
        )  # TODO replace with csv directory
        
        # grab the start and end data times
        self._start_time, end_time = self.read_simulation_obj(options["data_path"])
        # check if there is a num_days key
        if "num_days"  in options.keys():
            end_time = self._start_time + timedelta(days=options["num_days"])
        self._end_time = end_time

        self._cache = self.parse_to_cache()

    def read_simulation_obj(self, dir):
        file_path = os.path.join(dir, 'simulation_objects.csv')
        sim_df = pd.read_csv(file_path)
        start_time = datetime(sim_df.loc["Date_From"]["DAY_AHEAD"])
        end_time = datetime(sim_df.loc["Date_To"]["DAY_AHEAD"])

        return start_time, end_time

    def create_nc_skeleton(self, data_dir):
        model_data = data_skeleton.create_skeleton()

        system = model_data["system"]
        system["name"] = "nc_data"

        elements = model_data["elements"]
        system = model_data["system"]

        self._read_buses(data_dir, elements, system)
        self._read_branches(data_dir, elements)
        self._read_generators(data_dir, elements)

        return model_data

    def _read_buses(self, base_dir: str, elements: dict, system: dict) -> dict:

        elements["bus"] = {}
        elements["load"] = {}
        elements["shunt"] = {}

        # add the buses
        bus_id_to_name = {}
        bus_areas = set()
        bus_df = pd.read_csv(os.path.join(base_dir, "bus.csv"))

        for idx, row in bus_df.iterrows():

            bus_name = str(row["Bus Name"])
            bus_dict = {
                "id": str(row["Bus ID"]),
                "base_kv": float(row["BaseKV"]),
                "matpower_bustype": row["Bus Type"],
                "vm": float(row["V Mag"]),
                "va": float(row["V Angle"]),
                "v_min": 0.95,
                "v_max": 1.05,
                "area": str(row["Area"]),
                "zone": str(row["Zone"]),
                #extra data 
                "Carrier": str(row["carrier"]),
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
            
            bus_id_to_name[bus_dict["id"]] = bus_name
            bus_areas.add(bus_dict["area"])
            elements["bus"][bus_name] = bus_dict

        #add loads to elements  
        load_df = pd.read_csv(os.path.join(base_dir, "bus_load.csv"))
        p_load_df = pd.read_csv(os.path.join(base_dir, "p_load.csv"))
        q_load_df = pd.read_csv(os.path.join(base_dir, "q_load.csv"))

        for idx, row in load_df.iterrows():
            bus_name = str(row["Bus Name"])
            #format load dictionaries
            PD = {'data type':'time_series','values':p_load_df[bus_name]}
            QD = {'data type':'time_series','values':q_load_df[bus_name]}

            load_dict = {
                "bus": bus_name,
                "in_service": row['in_service'],
                "p_load": PD,
                "q_load": QD,
                "area": row["area"],
                "zone": row["zone"],
            }
            elements["load"][bus_name] = load_dict

        #add filler valyes for reference buses
        system["reference_bus"] = None
        system["reference_bus_angle"] = 0

        # add the areas
        elements["area"] = {name: dict() for name in bus_areas}


    def _read_branches(base_dir: str, elements: dict) -> None:

        # add the branches
        elements["branch"] = {}
        branch_df = pd.read_csv(os.path.join(base_dir, "branch.csv"))
        for idx, row in branch_df.iterrows():

            branch_dict = {
                "from_bus": bus_id_to_name[str(row["From Bus"])],
                "to_bus": bus_id_to_name[str(row["To Bus"])],
                "in_service": True,
                "resistance": float(row["R"]),
                "reactance": float(row["X"]),
                "charging_susceptance": float(row["B"]),
                "rating_long_term": float(row["Cont Rating"]) or None,
                "rating_short_term": float(row["LTE Rating"]) or None,
                "rating_emergency": float(row["STE Rating"]) or None,
                "angle_diff_min": -90,
                "angle_diff_max": 90,
                "pf": None,
                "qf": None,
                "pt": None,
                "qt": None,
            }

            TAP = float(row["Tr Ratio"])
            if TAP != 0.0:
                branch_dict["branch_type"] = "transformer"
                branch_dict["transformer_tap_ratio"] = TAP
                branch_dict["transformer_phase_shift"] = 0.0
            else:
                branch_dict["branch_type"] = "line"

            name = str(row["UID"])
            elements["branch"][name] = branch_dict
        branch_df = None

        # add the DC branches
        if os.path.exists(os.path.join(base_dir, "dc_branch.csv")):
            elements["dc_branch"] = {}
            branch_df = pd.read_csv(os.path.join(base_dir, "dc_branch.csv"))
            for idx, row in branch_df.iterrows():
                branch_dict = {
                    "from_bus": bus_id_to_name[str(row["From Bus"])],
                    "to_bus": bus_id_to_name[str(row["To Bus"])],
                    "rating_short_term": float(row["MW Load"]),
                    "rating_long_term": float(row["MW Load"]),
                    "rating_emergency": float(row["MW Load"]),
                }
                name = str(row["UID"])
                elements["dc_branch"][name] = branch_dict
            branch_df = None

    def _read_generators(base_dir: str, elements: dict) -> None:
        from math import isnan

        # add the generators
        elements["generator"] = {}
        RENEWABLE_TYPES = {"WIND", "HYDRO", "RTPV", "PV", "ROR"}
        gen_df = pd.read_csv(os.path.join(base_dir, "gen.csv"))
        for idx, row in gen_df.iterrows():
            # if this is storage we need to handle it differently
            if row["Fuel"] == "Storage":
                continue

            # NOTE: for now, Egret doesn't handle CSP -- not clear how to model
            if row["Unit Type"] == "CSP":
                continue

            name = str(row["GEN UID"])
            bus_name = bus_id_to_name[str(row["Bus ID"])]
            gen_dict = {
                "bus": bus_name,
                "in_service": True,
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
            }

            # Remove optional values if not present
            for key in ("p_min", "p_max", "q_min", "q_max", "ramp_q"):
                if isnan(gen_dict[key]):
                    del gen_dict[key]

            UNIT_TYPE = str(row["Unit Type"])
            if UNIT_TYPE in RENEWABLE_TYPES:
                gen_dict["generator_type"] = "renewable"
                # ROR is treated as HYDRO by Egret
                if UNIT_TYPE == "ROR":
                    gen_dict["unit_type"] = "HYDRO"
            elif UNIT_TYPE == "SYNC_COND":
                ## TODO: should we have a flag for these?
                gen_dict["generator_type"] = "thermal"
            else:
                gen_dict["generator_type"] = "thermal"

            elements["generator"][name] = gen_dict

            # after this is only really needed for thermal units
            if UNIT_TYPE in RENEWABLE_TYPES:
                continue

            # Gen cost
            ## round as in RTS-GMLC Prescient/topysp.py
            pmax = float(row["PMax MW"])

            # There can be any number of 'Output_pct_<i>' columns.
            # Stop at the first one that doesn't exist or doesn't hold a number
            def valid_output_pcts():
                for i in range(50):
                    try:
                        val = float(row[f"Output_pct_{i}"])
                        if isnan(val):
                            return
                        yield (i, val)
                    except:
                        return

            x = {i: round(val * pmax, 1) for i, val in valid_output_pcts()}
            fuel_field_count = len(x)

            if fuel_field_count > 0:
                ## /1000. from the RTS-GMLC MATPOWER writer --
                ## heat rates are in BTU/kWh, 10^6 BTU == 1 MMBTU, 10^3 kWh == 1 MWh, so MMBTU/MWh == 10^3/10^6 * BTU/kWh
                f = {}
                f[0] = (float(row["HR_avg_0"]) * 1000.0 / 1000000.0) * x[0]
                for i in range(1, fuel_field_count):
                    f[i] = (
                        (
                            (x[i] - x[i - 1])
                            * (float(row[f"HR_incr_{i}"]) * 1000.0 / 1000000.0)
                        )
                    ) + f[i - 1]

                F_COEFF = [
                    (x[i], round(f[i], 2))
                    for i in range(fuel_field_count)
                    if (
                        ((i == 0) or (x[i - 1], f[i - 1]) != (x[i], f[i]))
                        and (x[i], f[i]) != (0.0, 0.0)
                    )
                ]
                if F_COEFF == []:
                    F_COEFF = [(pmax, 0.0)]
                gen_dict["p_fuel"] = {"data_type": "fuel_curve", "values": F_COEFF}

            # UC Data
            MIN_DN_TIME = float(row["Min Down Time Hr"])

            # Startup types and costs, from hot to cold
            startup_heat = (
                float(row["Start Heat Hot MBTU"]),
                float(row["Start Heat Warm MBTU"]),
                float(row["Start Heat Cold MBTU"]),
            )
            startup_time = (
                float(row["Start Time Hot Hr"]),
                float(row["Start Time Warm Hr"]),
                float(row["Start Time Cold Hr"]),
            )

            # Arrange fuel requirements from hottest to coldest, ignoring missing values.
            startup_fuel = []
            for i in range(3):
                # Skip blank values
                if isnan(startup_time[i]) or isnan(startup_heat[i]):
                    continue

                t = max(startup_time[i], MIN_DN_TIME)
                f = startup_heat[i]

                # For entries with matching times, use to the colder data
                if len(startup_fuel) > 0 and startup_fuel[-1][0] == t:
                    startup_fuel[-1] = (t, f)
                else:
                    startup_fuel.append((t, f))

            # If the warmest fuel requirement has a time longer than the minimum
            # down time, extend that warmest requirement down to minimum down time.
            if len(startup_fuel) > 0 and startup_fuel[0][0] > MIN_DN_TIME:
                startup_fuel[0] = (MIN_DN_TIME, startup_fuel[0][1])

            gen_dict["startup_fuel"] = startup_fuel
            fixed_startup_cost = float(row["Non Fuel Start Cost $"])
            if not isnan(fixed_startup_cost):
                gen_dict["non_fuel_startup_cost"] = fixed_startup_cost
            gen_dict["shutdown_cost"] = 0.0

            gen_dict["agc_capable"] = True
            gen_dict["p_min_agc"] = gen_dict["p_min"]
            gen_dict["p_max_agc"] = gen_dict["p_max"]

            ramp_q = gen_dict["ramp_q"]
            gen_dict["ramp_agc"] = ramp_q
            gen_dict["ramp_up_60min"] = 60.0 * ramp_q
            gen_dict["ramp_down_60min"] = 60.0 * ramp_q

            gen_dict["fuel_cost"] = float(row["Fuel Price $/MMBTU"])

            # these assumptions are the same as prescient-rtsgmlc
            gen_dict["startup_capacity"] = gen_dict["p_min"]
            gen_dict["shutdown_capacity"] = gen_dict["p_min"]
            gen_dict["min_up_time"] = float(row["Min Up Time Hr"])
            gen_dict["min_down_time"] = MIN_DN_TIME

            elements["generator"][name] = gen_dict
        gen_df = None

        return model_data

    def parse_to_cache(
        nc_data_dir: str,
        begin_time: datetime,
        end_time: datetime,
    ) -> ParsedCache:
        """Parse data in NC-converted format, keeping the portions between a start and end time

        nc_data_dir : str
            Path to directory holding csv files in NC-converted format (bus.csv, gen.csv, etc).
        begin_time : datetime.datetime or str
            Beginning of time horizon.
        end_time : datetime.datetime or str
            End of time horizon.
        """
        if not os.path.exists(nc_data_dir):
            raise ValueError(f'NC Data directory "{nc_data_dir}" does not exist')

        # Create the skeleton
        model_data = data_skeleton.create_skeleton()

        # add bus, branch, gens, etc

        # Save the data frequencies
        metadata_df = _read_metadata(rts_gmlc_dir, honor_lookahead)
        minutes_per_period = {
            "DAY_AHEAD": int(metadata_df.loc["Period_Resolution", "DAY_AHEAD"]) // 60,
            "REAL_TIME": int(metadata_df.loc["Period_Resolution", "REAL_TIME"]) // 60,
        }

        data_start, data_end = _get_data_date_range(metadata_df)

        constant_reserve_data = _get_scalar_reserve_data(
            rts_gmlc_dir, metadata_df, model_data
        )

        begin_time, end_time = _parse_datetimes_if_strings(begin_time, end_time)
        # TODO: Validate begin_time and end_time.
        #       Do we want to enforce that they fall within the data date range?

        timeseries_df = _read_timeseries_data(
            model_data, rts_gmlc_dir, begin_time, end_time, minutes_per_period
        )

        load_participation_factors = _compute_bus_load_participation_factors(
            model_data
        )  # NOTE don't need since we are ignoring these values

        set_t0_data(model_data, rts_gmlc_dir, t0_state)

        return ParsedCache(
            model_data,
            begin_time,
            end_time,
            minutes_per_period["DAY_AHEAD"],
            minutes_per_period["REAL_TIME"],
            timeseries_df,
            load_participation_factors,
            constant_reserve_data,
        )

    def _get_scalar_reserve_data(
        base_dir: str, metadata_df: df, model_dict: dict
    ) -> ScalarReserveData:
        # Store scalar reserve values as stored in the input
        #
        # Scalar reserve values that apply to both simulation types are stored in the
        # passed in model dict. Scalar values that vary depending on model type are stored
        # in the returned ScalarReserveData.

        da_scalar_reserves, rt_scalar_reserves = _identify_allowed_scalar_reserve_types(
            metadata_df
        )
        shared_reserves = da_scalar_reserves.intersection(rt_scalar_reserves)

        # Collect constant scalar reserves
        da_scalars = []
        rt_scalars = []

        if not os.path.exists(os.path.join(base_dir, "reserves.csv")):
            logger.warning(f"Did not find reserves.csv; assuming no reserves")
            return ScalarReserveData(da_scalars, rt_scalars)

        reserve_df = pd.read_csv(os.path.join(base_dir, "reserves.csv"))
        system = model_dict["system"]
        areas = model_dict["elements"]["area"]
        for idx, row in reserve_df.iterrows():
            res_name = row["Reserve Product"]
            req = float(row["Requirement (MW)"])

            if res_name in reserve_name_map:
                target_dict = system
                area_name = None
            else:
                # reserve name must be <type>_R<area>.
                # split into type and area
                res_name, area_name = res_name.split("_R", 1)
                if res_name not in reserve_name_map:
                    logger.warning(
                        f"Skipping reserve for unrecognized reserve type '{res_name}'"
                    )
                    continue
                if area_name not in areas:
                    logger.warning(
                        f"Skipping reserve for unrecognized area '{area_name}'"
                    )
                    continue
                target_dict = areas[area_name]

            if res_name in shared_reserves:
                # If it applies to both types, save it in the skeleton
                target_dict[reserve_name_map[res_name]] = req
            elif res_name in da_scalar_reserves:
                # If it applies to just day-ahead, save to DA cache
                da_scalars.append(ScalarReserveValue(res_name, area_name, req))
            elif res_name in rt_scalar_reserves:
                # If it applies to just real-time, save to RT cache
                rt_scalars.append(ScalarReserveValue(res_name, area_name, req))

        return ScalarReserveData(da_scalars, rt_scalars)

    def _identify_allowed_scalar_reserve_types(
        metadata_df: df,
    ) -> Tuple[Set[str], Set[str]]:
        """Return a list of reserve types that apply to each type of model (DA and RT).

        Arguments
        ---------
        metadata_df:df
            The contents of simulation_objects.csv in a DataFrame

        Returns
        -------
        Returns a tuple with two lists of strings, one list for day-ahead models,
        and another list for real-time models. Each list holds the names of reserve
        categories whose scalar reserve values (if specified in reserves.csv) should
        be applied to that type of model.

        (day_ahead_reserves, rt_reserves)
            day_ahead_reserves: Sequence[str]
                The names of reserve categories whose scalar values apply to day-ahead models
            rt_reserves: Sequence[str]
                The names of reserve categories whose scalar values apply to real-time models
        """
        if not "Reserve_Products" in metadata_df.index:
            # By default, accept all reserve types in both types of model
            all_reserves = set(reserve_name_map.keys())
            return (all_reserves, all_reserves)

        row = metadata_df.loc["Reserve_Products"]

        def parse_reserves(which: str) -> Sequence[str]:
            all = row[which]
            if type(all) is not str:
                return {}
            # strip off parentheses, if present
            all = all.strip("()")
            return set(s.strip() for s in all.split(","))

        return (parse_reserves("DAY_AHEAD"), parse_reserves("REAL_TIME"))

    def _read_timeseries_data(
        model_data: dict,
        rts_gmlc_dir: str,
        start_time: datetime,
        end_time: datetime,
        minutes_per_period: dict[str, int],
    ):
        """
        Parse all relevant timeseries files

        Returns
        =======
        all_timeseries: DataFrame
            A DataFrame with the following columns:
            [Simulation, Category, Object, Parameter, Series]

        The Series column holds the data as a pandas series, indexed by the datetime
        of the value.

        """

        # All timeseries data that has already been read (map[filename] -> DataFrame)
        timeseries_file_map = {}

        timeseries_pointer_df = pd.read_csv(
            os.path.join(rts_gmlc_dir, "timeseries_pointers.csv"),
            header=0,
            dtype={"Object": str},
        )

        elements = model_data["elements"]
        params_of_interest = {
            "Generator": {"PMin MW", "PMax MW"},
            "Reserve": {"Requirement"},
            "Area": {"MW Load"},
        }

        # Create an array where we can gather parsed timeseries data
        series_data = [None] * timeseries_pointer_df.shape[0]

        # Store the timeseries data in the timeseries DF
        for idx, row in timeseries_pointer_df.iterrows():
            # Skip rows we don't ingest
            if not row["Category"] in params_of_interest:
                continue
            if not row["Parameter"] in params_of_interest[row["Category"]]:
                continue

            # Skip generators not in skeleton
            if (
                row["Category"] == "Generator"
                and not row["Object"] in elements["generator"]
            ):
                continue
            # Skip areas not in skeleton
            if row["Category"] == "Area" and not row["Object"] in elements["area"]:
                continue

            is_reserve = row["Category"] == "Reserve"
            if is_reserve:
                # Skip unrecognized reserve names
                name = row["Object"]
                if not is_valid_reserve_name(name, model_data):
                    continue

            # Read the timeseries file if we haven't already, using the
            # canonical file path as a key into previously read filenames.
            fname = os.path.abspath(os.path.join(rts_gmlc_dir, row["Data File"]))
            if not fname in timeseries_file_map:
                sim = row["Simulation"]
                data = _read_timeseries_file(
                    fname, minutes_per_period[sim], start_time, end_time, row["Object"]
                )
                timeseries_file_map[fname] = data

            # Save a reference to the relevant data as a Series
            series_data[idx] = timeseries_file_map[fname][row["Object"]]

        # Add the 'Series' column
        timeseries_pointer_df = timeseries_pointer_df.assign(Series=series_data)

        # Remove columns that we don't want to preserve
        keepers = {"Simulation", "Category", "Object", "Parameter", "Series"}
        for c in timeseries_pointer_df.columns:
            if not c in keepers:
                timeseries_pointer_df.pop(c)

        # Remove irrelevant rows
        timeseries_pointer_df.dropna(subset=["Series"], inplace=True)

        # Sort by simulation
        timeseries_pointer_df.sort_values(by="Simulation", inplace=True)

        return timeseries_pointer_df

    def _compute_bus_load_participation_factors(model_data):
        """
        compute aggregate load per area, and then compute
        load participation factors from each bus from that data.

        Returns
        =======
        participation_factors:dict[str,float]
            Maps bus name to the fraction of its area load that it carries (0 to 1)
        """
        elements = model_data["elements"]

        # Sum the loads for each area
        area_total_load = {area: 0 for area in elements["area"]}
        for name, load in elements["load"].items():
            area = elements["bus"][load["bus"]]["area"]
            area_total_load[area] += load["p_load"]

        bus_load_participation_factors = {}
        for name, load in elements["load"].items():
            area = elements["bus"][load["bus"]]["area"]
            bus_load_participation_factors[name] = (
                load["p_load"] / area_total_load[area]
            )

        return bus_load_participation_factors
