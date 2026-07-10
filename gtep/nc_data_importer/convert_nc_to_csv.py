import gtep.nc_data_importer.nc_file_reader as nc_reader
import os
import pandas as pd
import numpy as np


def _load_data_file(nc_file):
    if not os.path.isfile(nc_file):
        raise ValueError(f"nc_file '{nc_file}' is not a file")
    # read the file
    data, metadata = nc_reader.read_nc(nc_file)
    # group data
    groups = nc_reader.group_data(data)

    return groups, metadata


def save_csv(df, file_name):
    df.to_csv(file_name, index=False, header=True)


def bus_df(bus_data):
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

    bus_df = pd.DataFrame(bus_dict)

    return bus_df


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

# --------------------------#
if __name__ == "__main__":

    file = r"./gtep/data/nc_data/base_s_50_elec.nc"
    groups, metadata = _load_data_file(file)
    bus_df = bus_df(groups["buses"])
    branch_df, dc_branch_df = branch_df(groups['links'], groups['lines'])
    gen_df, p_fuel_df, p_cost_df = gen_df(groups['generators'], groups['carriers'])
    pass
