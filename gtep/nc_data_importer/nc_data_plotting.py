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


def gather_bus_details(bus_data):
    zones = []
    num_buses = 0
    for bus_info in bus_data.values():
        zones.append(bus_info["zone"])
        num_buses += 1
    zones = set(zones)
    return zones, num_buses


def gather_branch_details(branch_data, dc_branch_data):
    num_branches = 0
    ratings_long_term = []
    capital_costs = []
    distances = []
    for branch_info in branch_data.values():
        ratings_long_term.append(float(branch_info["rating_long_term"]))
        capital_costs.append(float(branch_info["capital_cost"]))
        distances.append(float(branch_info["distance"]))
        num_branches += 1

    # dc branches
    num_dc_branches = 0
    dc_ratings_long_term = []
    dc_capital_costs = []
    dc_distances = []
    for branch_info in dc_branch_data.values():
        dc_ratings_long_term.append(float(branch_info["rating_long_term"]))
        dc_capital_costs.append(float(branch_info["capital_cost"]))
        dc_distances.append(float(branch_info["distance"]))
        num_dc_branches += 1

    # totals
    total_branches = num_branches + num_dc_branches
    total_ratings = ratings_long_term + dc_ratings_long_term
    total_capital_costs = capital_costs + dc_capital_costs
    total_distances = distances + dc_distances

    # collect into dict
    branch_details = {
        "AC": {
            "num": num_branches,
            "rating": ratings_long_term,
            "capital_cost": capital_costs,
            "distance": distances,
        },
        "DC": {
            "num": num_dc_branches,
            "rating": dc_ratings_long_term,
            "capital_cost": dc_capital_costs,
            "distance": dc_distances,
        },
        "Total": {
            "num": total_branches,
            "rating": total_ratings,
            "capital_cost": total_capital_costs,
            "distance": total_distances,
        },
    }

    return branch_details


def gather_storage_details(storage_data):
    num_storage = 0
    capacity = []
    charge_efficiency = []
    discharge_efficiency = []
    capital_costs = []
    for stor in storage_data.values():
        num_storage += 1
        capacity.append(stor["energy_capacity"])
        charge_efficiency.append(stor["charge_efficiency"])
        discharge_efficiency.append(stor["discharge_efficiency"])
        capital_costs.append(stor["investment_cost"])
    stor_details = {
        "num": num_storage,
        "capacity": capacity,
        "charge_efficiency": charge_efficiency,
        "discharge_efficiency": discharge_efficiency,
        "capital_costs": capital_costs,
    }
    return stor_details


def gen_counts_by_zone(gen_data):
    zone_count = {}
    for gen, gen_info in gen_data.items():
        if "c" in gen:
            continue
        if gen_info["zone"] not in zone_count.keys():
            zone_count[gen_info["zone"]] = {"renewable": 0, "thermal": 0, "total": 0}
        zone_count[gen_info["zone"]][gen_info["generator_type"]] += 1
        zone_count[gen_info["zone"]]["total"] += 1
    return zone_count


def gather_gen_details(gen_data):
    num_gens = 0
    num_candidates = 0
    p_max = []
    gen_type = {"renewable": 0, "thermal": 0}
    lifetime = []
    emission_factor = []
    capital_costs = []
    for gen, gen_info in gen_data.items():
        if "c" in gen:
            num_candidates += 1
            continue
        num_gens += 1
        p_max.append(gen_info["p_max"])
        gen_type[gen_info["generator_type"]] += 1
        lifetime.append(gen_info["lifetime"])
        emission_factor.append(gen_info["emissions_factor"])
        capital_costs.append(gen_info["investment_cost"])

    # collect into dict
    gen_details = {
        "num": num_gens,
        "num_candidates": num_candidates,
        "p_max": p_max,
        "gen_type": gen_type,
        "lifetime": lifetime,
        "emission_factor": emission_factor,
        "capital_costs": capital_costs,
    }
    return gen_details


