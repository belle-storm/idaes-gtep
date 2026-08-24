import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import json
from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
import colorsys
import random
import math
import plotly.graph_objects as go
from collections import Counter
from plotly.subplots import make_subplots
import numpy as np
import plotly.colors as pc
import pandas as pd


def _iter_rings(coords):
    """
    Yield all rings from a GeoJSON-like Polygon or MultiPolygon geometry.
    Each ring is a list of [lon, lat] coordinate pairs.
    """
    for polygon in coords:
        for ring in polygon:
            yield ring


def plot_grid(zone_data, bus_data=None, branch_data=None):

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot zones
    patches = []
    colors = []
    for zone, info in zone_data.items():
        geom = info["coordinates"]
        color = info["color"]

        for ring in _iter_rings(geom):
            # GeoJSON uses [lon, lat], matplotlib expects x=lon, y=lat
            patches.append(MplPolygon(ring, closed=True))
            colors.append(color)

    if patches:
        collection = PatchCollection(
            patches,
            facecolor=colors,
            edgecolor="black",
            linewidth=1.0,
            alpha=0.4,
        )
        ax.add_collection(collection)

    if bus_data:
        for bus, loc in bus_data.items():
            ax.scatter(
                loc[0],
                loc[1],
                color="black",
                edgecolors="black",
                s=15,
                zorder=4,
                alpha=0.4,
                label=bus,
            )

    if branch_data:
        for branch, loc in branch_data.items():
            ax.plot(
                loc[0],
                loc[1],
                color="black",
                linewidth=2,
                linestyle="--",
                zorder=3,
                label=branch,
            )

    ax.autoscale()

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Grid Layout")
    ax.grid(True, linewidth=0.3, alpha=0.5)

    plt.tight_layout()
    plt.savefig("zones_and_components.png", dpi=300, bbox_inches="tight")
    plt.close()


def plot_branch_comparison(ac_branch, dc_branch, total):
    fig = make_subplots(
        rows=3,
        cols=3,
        vertical_spacing=0.08,
        horizontal_spacing=0.08,
    )

    data_groups = [
        [ac_branch["rating"], ac_branch["distance"], ac_branch["capital_cost"]],
        [dc_branch["rating"], dc_branch["distance"], dc_branch["capital_cost"]],
        [total["rating"], total["distance"], total["capital_cost"]],
    ]

    row_labels = ["AC Branches", "DC Branches", "All Branches"]
    col_labels = ["Long Term Rating", "Distance", "Capital Cost"]

    colors = ["royalblue", "firebrick", "seagreen"]

    for row_idx, group in enumerate(data_groups, start=1):
        for col_idx, values in enumerate(group, start=1):
            all_values = np.array(values, dtype=float)

            bin_start = np.floor(all_values.min())
            bin_end = np.ceil(all_values.max())
            bin_size = (bin_end - bin_start) / 20

            fig.add_trace(
                go.Histogram(
                    x=values,
                    xbins=dict(
                        start=bin_start,
                        end=bin_end,
                        size=bin_size,
                    ),
                    marker_color=colors[col_idx - 1],
                    opacity=0.75,
                    showlegend=False,
                ),
                row=row_idx,
                col=col_idx,
            )

    # Add row labels on the left
    row_centers = [0.83, 0.5, 0.17]
    col_centers = [0.17, 0.5, 0.83]
    # Row labels on left
    for y, label in zip(row_centers, row_labels):
        fig.add_annotation(
            x=-0.05,
            y=y,
            xref="paper",
            yref="paper",
            text=label,
            showarrow=False,
            textangle=-90,
            xanchor="center",
            yanchor="middle",
            font=dict(size=14),
        )

    # Column labels on top
    for x, label in zip(col_centers, col_labels):
        fig.add_annotation(
            x=x,
            y=1.03,
            xref="paper",
            yref="paper",
            text=label,
            showarrow=False,
            xanchor="center",
            yanchor="bottom",
            font=dict(size=14),
        )

    fig.update_layout(
        title="Baseline Branch Details",
        bargap=0.1,
        height=900,
        width=1200,
        showlegend=False,
    )

    fig.show()


