from pathlib import Path
import os
import pandas as pd


def find_csvs(folder):
    # grab all of the csv's and organize into caiso and ercot, and by the dataset name
    root_folder = Path(folder)
    files = []
    for csv in root_folder.rglob("*.csv"):
        files.append(csv)
    return files


def find_gaps_in_csv(file_path):
    df = pd.read_csv(file_path)
    gaps = []
    if "interval_start_utc" in df.columns:
        if "interval_end_utc" in df.columns:
            # Parse datetimes
            df["interval_start_utc"] = pd.to_datetime(
                df["interval_start_utc"], utc=True, errors="coerce"
            )
            df["interval_end_utc"] = pd.to_datetime(
                df["interval_end_utc"], utc=True, errors="coerce"
            )

            # Drop rows with invalid dates
            df = df.dropna(subset=["interval_start_utc", "interval_end_utc"])

            # Sort by interval start
            df = df.sort_values("interval_start_utc").reset_index(drop=True)

            for i in range(1, len(df)):
                prev_end = df.loc[i - 1, "interval_end_utc"]
                curr_start = df.loc[i, "interval_start_utc"]

                if curr_start > prev_end:
                    gap_duration = curr_start - prev_end
                    if gap_duration >= pd.Timedelta(days=1):
                        gaps.append(
                            {
                                "gap_start": prev_end,
                                "gap_end": curr_start,
                                "gap_duration": curr_start - prev_end,
                            }
                        )
    elif "sced_timestamp_utc" in df.columns:
        timestamp_col = "sced_timestamp_utc"
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")

        # Drop invalid timestamps
        df = df.dropna(subset=[timestamp_col])

        # Sort by time
        df = df.sort_values(timestamp_col).reset_index(drop=True)

        for i in range(1, len(df)):
            prev_time = df.loc[i - 1, timestamp_col]
            curr_time = df.loc[i, timestamp_col]

            gap = curr_time - prev_time

            if gap > pd.Timedelta(days=1):
                gaps.append(
                    {"gap_start": prev_time, "gap_end": curr_time, "gap_duration": gap}
                )

    return gaps


if __name__ == "__main__":

    for group in ["ERCOT", "CAISO"]:
        gap_data = {}
        root_folder = f"/Volumes/redeems/Grid Status/{group}/merged_csvs/"
        files = find_csvs(root_folder)
        for f in files:
            dataset_name = os.path.basename(f)
            name, ext = dataset_name.split(".")
            gap_data[name] = find_gaps_in_csv(f)
        for dname, gap_list in gap_data.items():
            if not gap_list:
                continue

            f_df = pd.DataFrame(gap_list)
            f_df.to_csv(
                f"/Volumes/redeems/Grid Status/{group}/QA_gaps/{dname}_gaps.csv",
                index=True,
            )
