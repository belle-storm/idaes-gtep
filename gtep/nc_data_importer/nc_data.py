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
