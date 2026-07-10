import gtep.nc_data_importer.nc_file_reader as nc_reader
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def _load_data_file(nc_file):
    if not os.path.isfile(nc_file):
        raise ValueError(f"nc_file '{nc_file}' is not a file")
    # read the file
    data, metadata = nc_reader.read_nc(nc_file)
    # group data
    groups = nc_reader.group_data(data)

    return groups, metadata


def _get_basetime(time_string):
        # grab the start date from the metadata string
        for i, char in enumerate(time_string):
            if char.isdigit():
                return time_string[:i], time_string[i:]


def _get_snapshot_time(start_time: datetime = None, hours_since: int = 0):
    """
    Convert the snapshots data into the full datetime
    by combining the time and the hours since that time
    """
    if start_time is None:
        start_time = datetime("2020-01-01 00:00:00")

    target_time = start_time + timedelta(hours=int(hours_since))
    return target_time


def get_start_end(
        time_data: list[int], time_string: str, num_days: int = None
    ) -> tuple[datetime, datetime]:
        # grab the base datetime from the metadata string
        _, start_date_string = _get_basetime(time_string)
        date_format = "%Y-%m-%d %H:%M:%S"
        dt_object = datetime.strptime(start_date_string, date_format)

        # grab the starting datetime (hours since basetime)
        start_time = _get_snapshot_time(dt_object, time_data[0])

        if num_days is None:
            hours = time_data[-1]
        else:
            ind = num_days * 24  # convert days to hours
            hours = time_data[ind]
        end_time = _get_snapshot_time(dt_object, hours)

        return start_time, end_time


def save_csv(df, file_name):
    df.to_csv(file_name, index=False, header=True)
    print(f'{file_name} successfully saved!')

def bus_df(bus_data, load_data):
    # save bus data as in csv friendly dataframe
    num_bus = len(bus_data["i"])

    bus_dict = {
        "Bus ID": bus_data["i"],
        "Bus Name": bus_data["i"],
        "BaseKV": bus_data["v_nom"],
        "Bus Type": bus_data["control"],
        "MW Load": [np.nan] * num_bus,
        "MVAR Load": [np.nan] * num_bus,
        "V Mag": [np.nan] * num_bus,
        "V Angle": [np.nan] * num_bus,
        "Area": bus_data["location"],
        "Zone": bus_data["country"],
        # extra columns
        "Carrier": bus_data["carrier"],
        "x": bus_data["x"],
        "y": bus_data["y"],
        "sub_network": bus_data["sub_network"],
        "substation_lv": bus_data["substation_lv"],
        "substation_off": bus_data["substation_off"],
    }

    num_load_bus = len(load_data['i'])

    loads_dict = {
        'bus_name': load_data['i'],
        'bus': load_data['bus'],
        'in_service': [True] * num_load_bus,
        # 'p_load'
        # 'data_type'
        # 'values'
        # 'q_load'
        # 'data_type'
        # 'values'
        'area':[],
        'zone':[],
    }
    p_load = {}
    q_load = {}

    for ix, name in enumerate(load_data['i']):
        bus_idx = bus_data['i'].index(name)
        #assign to dictionary
        loads_dict['bus_name'].append(name)
        loads_dict['bus'].append(load_data['bus'][ix])
        loads_dict['in_service'].append(True)
        loads_dict['area'].append(bus_data["location"][bus_idx])
        loads_dict['zone'].append(bus_data["country"][bus_idx])
        #sve p_load
        if name in load_data['t_p_set_i']:
            p_load_ix = load_data['t_p_set_i'].index(name)
            p_load[name] = load_data['t_p_set'][p_load_ix]
        q_load[name] = [np.nan]

    #TODO update bus read function

    bus_df = pd.DataFrame(bus_dict)
    load_df = pd.DataFrame(loads_dict)
    p_load_df = pd.DataFrame(p_load)
    q_load_df= pd.DataFrame(q_load)

    return bus_df, load_df, p_load_df, q_load_df


