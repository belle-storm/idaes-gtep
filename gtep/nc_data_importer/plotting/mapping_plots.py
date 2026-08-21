import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
import plotly.graph_objects as go
import plotly.colors as pc
import gtep.nc_data_importer.geojson_reader as geo
import gtep.nc_data_importer.plotting.helpers as plt_help

def bus_by_zone(bus_data):
    #grab the bus in each zone and area
    bus_zones = {}
    bus_areas = {}
    for bus_name, bus_dict in bus_data.items():
        country = bus_dict["zone"]
        area = bus_name.split(" ")[0]

        #save country
        if country not in bus_zones.keys():
            bus_zones[country] = [bus_name]
        else:
            bus_zones[country].append(bus_name)
        #save area
        if area not in bus_areas.keys():
            bus_areas[area] = [bus_name]
        else:
            bus_areas[area].append(bus_name)

    return bus_zones, bus_areas

def gen_by_zone(gen_data):
    #grab the gen in each zone and area
    gen_zones = {}
    gen_areas = {}
    for gen_name, gen_dict in gen_data.items():
        if "c" in gen_name:
            continue
        country = gen_dict["zone"]
        area = gen_name.split(" ")[0]
        capacity = gen_dict["p_max"]
        gen_type = gen_dict["generator_type"]

        gen_info = {gen_name: {"type": gen_type, "capacity": capacity}}
    
        #save country
        if country not in gen_zones.keys():
            gen_zones[country] = [gen_info]
        else:
            gen_zones[country].append(gen_info)
        #save area
        if area not in gen_areas.keys():
            gen_areas[area] = [gen_info]
        else:
            gen_areas[area].append(gen_info)
    
    return gen_zones, gen_areas

def components_by_zone(zone_data, grid_data):
    #filter zones by matching countries and assign components to zone
    bus_zone, bus_area = bus_by_zone(grid_data['elements']['bus'])
    gen_zone, gen_area = gen_by_zone(grid_data['elements']['generator'])

    #filter zones to include full countries even if no buses in that area
    filt_zone = {}
    for z, info in zone_data.items():
        if info['countryKey'] in bus_zone.keys():
            filt_zone[z] = info
            filt_zone[z]['buses'] = []
        if info['countryKey'] in gen_zone.keys():
            if z not in filt_zone.keys():
                filt_zone[z] = info
            filt_zone[z]['gens'] = []

    #save buses to their zones
    match_status = {i: False for i in bus_area.keys()}
    for z in zone_data.keys():
        for ix in bus_area.keys():
            if ix in z:
                filt_zone[z]["buses"] = bus_area[ix]
                match_status[ix] = True
        for g in gen_area.keys():
            if g in z:
                filt_zone[z]['gens'] = gen_area[g]
    #catch stragglers and assign to any country zone that matches
    for key, status in match_status.items():
        if not status:
            new_key = key[:-1]
            for z in filt_zone.keys():
                if new_key in z:
                    filt_zone[z]['buses'] = bus_area[key]
                    #debug check that everything found a home
                    match_status[key] = True
                    break

    return filt_zone

def gen_counts_by_zone(filt_zones):
    #add capacity info by zone for each type
    for z, info in filt_zones.items():
        gen_data = info['gens']
        capacity = {"renewable": 0, "thermal": 0, "total": 0}
        for g in gen_data:
            capacity['total'] += g['capacity']
            capacity[g['type']] += g['capacity']
        filt_zones[z]['total_generation'] = capacity['total']
        filt_zones[z]['renewable_generation'] = capacity['renewable']
        filt_zones[z]['thermal_generation'] = capacity['thermal']

    zone_count = {}
    for gen, gen_info in gen_data.items():
        if "c" in gen:
            continue
        if gen_info["zone"] not in zone_count.keys():
            zone_count[gen_info["zone"]] = {"renewable": 0, "thermal": 0, "total": 0}
        capacity = gen_info["p_max"]
        zone_count[gen_info["zone"]][gen_info["generator_type"]] += capacity
        zone_count[gen_info["zone"]]["total"] += capacity
    return zone_count


