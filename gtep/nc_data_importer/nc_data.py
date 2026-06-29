from gtep.gtep_data import ExpansionPlanningData
from gtep.nc_data_importer.nc_data_importer import NCDataProvider


class NCExpansionPlanningData(ExpansionPlanningData):
    def __init__(
        self,
        stages=2,
        num_reps=4,
        len_reps=1,
        num_commit=24,
        num_dispatch=1,
        duration_dispatch=60,
    ):
        super().__init__(
            stages, num_reps, len_reps, num_commit, num_dispatch, duration_dispatch
        )

        self.data_type = "nc_data"

    def _build_rep_dates(md, dates, weights, num_days, stages, period_per_step):
        if weights is None:
            # set the weight for each day to the total weight divided by number of days
            total_weight = num_days * stages
            weight_per_date = int(total_weight / (len(dates)))
            representative_weights = {
                key: weight_per_date for date, key in enumerate(dates)
            }

        time_keys = md.data["system"]["time_keys"]

        data_list = []

        for date in dates:
            key_idx = time_keys.index(date)
            time_key_set = time_keys[key_idx : key_idx + period_per_step]
            data_list.append(md.clone_at_time_keys(time_key_set))

        representative_data = data_list

        return representative_weights, representative_data

    def load_nc_data(self, nc_file, options_dict=None):

        if options_dict is None:
            options_dict = {"data_path": nc_file}
        else:
            options_dict["data_path"] = nc_file

        data_provider = NCDataProvider(options=options_dict)

    def import_load_data(self):
        pass

    def import_storage_data(self):
        pass