def gather_details_by_zone(grid_data, excel_name=None):
    # for easier calling
    bus_data = grid_data["elements"]["bus"]
    branch_data = grid_data["elements"]["branch"]
    dc_branch_data = grid_data["elements"]["dc_branch"]
    gen_data = grid_data["elements"]["generator"]
    stor_data = grid_data["elements"]["storage"]
    # grab list of zones being used
    zones = {}
    for bus_info in bus_data.values():
        if bus_info["zone"] not in zones.keys():
            zones[bus_info["zone"]] = {"num_bus": 0}
        zones[bus_info["zone"]]["num_bus"] += 1
    # grab branch info
    for br in [branch_data, dc_branch_data]:
        for branch in br.values():
            in_zone = bus_data[branch["from_bus"]]["zone"]
            out_zone = bus_data[branch["to_bus"]]["zone"]
            for name, target in {"incoming": in_zone, "outgoing": out_zone}.items():
                if target in zones.keys():
                    for item in ["capital_cost", "distance"]:
                        if f"{name}_branch_{item}" not in zones[in_zone].keys():
                            zones[in_zone][f"{name}_branch_{item}"] = []
                        zones[in_zone][f"{name}_branch_{item}"].append(
                            float(branch[item])
                        )
    # grab gen info
    for gen in gen_data.values():
        zone = gen["zone"]
        if zone in zones.keys():
            if "gen_count" not in zones[zone].keys():
                zones[zone]["gen_count"] = 0
            if "gen_renewable_count" not in zones[zone].keys():
                zones[zone]["gen_renewable_count"] = 0
            if "gen_capital_cost" not in zones[zone].keys():
                zones[zone]["gen_capital_cost"] = []
            if "gen_emissions_factor" not in zones[zone].keys():
                zones[zone]["gen_emissions_factor"] = []
            if "gen_lifetime" not in zones[zone].keys():
                zones[zone]["gen_lifetime"] = []
            zones[zone]["gen_count"] += 1
            zones[zone]["gen_renewable_count"] += 1
            zones[zone]["gen_capital_cost"].append(float(gen["investment_cost"]))
            zones[zone]["gen_emissions_factor"].append(float(gen["emissions_factor"]))
            zones[zone]["gen_lifetime"].append(float(gen["lifetime"]))

    # grab storage data
    for stor in stor_data.values():
        stor_zone = bus_data[stor["bus"]]["zone"]
        if stor_zone in zones.keys():
            for item in ["investment_cost", "energy_capacity"]:
                if f"storage_{item}" not in zones[stor_zone].keys():
                    zones[stor_zone][f"storage_{item}"] = []
                zones[stor_zone][f"storage_{item}"].append(stor[item])

    # grab averages
    for details in zones.values():
        for name, info in details.items():
            if isinstance(info, list):
                details[name] = np.mean(info)

    if excel_name is not None:
        zone_df = None
        for zone_name, zone_dict in zones.items():
            zdf = pd.DataFrame(zone_dict, index=[zone_name])
            if zone_df is None:
                zone_df = zdf
            else:
                zone_df = pd.concat([zone_df, zdf])
        with pd.ExcelWriter(excel_name, engine="openpyxl", mode="a") as writer:
            zone_df.to_excel(writer, sheet_name="Zone Details", index=True)

    return zones


def grab_zone_costs(zone_data):
    cost_data = {}
    for zone, details in zone_data.items():
        storage = 0.0
        if "storage_investment_cost" in details.keys():
            storage = details["storage_investment_cost"]

        cost_data[zone] = {
            "Incoming Branch": details["incoming_branch_capital_cost"],
            "Outgoing Branch": details["outgoing_branch_capital_cost"],
            "Generator": details["gen_capital_cost"],
            "Storage Unit": storage,
        }
    return cost_data