def assign_centroid_to_bus(filt_zones):
    updated_zones = filt_zones
    for zone, info in filt_zones:
        bus_list = info['buses']
        num_buses = len(bus_list)
        zone_centroid = zone_data[zone]["centroid"]
        zone_coords = zone_data[zone]["coordinates"]

        points = plt_help.generate_points_around_centroid(
            centroid=zone_centroid,
            multipolygon_coords=zone_coords,
            num_points=num_buses,
            min_sep=0.5,
        )

        # points is guaranteed to match num_buses
        bus_data = {}
        for bus, pt in zip(bus_list, points):
            bus_data[bus] = pt
        #replace bus list with assigned dictionary
        updated_zones[zone]['buses'] = bus_data

    return updated_zones


def assign_loc_to_branches(branch_data, bus_centroids):
    branch_by_centroid = {}
    for branch, info in branch_data.items():
        if info["from_bus"] in bus_centroids.keys():
            if info["to_bus"] in bus_centroids.keys():
                lat = [
                    bus_centroids[info["from_bus"]][0],
                    bus_centroids[info["to_bus"]][0],
                ]
                lon = [
                    bus_centroids[info["from_bus"]][1],
                    bus_centroids[info["to_bus"]][1],
                ]

                branch_by_centroid[branch] = (lat, lon)
    return branch_by_centroid


def plot_grid(zone_data, bus_data=None, branch_data=None):

    fig, ax = plt.subplots(figsize=(12, 8))

    # Plot zones
    patches = []
    colors = []
    for zone, info in zone_data.items():
        geom = info["coordinates"]
        color = info["color"]

        for ring in plt_help._iter_rings(geom):
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


