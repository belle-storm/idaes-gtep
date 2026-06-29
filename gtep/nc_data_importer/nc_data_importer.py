import netCDF4 as nc
import json
import numpy.ma as ma
from datetime import datetime, timedelta
import gtep.nc_data_importer.data_skeleton as data_skeleton


def read_nc(file):
    """Read netCDF file, saving data in a dictionary, with groups as keys and values as arrays. Save all metadata as dictionaries"""
    ds = nc.Dataset(file)
    metadata_dict = {"file_metadata": {}, "variables_metadata": {}, "dimensions": {}}
    # grab data
    data = {var: ds.variables[var][:] for var in ds.variables}
    # reformat masked arrays
    for k, v in data.items():
        if isinstance(v, ma.MaskedArray):
            data[k] = v.data
    # Extract global attributes (file-level metadata)
    for attr_name in ds.ncattrs():
        if attr_name == "meta" or attr_name == "crs":
            attribute = getattr(ds, attr_name)
            if isinstance(attribute, str):
                metadata_dict["file_metadata"][attr_name] = json.loads(attribute)
        else:
            metadata_dict["file_metadata"][attr_name] = getattr(ds, attr_name)

    # Iterate through variables
    for var_name, var in ds.variables.items():

        # Extract variable attributes (metadata)
        var_attrs = {}
        for attr_name in var.ncattrs():
            var_attrs[attr_name] = getattr(var, attr_name)
        metadata_dict["variables_metadata"][var_name] = var_attrs

    metadata_dict["dimensions"] = {
        dimname: len(dim) for dimname, dim in ds.dimensions.items()
    }

    return data, metadata_dict


def group_data(data):
    groups = {}
    for item, val in data.items():
        parts = item.split("_", 1)
        if len(parts) > 1:
            prefix = parts[0]
        else:
            prefix = parts[0]
        if prefix not in groups:
            groups[prefix] = {}
        groups[prefix][parts[-1]] = val
    return groups


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


def add_storage_data(elements, storage_data):

    for i, name in enumerate(storage_data["i"]):
        storage_dict = {}
        storage_dict["bus"] = storage_data["bus"][i]
        storage_dict["generator"] = None
        storage_dict["storage_type"] = storage_data["carrier"][i]
        storage_dict["energy_capacity"] = None
        storage_dict["initial_state_of_charge"] = None
        storage_dict["end_state_of_charge"] = None
        storage_dict["minimum_state_of_charge"] = None
        storage_dict["charge_efficiency"] = None
        storage_dict["discharge_efficiency"] = None
        storage_dict["max_discharge_rate"] = None
        storage_dict["min_discharge_rate"] = None
        storage_dict["max_charge_rate"] = None
        storage_dict["min_charge_rate"] = None
        storage_dict["initial_charge_rate"] = None
        storage_dict["initial_discharge_rate"] = None
        storage_dict["charge_cost"] = None
        storage_dict["discharge_cost"] = None
        storage_dict["retention_rate_60min"] = None
        storage_dict["ramp_up_input_60min"] = None
        storage_dict["ramp_down_input_60min"] = None
        storage_dict["ramp_up_output_60min"] = None
        storage_dict["ramp_down_output_60min"] = None
        storage_dict["in_service"] = True
        storage_dict["capital_multiplier"] = None
        storage_dict["extension_multiplier"] = None
        storage_dict["investment_cost"] = storage_data["capital_cost"][i]
        storage_dict["investment_cost_kwh"] = None

        # included in data but no match here
        storage_dict["e_nom_extendable"] = bool(storage_data["e_nom_extendable"][i])
        storage_dict["e_cyclic"] = bool(storage_data["e_cyclic"][i])
        storage_dict["lifetime"] = storage_data["lifetime"][i]

        elements[name] = storage_dict


def add_buses(buses, bus_data):
    for i, bus_name in enumerate(bus_data["i"]):
        bus_dict = {}
        bus_dict["id"] = bus_name
        bus_dict["base_kv"] = None
        bus_dict["matpower_bustype"] = bus_data["control"][i]
        bus_dict["vm"] = None
        bus_dict["va"] = None
        bus_dict["v_min"] = None
        bus_dict["v_max"] = None
        bus_dict["area"] = bus_data["location"][i]
        bus_dict["zone"] = bus_data["country"][i]

        # included in data but seemingly no match here
        bus_dict["v_nom"] = bus_data["v_nom"][i]
        bus_dict["x"] = bus_data["x"][i]
        bus_dict["y"] = bus_data["y"][i]
        bus_dict["carrier"] = bus_data["carrier"][i]
        bus_dict["sub_network"] = bus_data["sub_network"][i]
        bus_dict["substation_lv"] = bus_data["substation_lv"][i]
        bus_dict["substation_off"] = bus_data["substation_off"][i]

        buses[bus_name] = bus_dict


def add_branches(branches, dc_branch, branch_data):

    for ind, branch_name in enumerate(branch_data["i"]):
        if branch_data["carrier"][ind] != "DC":
            branch_dict = {}
            branch_dict["from_bus"] = branch_data["bus0"][ind]
            branch_dict["to_bus"] = branch_data["bus1"][ind]
            branch_dict["in_service"] = None
            branch_dict["resistance"] = None
            branch_dict["reactance"] = None
            branch_dict["charging_susceptance"] = None
            branch_dict["rating_long_term"] = None
            branch_dict["rating_short_term"] = None
            branch_dict["rating_emergency"] = None
            branch_dict["angle_diff_min"] = None
            branch_dict["angle_diff_max"] = None
            branch_dict["pf"] = None
            branch_dict["qf"] = None
            branch_dict["pt"] = None
            branch_dict["qt"] = None
            branch_dict["branch_type"] = branch_data["carrier"][ind]
            branch_dict["loss_rate"] = branch_data["efficiency"][ind]
            branch_dict["distance"] = branch_data["length"][ind]
            branch_dict["capital_cost"] = branch_data["capital_cost"][ind]
            branch_dict["capital_multiplier"] = None
            branch_dict["extension_multiplier"] = None

            # included in data but seemingly no match here
            branch_dict["p_nom"] = branch_data["p_nom"][ind]
            branch_dict["p_nom_extendable"] = bool(branch_data["p_nom_extendable"][ind])
            branch_dict["p_min_pu"] = branch_data["p_min_pu"][ind]
            branch_dict["lifetime"] = branch_data["lifetime"][ind]
            branch_dict["underground"] = bool(branch_data["underground"][ind])
            branch_dict["underwater_fraction"] = branch_data["underwater_fraction"][ind]
            branch_dict["under_construction"] = bool(
                branch_data["under_construction"][ind]
            )
            branch_dict["geometry"] = branch_data["geometry"][ind]
            branch_dict["dc"] = branch_data["dc"][ind]
            branch_dict["tags"] = branch_data["tags"][ind]

            branches[branch_name] = branch_dict

        else:
            # dc branch
            dc_branch_dict = {}
            dc_branch_dict["from_bus"] = branch_data["bus0"][ind]
            dc_branch_dict["to_bus"] = branch_data["bus1"][ind]
            dc_branch_dict["rating_short_term"] = None
            dc_branch_dict["rating_long_term"] = None
            dc_branch_dict["rating_emergency"] = None

            dc_branch[branch_name] = branch_dict


file = r"./gtep/data/nc_data/base_s_50_elec.nc"

data, metadata = read_nc(file)

start_time, end_time = get_start_end(
    data["snapshots_snapshot"],
    metadata["variables_metadata"]["snapshots_snapshot"]["units"],
)

groups = group_data(data)

model_data = data_skeleton.create_skeleton()


pass