def branch_df(links, lines):
    num_branches = len(lines["i"])

    branch_dict = {
        "UID": lines["i"],
        "From Bus": lines["bus0"],
        "To Bus": lines["bus1"],
        "R": [np.nan] * num_branches,
        "X": [0.00287] * num_branches,
        "B": [np.nan] * num_branches,
        "Cont Rating": lines["s_nom"],
        "LTE Rating": lines["s_nom"],
        "STE Rating": lines["s_nom"],
        "Tr Ratio": [1.0] * num_branches,  # if 0.0 this turns it into a tranformer
        # extra columns
        "Carrier": lines["carrier"],
        "s_max_pu": lines["s_max_pu"],
        "capital_cost": lines["capital_cost"],
        "length": lines["length"],
        "num_parallel": lines["num_parallel"],
        "sub_network": lines["sub_network"],
        "v_nom": lines["v_nom"],
        "i_nom": lines["i_nom"],
        "loss_rate": [np.nan] * num_branches,
    }

    #initialize spot for dc branches
    dc_dict = {
        "UID": [],
        "From Bus": [],
        "To Bus": [],
        "Cont Rating": [],
        "LTE Rating": [],
        "STE Rating": [],
        # extra columns
        "Carrier": [],
        "lifetime": [],
        "capital_cost": [],
        "length": [],
        "underground": [],
        "under_construction": [],
        "tags": [],
        "geometry": [],
        "loss_rate": [],
        "underwater_fraction": [],
        "p_nom_extendable": [],
        "p_min_pu": [],    
    }
 

    for ix, type in enumerate(links['carrier']):
        #save DC branches to dc branch dict
        if type == 'DC':
            dc_dict['UID'].append(links['i'][ix])
            dc_dict['From Bus'].append(links['bus0'][ix])
            dc_dict['To Bus'].append(links['bus1'][ix])
            dc_dict["Cont Rating"].append(links['p_nom'][ix])
            dc_dict["LTE Rating"].append(links['p_nom'][ix])
            dc_dict["STE Rating"].append(links['p_nom'][ix])
            #extras
            dc_dict["Carrier"].append(type)
            dc_dict["lifetime"].append(links['lifetime'][ix])
            dc_dict["capital_cost"].append(links['capital_cost'][ix])
            dc_dict["length"].append(links['length'][ix])
            dc_dict["underground"].append(links['underground'][ix])
            dc_dict["tags"].append(links['tags'][ix])
            dc_dict["geometry"].append(links['geometry'][ix])
            dc_dict["loss_rate"].append(links['efficiency'][ix])
            dc_dict["underwater_fraction"].append(links['underwater_fraction'][ix])
            dc_dict["p_nom_extendable"].append(bool(links['p_nom_extendable'][ix]))
            dc_dict["p_min_pu"].append(links['p_min_pu'][ix])
        #add the data from links that aren't DC lines to the branch dict
        else:
            branch_dict['UID'].append(links['i'][ix])
            branch_dict['From Bus'].append(links['bus0'][ix])
            branch_dict['To Bus'].append(links['bus1'][ix])
            branch_dict["R"].append(np.nan)
            branch_dict["X"].append(0.00287)
            branch_dict["B"].append(np.nan)
            branch_dict["Cont Rating"].append(links['p_nom'][ix])
            branch_dict["LTE Rating"].append(links['p_nom'][ix])
            branch_dict["STE Rating"].append(links['p_nom'][ix])
            branch_dict["Tr Ratio"].append(1.0)
            #extras
            branch_dict["Carrier"].append(type)
            branch_dict["s_max_pu"].append(np.nan)
            branch_dict["capital_cost"].append(links['capital_cost'][ix])
            branch_dict["length"].append(links['length'][ix])
            branch_dict["num_parallel"].append(np.nan)
            branch_dict["sub_network"].append(np.nan)
            branch_dict["v_nom"].append(np.nan)
            branch_dict["loss_rate"].append(links['efficiency'][ix])
            branch_dict["i_nom"].append(np.nan)

    branch_df = pd.DataFrame(branch_dict)
    dc_df = pd.DataFrame(dc_dict)

    return branch_df, dc_df