def plot_stacked_costs(cost_data):
    zones = list(cost_data.keys())

    # Collect all cost labels
    cost_labels = sorted(
        {label for zone_vals in cost_data.values() for label in zone_vals.keys()}
    )

    fig = go.Figure()

    for label in cost_labels:
        values = [cost_data[zone].get(label, 0) for zone in zones]

        fig.add_trace(
            go.Bar(
                x=zones,
                y=values,
                name=label,
            )
        )

    fig.update_layout(
        barmode="stack",
        title="Average Capital Costs by Zone and Element",
        xaxis_title="Zone",
        yaxis_title="Average Capital Cost",
        legend_title="Cost Category",
    )

    fig.show()


def run_gather_baseline_details_workflow(grid_data, excel_name=None):
    # grab basic details
    zones, num_buses = gather_bus_details(grid_data["elements"]["bus"])
    branch_details = gather_branch_details(
        grid_data["elements"]["branch"], grid_data["elements"]["dc_branch"]
    )
    gen_details = gather_gen_details(grid_data["elements"]["generator"])
    stor_details = gather_storage_details(grid_data["elements"]["storage"])
    areas = set(grid_data["elements"]["area"])
    num_areas = len(areas)
    # get stats

    # save to dictionary
    baseline_deets = {
        # totals
        "num_zones": [len(zones)],
        "num_areas": [num_areas],
        "num_buses": [num_buses],
        "num_ac_branches": [branch_details["AC"]["num"]],
        "num_dc_branches": [branch_details["DC"]["num"]],
        "num_total_branches": [branch_details["Total"]["num"]],
        "num_generators": [gen_details["num"]],
        "num_candidate_generators": [gen_details["num_candidates"]],
        "num_storage_units": [stor_details["num"]],
        # gen stats
        "percent_gen_renewable": [
            100.0 * gen_details["gen_type"]["renewable"] / gen_details["num"]
        ],
        "percent_gen_thermal": [
            100.0 * gen_details["gen_type"]["thermal"] / gen_details["num"]
        ],
        "avg_gen_p_max": [np.mean(gen_details["p_max"])],
        "avg_gen_lifetime": [np.mean(gen_details["lifetime"])],
        "avg_gen_emission": [np.mean(gen_details["emission_factor"])],
        "avg_gen_capital_cost": [np.mean(gen_details["capital_costs"])],
        "min_gen_p_max": [min(gen_details["p_max"])],
        "min_gen_lifetime": [min(gen_details["lifetime"])],
        "min_gen_emission": [min(gen_details["emission_factor"])],
        "min_gen_capital_cost": [min(gen_details["capital_costs"])],
        "max_gen_p_max": [max(gen_details["p_max"])],
        "max_gen_lifetime": [max(gen_details["lifetime"])],
        "max_gen_emission": [max(gen_details["emission_factor"])],
        "max_gen_capital_cost": [max(gen_details["capital_costs"])],
        # branch stats
        "avg_ac_branch_distance": [np.mean(branch_details["AC"]["distance"])],
        "min_ac_branch_distance": [min(branch_details["AC"]["distance"])],
        "max_ac_branch_distance": [max(branch_details["AC"]["distance"])],
        "avg_ac_branch_long_term_rating": [np.mean(branch_details["AC"]["rating"])],
        "min_ac_branch_long_term_rating": [min(branch_details["AC"]["rating"])],
        "max_ac_branch_long_term_rating": [max(branch_details["AC"]["rating"])],
        "avg_ac_branch_capital_cost": [np.mean(branch_details["AC"]["capital_cost"])],
        "min_ac_branch_capital_cost": [min(branch_details["AC"]["capital_cost"])],
        "max_ac_branch_capital_cost": [max(branch_details["AC"]["capital_cost"])],
        "avg_dc_branch_distance": [np.mean(branch_details["DC"]["distance"])],
        "min_dc_branch_distance": [min(branch_details["DC"]["distance"])],
        "max_dc_branch_distance": [max(branch_details["DC"]["distance"])],
        "avg_dc_branch_long_term_rating": [np.mean(branch_details["DC"]["rating"])],
        "min_dc_branch_long_term_rating": [min(branch_details["DC"]["rating"])],
        "max_dc_branch_long_term_rating": [max(branch_details["DC"]["rating"])],
        "avg_dc_branch_capital_cost": [np.mean(branch_details["DC"]["capital_cost"])],
        "min_dc_branch_capital_cost": [min(branch_details["DC"]["capital_cost"])],
        "max_dc_branch_capital_cost": [max(branch_details["DC"]["capital_cost"])],
        "avg_total_branch_distance": [np.mean(branch_details["Total"]["distance"])],
        "min_total_branch_distance": [min(branch_details["Total"]["distance"])],
        "max_total_branch_distance": [max(branch_details["Total"]["distance"])],
        "avg_total_branch_long_term_rating": [
            np.mean(branch_details["Total"]["rating"])
        ],
        "min_total_branch_long_term_rating": [min(branch_details["Total"]["rating"])],
        "max_total_branch_long_term_rating": [max(branch_details["Total"]["rating"])],
        "avg_total_branch_capital_cost": [
            np.mean(branch_details["Total"]["capital_cost"])
        ],
        "min_total_branch_capital_cost": [min(branch_details["Total"]["capital_cost"])],
        "max_total_branch_capital_cost": [max(branch_details["Total"]["capital_cost"])],
        # storage stats
        "avg_storage_capacity": [np.mean(stor_details["capacity"])],
        "min_storage_capacity": [min(stor_details["capacity"])],
        "max_storage_capacity": [max(stor_details["capacity"])],
        "avg_storage_charge_efficiency": [np.mean(stor_details["charge_efficiency"])],
        "min_storage_charge_efficiency": [min(stor_details["charge_efficiency"])],
        "max_storage_charge_efficiency": [max(stor_details["charge_efficiency"])],
        "avg_storage_discharge_efficiency": [
            np.mean(stor_details["discharge_efficiency"])
        ],
        "min_storage_discharge_efficiency": [min(stor_details["discharge_efficiency"])],
        "max_storage_discharge_efficiency": [max(stor_details["discharge_efficiency"])],
        "avg_storage_capital_costs": [np.mean(stor_details["capital_costs"])],
        "min_storage_capital_costs": [min(stor_details["capital_costs"])],
        "max_storage_capital_costs": [max(stor_details["capital_costs"])],
    }
    # turn into dataframe
    stats_df = pd.DataFrame(baseline_deets, index=["value"])
    flipped_df = stats_df.T
    # save to excel sheet
    if excel_name is None:
        excel_name = "baseline_details.xlsx"
    with pd.ExcelWriter(excel_name, engine="openpyxl", mode="a") as writer:
        flipped_df.to_excel(writer, sheet_name="Whole Grid", index=True)


