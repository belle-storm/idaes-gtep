"""code to request data from Grid Status and save as a csv"""

from gridstatusio import GridStatusClient
import dataset_info

# Creating API Client
client = GridStatusClient(api_key="CHANGEME")

# safety limit
QUERY_LIMIT = 10_000

# Request
data = client.get_dataset(
    dataset="ercot_spp_day_ahead_hourly",
    start="2026-01-01",
    end="2023-01-31",
    limit=QUERY_LIMIT,
    # columns=[
    #     "interval_start_utc",
    #     "interval_end_utc",
    #     "resource_name",
    #     "resource_type",
    #     "telemetered_net_output",
    # ],
    # filter_column="location",
    # filter_operator="in",
    # filter_value="HB_HOUSTON",
)

# Save data for csv

# check usage
usage = client.get_api_usage()
