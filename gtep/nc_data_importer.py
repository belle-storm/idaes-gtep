import netCDF4 as nc
import json
import numpy.ma as ma
import pandas as pd
from datetime import datetime, timedelta
import egret.data.model_data as md


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


def _create_skeleton():
    model_data = md.ModelData.empty_model_data_dict()
    elements = model_data["elements"]
    system = model_data["system"]

    system["name"] = "NC"
    system["baseMVA"] = None  # FIXME update with new default


def _add_buses(data_file, elements, system):
    elements["bus"] = {}
    elements["load"] = {}
    elements["shunt"] = {}


def _add_branches():
    pass


def _add_generators():
    pass


def _read_metadata():
    pass
    # read simulations objects csv type stuff (check what is needed for the model) as df


# minutes_per_period = {
#     "DAY_AHEAD": int(metadata_df.loc["Period_Resolution", "DAY_AHEAD"]) // 60,
#     "REAL_TIME": int(metadata_df.loc["Period_Resolution", "REAL_TIME"]) // 60,
# }


def _get_scalar_reserve_data():
    pass
    # TODO confirm what this is in the regular model and mirror


def _time_series_data():
    pass


def _compute_bus_load_participation_factors():
    """
    compute aggregate load per area, and then compute
    load participation factors from each bus from that data.

    Returns
    =======
    participation_factors:dict[str,float]
        Maps bus name to the fraction of its area load that it carries (0 to 1)
    """
    pass


def set_t0_data():
    """Put t0 information into the passed in model dict

    Only t0 data for thermal generators is populated.

    Data comes from:
    * t0_state, if provided
    * otherwise, a file called initial_status.csv, if present
    * otherwise, t0 data is left blank

    If t0_state is provided, it should be organized as t0_state[name][value],
    where `name` is the name of a generator, and `value` is 'initial_status',
    'initial_p_output', and 'initial_q_output'.  For any generator included in
    t0_state, all three values must be present.

    If initial_status.csv is used, it must have a header row and may have
    from 1 to 3 data rows.  Row 1 is 'initial_status'.  Row 2 is
    'initial_p_output'.  Row 3 is 'initial_q_output'.  Column headers are
    the generator names. Default values are used for any missing rows.

    Any generators not mentioned in the data source are left untouched.
    """
    pass


# return ParsedCache object


def _get_intial_actuals():
    pass
    # data = self._cache.get_new_skeleton() #copy the model (deep copy)
    # data['system']['time_period_length_minutes'] = minutes_per_timestep #sced_freq_min
    # data['system']['time_keys'] = [str(i) for i in range(1,num_time_steps+1)] #num time step is the num days in options and meta_df
    # md = EgretModel(data)


def _ensure_forecastable_storage(self, sim_type: str, num_entries: int, model) -> None:
    # """ Ensure that the model has an array allocated for every type of forecastable data
    # """
    # sim type for prescient has been "REAL TIME"
    # for data, key in self._get_forecastable_locations(sim_type, model):
    #     if (key not in data or \
    #         type(data[key]) is not dict or \
    #         data[key]['data_type'] != 'time_series' or \
    #         len(data[key]['values'] != num_entries)
    #        ):
    #         data[key] = { 'data_type': 'time_series',
    #                       'values': [None]*num_entries}
    pass


def _populate_with_forecastable_data(
    self,
    sim_type: str,
    start_time: datetime,
    num_time_periods: int,
    time_period_length_minutes: int,
    model,
) -> None:
    # end_time = start_time + timedelta(minutes=num_time_periods*time_period_length_minutes)
    # native_frequency = self._cache.minutes_per_period[sim_type]
    # step_ratio = time_period_length_minutes // native_frequency

    # if step_ratio == 1 and len(model.data['system']['time_keys']) == num_time_periods:
    #     self._cache.populate_skeleton_with_data(model.data, sim_type, start_time, end_time)
    # else:
    #     copy_from = self._cache.generate_model(sim_type, start_time, end_time)
    #     _recurse_copy_at_ratio(copy_from.data, model.data, step_ratio)

    # # Fill in the times
    # time_labels = model.data['system']['time_keys']
    # delta = timedelta(minutes=time_period_length_minutes)
    # for i in range(len(time_labels)):
    #     dt = start_time + i*delta
    #     time_labels[i] = dt.strftime('%Y-%m-%d %H:%M')
    # sim type for prescient has been "REAL TIME"
    pass


# finish the rest of the prescient workflow (identify how much is needed)


# ---------------------------------------------------#
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


# -----------------------------------------------------#
if __name__ == "__main__":
    file = r"./gtep/data/nc_data/base_s_50_elec.nc"

    data, metadata = read_nc(file)

    # grab the base datetime from the metadata string
    time_string = metadata["variables_metadata"]["snapshots_snapshot"]["units"]
    _, start_date_string = _get_basetime(time_string)
    date_format = "%Y-%m-%d %H:%M:%S"
    dt_object = datetime.strptime(start_date_string, date_format)

    # grab the starting datetime (hours since basetime)
    time_data = data["snapshots_snapshot"]
    start_time = _get_snapshot_time(dt_object, time_data[0])
    end_time = _get_snapshot_time(
        dt_object, time_data[-1]
    )  # needs to be based on the number of days in the options set (default 365)

    pass