def gen_df(gens, carriers):
    num_gens = len(gens['i'])
    CARRIER_ASSIGN = {
        'CCGT': {'unit_type': 'CT', 'fuel': 'C'},
        'biomass': {'unit_type': 'BIO', 'fuel': 'B'},
        'oil': {'unit_type': 'CC', 'fuel': 'G'}, #FIXME
        'waste': {'unit_type': 'LFILL', 'fuel': 'G'},
        'lignite': {'unit_type': 'COAL', 'fuel': 'C'},
        'nuclear': {'unit_type': 'NUC', 'fuel': 'N'},
        'OCGT': {'unit_type': 'OGS', 'fuel': 'G'},
        'geothermal': {'unit_type': 'GEO', 'fuel': 'GEO'},
        'coal': {'unit_type': 'COAL', 'fuel': 'C'},
        'solar': {'unit_type': 'PV', 'fuel': 'S'},
        'solar-hsat': {'unit_type': 'PV', 'fuel': 'S'},
        'offwind-ac': {'unit_type': 'WIND', 'fuel': 'W'},
        'offwind-float': {'unit_type': 'WIND', 'fuel': 'W'},
        'offwind-dc': {'unit_type': 'WIND', 'fuel': 'W'},
        'onwind': {'unit_type': 'WIND', 'fuel': 'W'},
        'ror': {'unit_type': 'ROR', 'fuel': 'W'} #FIXME
        }
    CO2_EMISSIONS = {}
    #assign co2 emission factors to carrier type
    for ix, name in enumerate(carriers['i']):
        CO2_EMISSIONS[name] = carriers['co2_emissions'][ix]

    gen_dict = {
        'GEN UID':[], 
        'Bus ID':[], 
        'Unit Type':[], #carrier assignment
        'Fuel':[], # carrier assignment
        'MW Inj':[np.nan] * num_gens, 
        'MVAR Inj':[np.nan] * num_gens,
        'V Setpoint p.u.':[np.nan] * num_gens,
        'PMax MW':[], # p_nom
        'PMin MW':[0] * num_gens,
        'QMax MVAR':[np.nan] * num_gens,
        'QMin MVAR':[np.nan] * num_gens,
        'Min Down Time Hr':[np.nan] * num_gens,
        'Min Up Time Hr':[np.nan] * num_gens,
        'Ramp Rate MW/Min':[1] * num_gens,  #TODO read function pull in 1 
        'Start Time Cold Hr':[np.nan] * num_gens,
        'Start Time Warm Hr':[np.nan] * num_gens,
        'Start Time Hot Hr':[np.nan] * num_gens,
        'Start Heat Cold MBTU':[np.nan] * num_gens,
        'Start Heat Warm MBTU':[np.nan] * num_gens,
        'Start Heat Hot MBTU':[np.nan] * num_gens, #TODO read function default startup fuel to 0
        'Non Fuel Start Cost $':[0] * num_gens,
        'Fuel Price $/MMBTU':[1] * num_gens,
        #These are used for p_fuel but we have those values saved individually
        'Output_pct_0':[np.nan] * num_gens,
        'Output_pct_1':[np.nan] * num_gens,
        'Output_pct_2':[np.nan] * num_gens,
        'Output_pct_3':[np.nan] * num_gens,
        'Output_pct_4':[np.nan] * num_gens,
        'HR_avg_0':[np.nan] * num_gens,
        'HR_incr_1':[np.nan] * num_gens,
        'HR_incr_3':[np.nan] * num_gens,
        'HR_incr_4':[np.nan] * num_gens,
        #extra
        'capital_cost':[],
        'emissions_factor':[],
        'lifetime':[],
        'efficiency':[],
        'weight':[],
        'p_nom_min':[],
        'p_nom_max':[],
        'p_max_pu':[],
    }

    #extra p_fuel dataframe 
    p_fuel = {} #key gen uid, val array 
    #TODO PFUEL READ function will need to map to renewable unit type and multiply value by p_nom
    p_cost = {} #key gen uid, val array
    #TODO PCOST read function to do simple labeling for the data_type 
    
    for ix, name in enumerate(gens['i']):
        gen_dict['GEN UID'].append(name) 
        gen_dict['Bus ID'].append(gens['bus'][ix])
        gen_dict['Unit Type'].append(CARRIER_ASSIGN[gens['carrier'][ix]]['unit_type'])
        gen_dict['Fuel'].append(CARRIER_ASSIGN[gens['carrier'][ix]]['fuel'])
        gen_dict['PMax MW'].append(gens['p_nom'][ix])
        #extra
        gen_dict['capital_cost'].append(gens['capital_cost'][ix])
        gen_dict['emissions_factor'].append(CO2_EMISSIONS[gens['carrier'][ix]])
        gen_dict['lifetime'].append(gens['lifetime'][ix])
        gen_dict['efficiency'].append(gens['efficiency'][ix])
        gen_dict['weight'].append(gens['weight'][ix])
        gen_dict['p_nom_min'].append(gens['p_nom_min'][ix])
        gen_dict['p_nom_max'].append(gens['p_nom_max'][ix])
        gen_dict['p_max_pu'].append(gens['p_max_pu'][ix])

        #add -c version if extendable
        if bool(gens['p_nom_extendable']):
            gen_dict['GEN UID'].append(f'{name}-c') 
            gen_dict['Bus ID'].append(gens['bus'][ix])
            gen_dict['Unit Type'].append(CARRIER_ASSIGN[gens['carrier'][ix]]['unit_type'])
            gen_dict['Fuel'].append(CARRIER_ASSIGN[gens['carrier'][ix]]['fuel'])
            gen_dict['PMax MW'].append(gens['p_nom'][ix])
            #extra
            gen_dict['capital_cost'].append(gens['capital_cost'][ix])
            gen_dict['emissions_factor'].append(CO2_EMISSIONS[gens['carrier'][ix]])
            gen_dict['lifetime'].append(gens['lifetime'][ix])
            gen_dict['efficiency'].append(gens['efficiency'][ix])
            gen_dict['weight'].append(gens['weight'][ix])
            gen_dict['p_nom_min'].append(gens['p_nom_min'][ix])
            gen_dict['p_nom_max'].append(gens['p_nom_max'][ix])
            gen_dict['p_max_pu'].append(gens['p_max_pu'][ix])

        if name in gens['t_p_max_pu_i']:
            p_fuel_idx = gens['t_p_max_pu_i'].index(name)
            p_fuel[name] = gens['t_p_max_pu'][p_fuel_idx]
        p_cost[name] = gens['marginal_cost'][ix]

    gen_df = pd.DataFrame(gen_dict)
    p_fuel_df = pd.DataFrame(p_fuel)
    p_cost_df = pd.DataFrame(p_cost)

    return gen_df, p_fuel_df, p_cost_df


