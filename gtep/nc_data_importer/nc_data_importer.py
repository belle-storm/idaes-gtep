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
from math import isnan

file = r"./gtep/data/nc_data/base_s_50_elec.nc"


class NCDataProvider:
    """Provides data for RTS-GMLC like files"""

    def __init__(self, options: dict = None):
        # read the nc file
        if not os.path.exists(options["data_path"]):
            raise ValueError(f'NC Data directory "{options["data_path"]}" does not exist')
        
        # grab the start and end data times
        sim_df = self._read_simulation_obj(options["data_path"])
        self._start_time, end_time = self._get_data_date_range(sim_df)
        
        # check if there is a num_days key
        if "num_days"  in options.keys():
            end_time = self._start_time + timedelta(days=options["num_days"])
        self._end_time = end_time

        self._cache = self.parse_to_cache(
            options["data_path"],
            self._start_time,
            self._end_time,
            )

    def _read_simulation_obj(self, dir):
        file_path = os.path.join(dir, 'simulation_objects.csv')
        sim_df = pd.read_csv(file_path)

        return sim_df

    def _get_data_date_range(metadata_df):
        data_start = datetime(metadata_df.loc["Date_From"]["DAY_AHEAD"])
        data_end = datetime(metadata_df.loc["Date_To"]["DAY_AHEAD"])

        return data_start, data_end

    def _create_nc_skeleton(self, data_dir):
        model_data = data_skeleton.create_skeleton()

        system = model_data["system"]
        system["name"] = "nc_data"

        elements = model_data["elements"]
        system = model_data["system"]

        self._read_buses(data_dir, elements, system)
        self._read_branches(data_dir, elements)
        self._read_generators(data_dir, elements)
        self._read_storage(data_dir, elements)

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
                "from_bus": str(row["From Bus"]),
                "to_bus": str(row["To Bus"]),
                "in_service": True,
                "resistance": float(row["R"]),
                "reactance": float(row["X"]),
                "charging_susceptance": float(row["B"]),
                "rating_long_term": float(row["LTE Rating"]) or None,
                "rating_short_term": float(row["STE Rating"]) or None,
                "rating_emergency": float(row["Cont Rating"]) or None,
                "angle_diff_min": -90,
                "angle_diff_max": 90,
                "pf": None,
                "qf": None,
                "pt": None,
                "qt": None,
                "branch_type" : "line",
                "capital_cost": float(row["capital_cost"]),
                "distance": float(row["length"]),
                "loss_rate": float(row['loss_rate']),
                # extra columns
                "Carrier": str(row["Carrier"]),
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
            elements["dc_branch"] = {}
            dc_branch_df = pd.read_csv(os.path.join(base_dir, "dc_branch.csv"))

            for idx, row in dc_branch_df.iterrows():
                dc_branch_dict = {
                    "from_bus": str(row["From Bus"]),
                    "to_bus": str(row["To Bus"]),
                    "rating_long_term": float(row["LTE Rating"]),
                    "rating_short_term": float(row["STE Rating"]),
                    "rating_emergency": float(row["Cont Rating"]),
                    "capital_cost": str(row['capital_cost']),
                    "distance": str(row['length']),
                    "loss_rate": float(row['loss_rate']),
                    # extra columns
                    "carrier": str(row['Carrier']),
                    "lifetime": str(row['lifetime']),
                    "underground": str(row['underground']),
                    "under_construction": bool(row['under_construction']),
                    "tags": row['tags'],
                    "geometry": row['geometry'],
                    "underwater_fraction": float(row['underwater_fraction']),
                    "p_nom_extendable": bool(row['p_nom_extendable']),
                    "p_min_pu": float(row['p_min_pu']),
                }
                name = str(row["UID"])
                elements["dc_branch"][name] = dc_branch_dict

    def _read_generators(base_dir: str, elements: dict) -> None:
        # add the generators
        elements["generator"] = {}
        RENEWABLE_TYPES = ['GEO', 'PV','WIND','ROR','HYDRO','RTPV']

        gen_df = pd.read_csv(os.path.join(base_dir, "gen.csv"))
        p_fuel_df = pd.read_csv(os.path.join(base_dir, "p_fuel.csv"))
        p_cost_df = pd.read_csv(os.path.join(base_dir, "p_cost.csv"))
    
        for idx, row in gen_df.iterrows():

            name = str(row["GEN UID"])
            bus_name = str(row["Bus ID"])
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
                # extra
                "investment_cost": float(row['capital_cost']),
                "emissions_factor": float(row['emissions_factor']),
                "lifetime": int(row['lifetime']),
                "efficiency": float(row['efficiency']),
                "weight": row['weight'],
                "p_nom_min": float(row['p_nom_min']),
                "p_nom_max": row['p_nom_max'],
                "p_max_pu": float(row['p_max_pu']),
            }

            # Remove optional values if not present
            for key in ("p_min", "p_max", "q_min", "q_max"):
                if isnan(gen_dict[key]):
                    del gen_dict[key]

            UNIT_TYPE = str(row["Unit Type"])
            if UNIT_TYPE in RENEWABLE_TYPES:
                gen_dict["generator_type"] = "renewable"
                gen_dict['p_fuel'] = {'data_type':'fuel_curve','values':p_fuel_df[name]}
                # ROR is treated as HYDRO by Egret
                if UNIT_TYPE == "ROR":
                    gen_dict["unit_type"] = "HYDRO"
            else:
                gen_dict["generator_type"] = "thermal"
                gen_dict['p_cost'] = {'data_type':'cost_data','values':p_cost_df[name]}

            #set defaults
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
            gen_dict["min_up_time"] = None
            gen_dict["min_down_time"] = None

            elements["generator"][name] = gen_dict

    def _read_storage(base_dir: str, elements: dict) -> None:
        store_df = pd.read_csv(os.path.join(base_dir, "storage.csv"))
    
        for idx, row in store_df.iterrows():
            storage_dict = {
                'bus' : row['bus'],
                'generator_type' :row['generator'],
                'storage_type' :row['storage_type'],
                'energy_capacity' :row['energy_capacity'],
                'initial_state_of_charge' :row['initial_state_of_charge'],
                'end_state_of_charge' :row['end_state_of_charge'],
                'minimum_state_of_charge' :row['minimum_state_of_charge'],
                'charge_efficiency' :row['charge_efficiency'],
                'discharge_effeciency' :row['discharge_effeciency'],
                'max_discharge_rate' :row['max_discharge_rate'],
                'min_discharge_rate' :row['min_discharge_rate'],
                'max_charge_rate' :row['max_charge_rate'],
                'min_charge_rate' :row['min_charge_rate'],
                'initial_charge_rate' :row['initial_charge_rate'],
                'initial_discharge_rate' :row['initial_discharge_rate'],
                'charge_cost' :row['charge_cost'],
                'discharge_cost' :row['discharge_cost'],
                'retention_rate_60min' :row['retention_rate_60min'],
                'ramp_up_input_60min' :row['ramp_up_input_60min'],
                'ramp_down_input_60min' :row['ramp_down_input_60min'],
                'ramp_up_output_60min' :row['ramp_up_output_60min'],
                'ramp_down_output_60min' :row['ramp_down_output_60min'],
                'in_service' :row['in_service'],
                'capital_multiplier' :row['capital_multiplier'],
                'extension_multiplier' :row['extension_multiplier'],
                'investment_cost' :row['investment_cost'],
                'investment_cost_kwh' :row['investment_cost_kwh'],
            }

            elements["storage"][row['name']] = storage_dict

    def _read_timeseries_data(
        system: dict,
        nc_data_dir: str,
        start_time: datetime,
        end_time: datetime,
        minutes_per_period: int,
    ):

        time_series_df = pd.read_csv(os.path.join(nc_data_dir, "time_series.csv"))
        time_series_df['datetime'] = pd.to_datetime(time_series_df[['Year', 'Month', 'Day', 'Hour']])
        time_keys = []
        for idx, row in time_series_df.iterrows():
            #only append if it is within the target time range
            if start_time <= row['datetime'] <= end_time:
                time = f'{row['Year']}-{row['Month']:02d}-{row['Day']:02d} {row['Hour']:02d}:00'
                time_keys.append(time)

        system['time_keys'] = time_keys
        system['time_period_length_minutes'] = minutes_per_period

        return time_keys

    def parse_to_cache(
        self,
        nc_data_dir: str,
        begin_time: datetime,
        end_time: datetime,
    ):
        """Parse data in NC-converted format, keeping the portions between a start and end time
        """

        # Create the skeleton with data
        model_data = self._create_nc_skeleton(nc_data_dir)

        # Save the data frequencies
        metadata_df = self._read_simulation_obj(nc_data_dir)
        minutes_per_period = {
            "DAY_AHEAD": int(metadata_df.loc["Period_Resolution", "DAY_AHEAD"]) // 60,
        }

        data_start, data_end = self._get_data_date_range(metadata_df)
        #TODO maybe check if start and end are within the data start and data end

        self._read_timeseries_data(
            model_data['system'], nc_data_dir, begin_time, end_time, minutes_per_period
        )

        return model_data

