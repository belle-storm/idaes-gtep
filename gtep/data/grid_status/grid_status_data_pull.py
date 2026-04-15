"""code to request data from Grid Status and save as a csv"""

from gridstatusio import GridStatusClient
import dataset_info

# Creating API Client
client = GridStatusClient(api_key="81eb9f596a2e4abb9d256a7287a6b668")

# safety limit
QUERY_LIMIT = 10_000

for dataset, info in dataset_info.CAISO_datasets.items():

    # Request
    data = client.get_dataset(
        dataset=dataset,
        start="2026-01-01",
        end="2026-01-31",
        limit=QUERY_LIMIT,
        columns=info["columns"]["name"],
        # filter_column="location",
        # filter_operator="in",
        # filter_value="HB_HOUSTON",
        # resample = '1 hour'
    )

    # Save data for csv
    data.to_csv(f"{dataset}.csv", index=False)
    print(f"The Dataset: {dataset} was saved as a csv")

    # check usage
    usage = client.get_api_usage()

pass