def read_geojson(filepath):
    """
    Read a GeoJSON file and return its contents as a Python dict.

    Parameters
    ----------
    filepath : str
        Path to the GeoJSON file.

    Returns
    -------
    dict
        Parsed GeoJSON object.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_features(geojson_data):
    """
    Return the list of features from a GeoJSON FeatureCollection.
    """
    if geojson_data.get("type") == "FeatureCollection":
        return geojson_data.get("features", [])
    elif geojson_data.get("type") == "Feature":
        return [geojson_data]
    else:
        raise ValueError("Unsupported GeoJSON type")


def make_zone_dict(geojson_data, centroids):
    zone_data = {}
    for ix in geojson_data:
        name = ix["properties"]["countryKey"]
        countryName = ix["properties"]["countryName"]
        centroid = None
        if name in centroids.keys():
            centroid = centroids[name]
        zone_data[name] = {
            "coordinates": ix["geometry"]["coordinates"],
            "centroid": centroid,
            "countryName": countryName,
        }
    return zone_data


def polygon_centroid(coords):
    """
    Compute centroid of a single polygon using the shoelace formula.

    Parameters
    ----------
    coords : list
        A linear ring from GeoJSON polygon coordinates.
        Example: [[x1, y1], [x2, y2], ..., [x1, y1]]

    Returns
    -------
    tuple
        (centroid_x, centroid_y, area)
    """
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]

    area2 = 0.0
    cx = 0.0
    cy = 0.0

    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross

    area = area2 / 2.0

    if abs(area) < 1e-12:
        # Degenerate polygon: fallback to average of vertices
        xs = [p[0] for p in coords[:-1]]
        ys = [p[1] for p in coords[:-1]]
        return sum(xs) / len(xs), sum(ys) / len(ys), 0.0

    cx /= 3.0 * area2
    cy /= 3.0 * area2

    return cx, cy, abs(area)


def multipolygon_centroid(multipolygon_coords):
    """
    Compute centroid for a MultiPolygon by area-weighting each polygon centroid.

    Parameters
    ----------
    multipolygon_coords : list
        GeoJSON MultiPolygon coordinates:
        [
          [polygon1_rings],
          [polygon2_rings],
          ...
        ]

    Returns
    -------
    tuple
        (centroid_x, centroid_y)
    """
    total_area = 0.0
    weighted_cx = 0.0
    weighted_cy = 0.0

    for polygon in multipolygon_coords:
        outer_ring = polygon[0]  # ignore holes for simplicity
        cx, cy, area = polygon_centroid(outer_ring)

        if area > 0:
            total_area += area
            weighted_cx += cx * area
            weighted_cy += cy * area

    if total_area == 0:
        # fallback: average all polygon centroids
        centroids = [polygon_centroid(poly[0])[:2] for poly in multipolygon_coords]
        xs = [c[0] for c in centroids]
        ys = [c[1] for c in centroids]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    return weighted_cx / total_area, weighted_cy / total_area


def calculate_zone_centroids_from_geojson(geojson_data, zone_name_key="countryKey"):
    """
    Calculate centroid coordinates for each zone from a GeoJSON dictionary
    """
    centroids = {}

    for feature in geojson_data["features"]:
        zone_name = feature["properties"][zone_name_key]
        geom = feature["geometry"]

        if geom["type"] == "Polygon":
            cx, cy, _ = polygon_centroid(geom["coordinates"][0])
        elif geom["type"] == "MultiPolygon":
            cx, cy = multipolygon_centroid(geom["coordinates"])
        else:
            continue  # unsupported geometry type

        centroids[zone_name] = (cx, cy)

    return centroids


def jitter_pattern(center, n, scale):
    """
    Deterministic offsets around a center point.
    """
    cx, cy = center
    pts = []
    for i in range(n):
        angle = 2 * math.pi * i / max(n, 1)
        r = scale * (1 + 0.15 * (i % 3))
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def normalize_pt(pt):
    return (round(pt[0], 10), round(pt[1], 10))


def get_outer_rings_from_multipolygon(multipolygon_coords):
    """
    Extract outer rings from a GeoJSON MultiPolygon coordinate structure.
    Returns a list of flat rings.
    """
    return [polygon[0] for polygon in multipolygon_coords if polygon and polygon[0]]


def point_in_polygon(x, y, polygon):
    """
    Ray casting point-in-polygon test for a flat ring.
    """
    if not polygon or len(polygon) < 3:
        return False

    inside = False
    ring = polygon[:]
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]

    for i in range(len(ring) - 1):
        x0, y0 = ring[i]
        x1, y1 = ring[i + 1]

        if (y0 > y) != (y1 > y):
            xinters = (x1 - x0) * (y - y0) / (y1 - y0 + 1e-15) + x0
            if x < xinters:
                inside = not inside

    return inside


def point_in_multipolygon(x, y, multipolygon_coords):
    """
    True if the point is inside any polygon part.
    """
    for ring in get_outer_rings_from_multipolygon(multipolygon_coords):
        if point_in_polygon(x, y, ring):
            return True
    return False


def multipolygon_bounds(multipolygon_coords):
    """
    Bounds of all outer rings in a MultiPolygon.
    """
    xs = []
    ys = []

    for ring in get_outer_rings_from_multipolygon(multipolygon_coords):
        for x, y in ring:
            xs.append(x)
            ys.append(y)

    if not xs or not ys:
        raise ValueError("Empty multipolygon coordinates")

    return min(xs), min(ys), max(xs), max(ys)


def find_interior_point_near_centroid(
    centroid, multipolygon_coords, step=None, max_radius=None
):
    """
    Find one point inside the multipolygon near centroid.
    """
    pts = generate_points_around_centroid(
        centroid, multipolygon_coords, 1, step=step, max_radius=max_radius
    )
    return pts[0] if pts else centroid


def multipolygon_part_centroids(multipolygon_coords):
    centroids = []
    for polygon in multipolygon_coords:
        if not polygon or not polygon[0]:
            continue
        cx, cy, _ = polygon_centroid(polygon[0])
        centroids.append((cx, cy))
    return centroids


def point_distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def is_far_enough(candidate, points, min_sep):
    """
    Check if candidate is at least min_sep away from all existing points.
    """
    for pt in points:
        if point_distance(candidate, pt) < min_sep:
            return False
    return True


def generate_points_around_centroid(
    centroid, multipolygon_coords, num_points, step=None, max_radius=None, min_sep=None
):
    """
    Generate exactly num_points points associated with a multipolygon,
    while keeping a minimum separation between points.
    """
    if num_points <= 0:
        return []

    minx, miny, maxx, maxy = multipolygon_bounds(multipolygon_coords)
    cx, cy = centroid

    width = maxx - minx
    height = maxy - miny

    # Minimum spacing between points
    if min_sep is None:
        min_sep = max(min(width, height) / max(4 * num_points, 1), 1e-9)

    # Search step
    if step is None:
        step = max(min(width, height) / 20.0, min_sep)

    if max_radius is None:
        max_radius = max(width, height)

    points = []
    used = set()

    def add_point(x, y):
        pt = normalize_pt((x, y))
        if pt in used:
            return False

        if not point_in_multipolygon(x, y, multipolygon_coords):
            return False

        if not is_far_enough(pt, points, min_sep):
            return False

        points.append(pt)
        used.add(pt)
        return True

    # 1) centroid first
    add_point(cx, cy)

    # 2) expanding ring search
    radius = step
    while len(points) < num_points and radius <= max_radius:
        # More angles = more options around the ring
        num_angles = max(24, 12 * len(points) + 24)

        for i in range(num_angles):
            if len(points) >= num_points:
                break

            angle = 2 * math.pi * i / num_angles
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            add_point(x, y)

        radius += step

    # 3) fallback: polygon-part centroids + jitter with spacing
    if len(points) < num_points:
        for px, py in multipolygon_part_centroids(multipolygon_coords):
            if len(points) >= num_points:
                break

            add_point(px, py)

            # Try around this part centroid
            jitter_scale = max(min_sep / 2.0, 1e-9)
            for x, y in jitter_pattern((px, py), 16, jitter_scale):
                if len(points) >= num_points:
                    break
                add_point(x, y)

    # 4) final fallback: wider jitter around centroid
    if len(points) < num_points:
        jitter_scale = max(min_sep / 2.0, 1e-9)
        for x, y in jitter_pattern((cx, cy), max(48, num_points * 8), jitter_scale):
            if len(points) >= num_points:
                break
            add_point(x, y)

    # 5) absolute fallback
    if not points:
        points = [normalize_pt((cx, cy))]

    while len(points) < num_points:
        # If geometry is too tight, repeat the last point
        points.append(points[-1])

    return points


def assign_distinct_colors(items, seed=42):
    items = list(items)
    n = len(items)

    random.seed(seed)

    # Evenly spaced hues
    hues = [i / n for i in range(n)]
    random.shuffle(hues)  # helps avoid neighboring similar colors

    color_map = {}
    for item, h in zip(items, hues):
        s = 0.75  # saturation
        v = 0.95  # brightness
        color_map[item] = colorsys.hsv_to_rgb(h, s, v)

    return color_map


def assign_centroid_to_bus(bus_data, zone_data):
    bus_by_centroid = {}
    no_loc_data = []

    for zone, bus_list in bus_data.items():
        if zone not in zone_data:
            no_loc_data.append(zone)
            continue

        num_buses = len(bus_list)
        zone_centroid = zone_data[zone]["centroid"]
        zone_coords = zone_data[zone]["coordinates"]

        points = generate_points_around_centroid(
            centroid=zone_centroid,
            multipolygon_coords=zone_coords,
            num_points=num_buses,
            min_sep=0.5,
        )

        # points is guaranteed to match num_buses
        for bus, pt in zip(bus_list, points):
            bus_by_centroid[bus] = pt

    return bus_by_centroid


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


def collect_unit_types_total(gen_data):
    unit_types = []

    for gen, gen_info in gen_data.items():
        unit_types.append(gen_info["unit_type"])
    return unit_types


def collect_unit_by_zone(gen_data):
    zone_counts = {}
    for gen, gen_info in gen_data.items():
        zone = gen_info.get("zone", "Unknown")
        unit_type = gen_info.get("unit_type", "Unknown")
        if zone != "Unknown" and zone not in zone_counts.keys():
            zone_counts[zone] = {}
        if unit_type != "Unknown":
            if unit_type not in zone_counts[zone].keys():
                zone_counts[zone][unit_type] = 0
            zone_counts[zone][unit_type] += 1
    return zone_counts


def plot_fuel_pie(unit_types):
    counts = Counter(unit_types)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(counts.keys()),
                values=list(counts.values()),
                textinfo="label+percent",
            )
        ]
    )

    fig.update_layout(title="Distribution of Generators by Unit Type")
    fig.show()


def plot_fuel_by_zone(zone_units):
    # Get all zones and all unit types
    zones = sorted(zone_units.keys())
    all_unit_types = sorted(
        {unit_type for counts in zone_units.values() for unit_type in counts.keys()}
    )

    fig = go.Figure()

    for unit_type in all_unit_types:
        values = [zone_units[zone].get(unit_type, 0) for zone in zones]

        fig.add_trace(
            go.Bar(
                x=zones,
                y=values,
                name=unit_type,
            )
        )

    fig.update_layout(
        barmode="stack",
        title="Distribution of Components by Zone and Unit Type",
        xaxis_title="Zone",
        yaxis_title="Number of Generators by Unit Type",
        legend_title="Unit Type",
    )

    fig.show()


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


def plot_renewable_percentage_map(zone_data, map_style="open-street-map"):
    """
    Plot MultiPolygon zones on a Mapbox/Plotly map, coloring each zone by
    renewable generator percentage.
    """
    fig = go.Figure()

    # Gather renewable percentages
    zone_percentages = {}
    for zone_name, zone_info in zone_data.items():
        renewable_count = zone_info.get("renewable", 0)
        total_count = zone_info.get("total", 0)

        if total_count and total_count > 0:
            pct = 100.0 * renewable_count / total_count
        else:
            pct = 0.0

        zone_percentages[zone_name] = pct

    # Define colorscale and normalization range
    colorscale = "Viridis"
    cmin = min(zone_percentages.values()) if zone_percentages else 0
    cmax = max(zone_percentages.values()) if zone_percentages else 100

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
        pct = zone_percentages[zone_name]
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
                    text=f"{zone_name}<br>Renewable: {pct:.1f}%",
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
                colorbar=dict(title="Renewable %"),
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
        title="Percentage of Renewable Generators by Zone",
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


def run_grid_location_workflow(bus_data, branch_data, geojson_path=None):
    if geojson_path is None:
        geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"
    # read location data
    geojson_data = read_geojson(geojson_path)
    data = get_features(geojson_data)
    centroids = calculate_zone_centroids_from_geojson(geojson_data)

    zone_data = make_zone_dict(data, centroids)

    # grab list of zones we need with a list of buses associated
    bus_zones = {}
    for bus_name, bus_dict in bus_data.items():
        if bus_dict["zone"] not in bus_zones.keys():
            bus_zones[bus_dict["zone"]] = [bus_name]
        else:
            bus_zones[bus_dict["zone"]].append(bus_name)

    # filter zone data to ones we need
    filt_zone = {}
    for ix in zone_data.keys():
        if ix in bus_zones.keys():
            filt_zone[ix] = zone_data[ix]
            filt_zone[ix]["buses"] = bus_zones[ix]

    # grab a random color for each zone
    color_map = assign_distinct_colors(filt_zone.keys())
    for ix, val in color_map.items():
        filt_zone[ix]["color"] = val

    # find percentage renewable gen by zone
    gen_details = gen_counts_by_zone(grid_data["elements"]["generator"])

    for zone_name, renewable_vals in gen_details.items():
        if zone_name in filt_zone:
            filt_zone[zone_name].update(renewable_vals)

    bus_by_centroid = assign_centroid_to_bus(bus_zones, filt_zone)

    branch_by_centroid = assign_loc_to_branches(branch_data, bus_by_centroid)

    plot_zones_and_buses_mapbox(filt_zone, bus_by_centroid, branch_by_centroid)

    plot_renewable_percentage_map(filt_zone)


def run_unit_type_plotting_workflow(gen_data, plot_type="pie"):
    VALID_PLOT_TYPE = ["pie", "bar"]
    if plot_type.lower() not in VALID_PLOT_TYPE:
        raise KeyError(
            f"invalid plot type input: {plot_type}. Please select one of the following: {VALID_PLOT_TYPE}"
        )

    if plot_type == "pie":
        # plot total unit type distribution
        unit_types = collect_unit_types_total(gen_data)
        plot_fuel_pie(unit_types)
    elif plot_type == "bar":
        # plot unit types by zone
        zone_units = collect_unit_by_zone(gen_data)
        plot_fuel_by_zone(zone_units)


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
    #     grid_data["elements"]["bus"], grid_data["elements"]["branch"]
    # )

    # plot units
    # run_unit_type_plotting_workflow(grid_data['elements']['generator'], plot_type='bar')

    # get baseline info
    run_gather_baseline_details_workflow(
        grid_data, "/Users/bstorm/Desktop/baseline_details.xlsx"
    )

    # zone_data = gather_details_by_zone(
    #     grid_data, "/Users/bstorm/Desktop/baseline_details.xlsx"
    # )

    pass
