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
        "Tr Ratio": lines["i"],  # if 0.0 this turns it into a tranformer
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

    dc_dict = {}


# --------------------------#
if __name__ == "__main__":

    file = r"./gtep/data/nc_data/base_s_50_elec.nc"
    groups, metadata = _load_data_file(file)
    bus_df(groups["buses"])
    pass