def storage_df(storage, num_hours):
    num_stores = len(storage)
    energy_capacity = storage['units_p_nom'] * num_hours
    stor_dict = {
        'name': storage['units_i'],
        'bus': storage['units_bus'],
        'generator':[np.nan] * num_stores,
        'storage_type':[np.nan] * num_stores,
        'energy_capacity': energy_capacity,
        'initial_state_of_charge':[np.nan] * num_stores,
        'end_state_of_charge':[np.nan] * num_stores,
        'minimum_state_of_charge':[0] * num_stores,
        'charge_efficiency': storage['units_efficiency_store'],
        'discharge_efficiency': storage['units_efficiency_dispatch'],
        'max_discharge_rate': storage['units_p_nom'],
        'min_discharge_rate':[0] * num_stores,
        'max_charge_rate': storage['units_p_nom'],
        'min_charge_rate':[0] * num_stores,
        'initial_charge_rate':[np.nan] * num_stores,
        'initial_discharge_rate':[np.nan] * num_stores,
        'charge_cost':[0] * num_stores,
        'discharge_cost':[0] * num_stores,
        'retention_rate_60min':[1] * num_stores,
        'ramp_up_input_60min':[np.nan] * num_stores,
        'ramp_down_input_60min':[np.nan] * num_stores,
        'ramp_up_output_60min':[np.nan] * num_stores,
        'ramp_down_output_60min':[np.nan] * num_stores,
        'in_service':[True] * num_stores,
        'capital_multiplier':[np.nan] * num_stores,
        'extension_multiplier':[np.nan] * num_stores,
        'investment_cost': storage['units_capital_cost'],
        'investment_cost_kwh':[np.nan] * num_stores,
    }

    store_df = pd.DataFrame(stor_dict)
    return store_df


def simulation_objects(start_time, end_time):
    sim_dict = {
        'Parameters':['Periods_per_Step','Period Resolution','Date_From','Date_To'],
        'REAL TIME':[24, 3600, start_time, end_time]
    }
    sim_df = pd.DataFrame(sim_dict)
    return sim_df


def time_series_data(time_data, start):
    time_dict = {
        'Year':[],
        'Month':[],
        'Day':[],
        'Hour':[],
    }

    for hr in time_data:
        dt = _get_snapshot_time(start, hr)
        #assign to dictionary
        time_dict['Year'].append(dt.year)
        time_dict['Month'].append(dt.month)
        time_dict['Day'].append(dt.day)
        time_dict['Hour'].append(dt.hour)

    time_df = pd.DataFrame(time_dict)
    return time_df


# --------------------------#
if __name__ == "__main__":

    #grab data
    file = r"./gtep/data/nc_data/base_s_50_elec.nc"
    groups, metadata = _load_data_file(file)

    #make into dataframes
    data = {
        'bus.csv': None,
        'branch.csv':None
    }
    data['bus.csv'], data['bus_load.csv'], data['p_load.csv'], data['q_load.csv'] = bus_df(groups["buses"])
    data['branch.csv'], data['dc_branch.csv'] = branch_df(groups['links'], groups['lines'])
    data['gen.csv'], data['p_fuel.csv'], data['p_cost.csv'] = gen_df(groups['generators'], groups['carriers'])
    data['storage.csv'] = storage_df(groups['storage'], max(groups['snapshots']['snapshot']))
    basetime_str = _get_basetime(metadata["variables_metadata"]["snapshots_snapshot"]["units"])
    start_time, end_time = get_start_end(groups['snapshots']['snapshot'], basetime_str)
    data['time_series.csv'] = time_series_data(groups['snapshots']['snapshot'], start_time)
    data['simulation_objects.csv'] = simulation_objects(start_time, end_time)

    #save dataframes to csv
    for filename, df in data.items():
        save_csv(df, os.path.join(os.path.dirname(file), filename))
