from pathlib import Path
import os
import pandas as pd


def find_csvs(folder):
    # grab all of the csv's and organize into caiso and ercot, and by the dataset name
    root_folder = Path(folder)
    files = []
    for csv in root_folder.rglob("*.csv"):
        files.append(csv)

    caiso = {}
    ercot = {}
    for f in files:
        if "merged_csvs" in f.parts:
            continue
        name = os.path.basename(f)
        if "-" not in name:
            continue
        sections = name.split("-")
        dataset = sections[0]
        if "caiso" in dataset:
            if dataset not in caiso.keys():
                caiso[dataset] = []
            caiso[dataset].append(f)
        if "ercot" in dataset:
            if dataset not in caiso.keys():
                ercot[dataset] = []
            ercot[dataset].append(f)

    return caiso, ercot


def merge_csvs(file_dict, output_folder):
    # check that the output folder exists
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    # grab all the datasets and their files
    for dataset_name, files in file_dict.items():
        # turn each file into a dataframe
        dataframes = []
        for f in files:
            try:
                df = pd.read_csv(f)
                dataframes.append(df)
            except Exception as e:
                print(f"Could not read {f}: {e}")
        # merge dataframes together
        if dataframes:
            combined_df = pd.concat(dataframes, ignore_index=True, sort=False)

        # save to one csv
        output_file = f"{dataset_name}.csv"
        output_path = os.path.join(output_folder, output_file)
        combined_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    root_folder = r"/Volumes/redeems/Grid Status/"
    files = {"CAISO": None, "ERCOT": None}
    files["CAISO"], files["ERCOT"] = find_csvs(root_folder)
    for name in files.keys():
        output_folder = os.path.join(root_folder, f"{name}/merged_csvs/")
        merge_csvs(files[name], output_folder)

pass