def plot_zones_and_buses_mapbox(
    zone_data,
    bus_positions,
    branch_data=None,
    zone_colors=None,
    zone_legend=True,
    map_style="open-street-map",
):
    """
    Plot MultiPolygon zones and bus points on a Mapbox/Plotly map.
    """
    fig = go.Figure()

    # uncomment to switch to adding each country to the legend
    # Track which zone legends have already been added
    # seen_zones = set()
    first_trace_for_zone = True

    # Add zones as filled polygon traces
    for i, (zone_name, zone_info) in enumerate(zone_data.items()):
        coords = zone_info["coordinates"]
        country = zone_info["countryName"]
        color = zone_colors.get(zone_name, None) if zone_colors else None
        if color is None:
            color = (
                f"rgba({50 + (i*40)%200}, {100 + (i*70)%155}, {180 + (i*30)%75}, 0.35)"
            )

        # uncomment to switch to adding each country to the legend
        # check if this zone has already been added
        # first_trace_for_zone = False
        # if zone_legend:
        #    first_trace_for_zone = zone_name not in seen_zones

        # MultiPolygon -> multiple polygon parts
        for poly in coords:
            if not poly or not poly[0]:
                continue

            outer_ring = poly[0]
            lons = [pt[0] for pt in outer_ring]
            lats = [pt[1] for pt in outer_ring]

            # Close ring if needed
            if lons[0] != lons[-1] or lats[0] != lats[-1]:
                lons.append(lons[0])
                lats.append(lats[0])

            fig.add_trace(
                go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode="lines",
                    fill="toself",
                    fillcolor=color,
                    line=dict(color="black", width=1),
                    # switch lines to switch to adding each country to the legend
                    # name=country,
                    name="Zones",
                    hoverinfo="text",
                    text=zone_name,
                    showlegend=first_trace_for_zone,
                )
            )
            # switch lines to switch to adding each country to the legend
            # add zone to the seen zones set
            # seen_zones.add(zone_name)
            first_trace_for_zone = False

    # Add bus points
    bus_lons = []
    bus_lats = []
    bus_text = []

    for bus_name, (lon, lat) in bus_positions.items():
        bus_lons.append(lon)
        bus_lats.append(lat)
        bus_text.append(bus_name)

    fig.add_trace(
        go.Scattermapbox(
            lon=bus_lons,
            lat=bus_lats,
            mode="markers+text",
            marker=dict(size=10, color="rgba(255, 0, 0, 0.5)"),
            # text=bus_text,
            # textposition="top center",
            name="Buses",
        )
    )

    if branch_data:
        branch_legend_added = False
        for branch, loc in branch_data.items():
            fig.add_trace(
                go.Scattermapbox(
                    lon=loc[0],
                    lat=loc[1],
                    mode="lines",
                    line=dict(color="rgba(0, 0, 0, 0.5)", width=1),
                    name="Branches",
                    legendgroup="Branches",
                    showlegend=not branch_legend_added,
                )
            )
            branch_legend_added = True

    # Center map on data
    all_lons = []
    all_lats = []

    for zone_info in zone_data.values():
        for poly in zone_info["coordinates"]:
            if not poly or not poly[0]:
                continue
            for pt in poly[0]:
                all_lons.append(pt[0])
                all_lats.append(pt[1])

    all_lons.extend(bus_lons)
    all_lats.extend(bus_lats)

    if all_lons and all_lats:
        center_lon = sum(all_lons) / len(all_lons)
        center_lat = sum(all_lats) / len(all_lats)
    else:
        center_lon, center_lat = 0, 0

    fig.update_layout(
        mapbox=dict(
            style=map_style, center=dict(lon=center_lon, lat=center_lat), zoom=8
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        title="Baseline Branches and Buses by Country Zone",
    )

    fig.show()


def plot_renewable_percentage_map(zone_data, map_style="open-street-map", percent=True):
    """
    Plot MultiPolygon zones on a Mapbox/Plotly map, coloring each zone by
    renewable generator percentage.
    """
    fig = go.Figure()

    if not percent:
        title = "Renewable Generation Capacity by Zone"
        unit_label = "Capacity (MW)"
        # Gather renewable capacities
        zone_renewables = {}
        for zone_name, zone_info in zone_data.items():
            renewable_capacity = zone_info.get("renewable", 0)
            zone_renewables[zone_name] = renewable_capacity

    else:
        title = "Percentage of Generation Capacity from Renewables by Zone"
        unit_label = "%"
        # Gather renewable percentages
        zone_renewables = {}
        for zone_name, zone_info in zone_data.items():
            renewable_count = zone_info.get("renewable", 0)
            total_count = zone_info.get("total", 0)

            if total_count and total_count > 0:
                pct = 100.0 * renewable_count / total_count
            else:
                pct = 0.0

            zone_renewables[zone_name] = pct

    # Define colorscale and normalization range
    colorscale = "Viridis"
    cmin = min(zone_renewables.values()) if zone_renewables else 0
    cmax = max(zone_renewables.values()) if zone_renewables else 100

    def pct_to_color(pct):
        if cmax == cmin:
            normalized = 0.5  # or 0.0, depending on the color you want
        else:
            normalized = (pct - cmin) / (cmax - cmin)

        normalized = max(0, min(1, normalized))
        return pc.sample_colorscale(colorscale, [normalized])[0]

    # Add zones as filled polygon traces
    for zone_name, zone_info in zone_data.items():
        coords = zone_info["coordinates"]
        pct = zone_renewables[zone_name]
        fill_color = pct_to_color(pct)

        for poly in coords:
            if not poly or not poly[0]:
                continue

            outer_ring = poly[0]
            lons = [pt[0] for pt in outer_ring]
            lats = [pt[1] for pt in outer_ring]

            # Close ring if needed
            if lons[0] != lons[-1] or lats[0] != lats[-1]:
                lons.append(lons[0])
                lats.append(lats[0])

            fig.add_trace(
                go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode="lines",
                    fill="toself",
                    fillcolor=fill_color,
                    line=dict(color="black", width=1),
                    name=zone_name,
                    hoverinfo="text",
                    text=f"{zone_name}<br>Renewable: {pct:.1f}{unit_label}",
                    showlegend=False,
                )
            )

    # Add a dummy trace only for the colorbar
    fig.add_trace(
        go.Scattermapbox(
            lon=[None],
            lat=[None],
            mode="markers",
            marker=dict(
                size=10,
                color=[0, 100],
                cmin=cmin,
                cmax=cmax,
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(title=f"Renewable {unit_label}"),
            ),
            showlegend=False,
            hoverinfo="none",
        )
    )

    # Center map on data
    all_lons = []
    all_lats = []

    for zone_info in zone_data.values():
        for poly in zone_info["coordinates"]:
            if not poly or not poly[0]:
                continue
            for pt in poly[0]:
                all_lons.append(pt[0])
                all_lats.append(pt[1])

    if all_lons and all_lats:
        center_lon = sum(all_lons) / len(all_lons)
        center_lat = sum(all_lats) / len(all_lats)
    else:
        center_lon, center_lat = 0, 0

    fig.update_layout(
        mapbox=dict(
            style=map_style,
            center=dict(lon=center_lon, lat=center_lat),
            zoom=8,
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        title=title,
    )

    fig.show()


def run_grid_location_workflow(bus_data, branch_data, geojson_path=None, percent=True):
    if geojson_path is None:
        geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"

    zone_data = geo.retrieve_zone_loc_data(geojson_path)

    # grab list of zones we need with a list of buses associated
    bus_zones = {}
    bus_areas = {}
    for bus_name, bus_dict in bus_data.items():
        if bus_dict["zone"] not in bus_zones.keys():
            bus_zones[bus_dict["zone"]] = [bus_name]
        else:
            bus_zones[bus_dict["zone"]].append(bus_name)
        area = bus_name.split(" ")[0]
        #area = f'{area[:-2]}_{area[-1]}'
        if area not in bus_areas.keys():
            bus_areas[area] = [bus_name]
        else:
            bus_areas[area].append(bus_name)

    # filter zone data to ones we need
    filt_zone = {}
    for z in zone_data.keys():
        target_loc = bus_zones
        if '-' in z:
            target_loc = bus_areas
        for ix in target_loc.keys():
            if ix in z:
                filt_zone[z] = zone_data[z]
                filt_zone[z]["buses"] = target_loc[ix]

    # grab a random color for each zone
    color_map = plt_help.assign_distinct_colors(filt_zone.keys())
    for ix, val in color_map.items():
        filt_zone[ix]["color"] = val

    # find percentage renewable gen by zone
    gen_details = gen_counts_by_zone(grid_data["elements"]["generator"])

    for zone_name, renewable_vals in gen_details.items():
        if zone_name in filt_zone:
            filt_zone[zone_name].update(renewable_vals)

    # bus_by_centroid = assign_centroid_to_bus(bus_zones, filt_zone)

    # branch_by_centroid = assign_loc_to_branches(branch_data, bus_by_centroid)

    # plot_zones_and_buses_mapbox(filt_zone, bus_by_centroid, branch_by_centroid)

    plot_zones(filt_zone)

    # plot_renewable_percentage_map(filt_zone, percent=percent)


def plot_zones(
    zone_data,
    map_style="open-street-map",
):
    """
    Plot Polygon and MultiPolygon zones on a Mapbox/Plotly map.
    """
    fig = go.Figure()
    first_trace_for_zone = True

    # Collect all coordinates for centering the map
    all_lons = []
    all_lats = []

    for i, (zone_name, zone_info) in enumerate(zone_data.items()):
        geometry = zone_info["geometry"]
        coords = geometry["coordinates"]
        geo_type = geometry["type"]

        color = f"rgba({50 + (i*40)%200}, {100 + (i*70)%155}, {180 + (i*30)%75}, 0.35)"

        # Normalize to a list of polygon parts:
        # - Polygon: coords = [outer_ring, hole1, hole2, ...]
        # - MultiPolygon: coords = [[outer_ring, ...], [outer_ring, ...], ...]
        if geo_type == "Polygon":
            polygon_parts = [coords]
        elif geo_type == "MultiPolygon":
            polygon_parts = coords
        else:
            # Skip unsupported geometry types
            continue

        for poly in polygon_parts:
            if not poly or not poly[0]:
                continue

            outer_ring = poly[0]
            lons = [pt[0] for pt in outer_ring]
            lats = [pt[1] for pt in outer_ring]

            # Close ring if needed
            if lons[0] != lons[-1] or lats[0] != lats[-1]:
                lons.append(lons[0])
                lats.append(lats[0])

            # Add to centering lists
            all_lons.extend(lons)
            all_lats.extend(lats)

            fig.add_trace(
                go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode="lines",
                    fill="toself",
                    fillcolor=color,
                    line=dict(color="black", width=1),
                    name=zone_name,
                    hoverinfo="text",
                    text=zone_name,
                    showlegend=first_trace_for_zone,
                )
            )

            first_trace_for_zone = False

    # Center map on data
    if all_lons and all_lats:
        center_lon = sum(all_lons) / len(all_lons)
        center_lat = sum(all_lats) / len(all_lats)
    else:
        center_lon, center_lat = 0, 0

    fig.update_layout(
        mapbox=dict(
            style=map_style,
            center=dict(lon=center_lon, lat=center_lat),
            zoom=8,
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        title="Zones",
    )

    fig.show()


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

    geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"
    # geojson_path = (
    #     "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_entsoepy.geojson"
    # )

    zone_data = geo.retrieve_zone_loc_data(geojson_path)
    components_by_zone(zone_data, grid_data)
    # run_grid_location_workflow(
    #     grid_data["elements"]["bus"], grid_data["elements"]["branch"], geojson_path
    # )

    pass
