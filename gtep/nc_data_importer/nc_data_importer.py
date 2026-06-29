import gtep.nc_data_importer.data_skeleton as data_skeleton
from datetime import datetime, timedelta
import gtep.nc_data_importer.nc_file_reader as nc_reader
import os

file = r"./gtep/data/nc_data/base_s_50_elec.nc"

# start_time, end_time = get_start_end(
#     data["snapshots_snapshot"],
#     metadata["variables_metadata"]["snapshots_snapshot"]["units"],
# )


class NCDataProvider:
    """Provides data for RTS-GMLC like files"""

    def __init__(self, options: dict = None):
        # read the nc file
        self.data_groups, self.metadata = self._load_data_file(options["data_path"])
        # check if there is a num_days key
        if "num_days" not in options.keys():
            options["num_days"] = None
        # grab the start and end data times
        self._start_time, self._end_time = self.get_start_end(
            self.data_groups["snapshots"]["snapshots_snapshot"],
            self.metadata["variables_metadata"]["snapshots_snapshot"]["units"],
            num_days=options["num_days"],
        )
        self._cache = self.parse_to_cache()

    def _load_data_file(self, nc_file):
        if not os.path.isfile(nc_file):
            raise ValueError(f"nc_file '{nc_file}' is not a file")
        # read the file
        data, metadata = nc_reader.read_nc(nc_file)
        # group data
        groups = nc_reader.group_data(data)

        return groups, metadata

    def _get_basetime(self, time_string):
        # grab the start date from the metadata string
        for i, char in enumerate(time_string):
            if char.isdigit():
                return time_string[:i], time_string[i:]

    def _get_snapshot_time(self, start_time: datetime = None, hours_since: int = 0):
        """
        Convert the snapshots data into the full datetime
        by combining the time and the hours since that time
        """
        if start_time is None:
            start_time = datetime("2020-01-01 00:00:00")

        target_time = start_time + timedelta(hours=int(hours_since))
        return target_time

    def get_start_end(
        self, time_data: list[int], time_string: str, num_days: int = None
    ) -> tuple[datetime, datetime]:
        # grab the base datetime from the metadata string
        _, start_date_string = self._get_basetime(time_string)
        date_format = "%Y-%m-%d %H:%M:%S"
        dt_object = datetime.strptime(start_date_string, date_format)

        # grab the starting datetime (hours since basetime)
        start_time = self._get_snapshot_time(dt_object, time_data[0])

        if num_days is None:
            hours = time_data[-1]
        else:
            ind = num_days * 24  # convert days to hours
            hours = time_data[ind]
        end_time = self._get_snapshot_time(dt_object, hours)

        return start_time, end_time

    def create_nc_skeleton(self, data_groups):
        model_data = data_skeleton.create_skeleton()
        elements = model_data["elements"]
        system = model_data["system"]

        system["name"] = "nc_data"

        # fill in bus data
        bus_data = data_groups["buses"]
        data_skeleton.add_buses(elements["bus"], bus_data)

        # fill in branch data
        branch_data = data_groups["links"]
        data_skeleton.add_branches(
            elements["branch"], elements["dc_branch"], branch_data
        )

        # fill in generator data
        gen_data = data_groups["generators"]
        carrier_data = data_groups["carriers"]
        data_skeleton.add_gens(elements["generator"], gen_data, carrier_data)

        return model_data

    def import_load_data(self, data_groups):
        load_data = data_groups["loads"]
        data_skeleton.add_loads(
            self.model_data["elements"]["load"],
            self.model_data["elements"]["bus"],
            load_data,
        )

    def import_storage_data(self, data_groups):
        storage_data = data_groups["stores"]
        data_skeleton.add_storage_data(
            self.model_data["elements"]["storage"], storage_data
        )

    def parse_to_cache(self):
        model_data = self.create_nc_skeleton(self.data_groups)

        # time data is saved in hours
        minutes_per_period = {"DAY_AHEAD": 60, "REAL_TIME": 60}
