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
    groups = []
    for item in data.keys():
        prefix = None
        for i, char in enumerate(item):
            if char == "_":
                prefix = item[:i], item[i:]
        if prefix is None:
            prefix = item
        if prefix not in groups:
            groups.append(prefix)


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


file = r"./gtep/data/nc_data/base_s_50_elec.nc"

data, metadata = read_nc(file)

start_time, end_time = get_start_end(
    data["snapshots_snapshot"],
    metadata["variables_metadata"]["snapshots_snapshot"]["units"],
)

pass