def run_cost_plotting_workflow(grid_data):
    zone_data = gather_details_by_zone(grid_data)
    costs_by_zone = grab_zone_costs(zone_data)
    plot_stacked_costs(costs_by_zone)


if __name__ == "__main__":

    # Open grid data
    data_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/"
    data_object = NCExpansionPlanningData(
        stages=2,
        num_reps=2,
        len_reps=1,
        num_commit=6,
        num_dispatch=4,
        duration_dispatch=15,
    )
    data_object.load_nc_data(data_path)

    # grab grid data elements
    grid_data = data_object.md.data

    # plot grid by location
    # run_grid_location_workflow(
    #     grid_data["elements"]["bus"], grid_data["elements"]["branch"], percent=False
    # )

    # plot units
    run_unit_type_plotting_workflow(
        grid_data["elements"]["generator"], plot_type="bar", percent=True
    )
    # run_unit_type_plotting_workflow(
    #     grid_data["elements"]["generator"], plot_type="pie", percent=False
    # )
    # geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"
    # # read location data
    # geojson_data = read_geojson(geojson_path)
    # data = get_features(geojson_data)
    # centroids = calculate_zone_centroids_from_geojson(geojson_data)

    # zone_data = make_zone_dict(data, centroids)
    # zone_units = collect_unit_by_zone(grid_data["elements"]["generator"], percent=False)
    # for zone, unit_info in zone_units.items():
    #     country = zone_data[zone]["countryName"]
    #     title = f"{country}: Distribution of Generation Capacity (MW) by Unit Type"
    #     plot_fuel_pie(unit_info, title)

    # get baseline info
    # run_gather_baseline_details_workflow(
    #     grid_data, "/Users/bstorm/Desktop/baseline_details.xlsx"
    # )

    # zone_data = gather_details_by_zone(
    #     grid_data,
    #     # "/Users/bstorm/Desktop/baseline_details.xlsx"
    # )
    # gen_deets = {}
    # for zone, deets in zone_data.items():
    #     gen_deets[zone] = {
    #         "num": deets["gen_count"],
    #         "num_ren": deets["gen_renewable_count"],
    #         "percent_ren": 100.0 * deets["gen_renewable_count"] / deets["gen_count"],
    #     }
    pass
