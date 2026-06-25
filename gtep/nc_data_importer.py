import netCDF4 as nc
import json
import numpy.ma as ma
import pandas as pd


def list_sections(file):
    ds = nc.Dataset(file)
    return ds.variables.keys()


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


def convert_to_dataframes(data):
    """Convert all data arrays in the data dictionary as dataframes"""
    for k, v in data.items():
        data[k] = pd.DataFrame(v)

    return data


if __name__ == "__main__":
    file = r"./gtep/data/nc_data/base_s_50_elec.nc"

    data, metadata = read_nc(file)

    start_time = data["snapshots_snapshot"]

    pass
