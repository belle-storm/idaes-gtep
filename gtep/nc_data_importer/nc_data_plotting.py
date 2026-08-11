import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import json
from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
import colorsys
import random
import math


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
        centroid = None
        if name in centroids.keys():
            centroid = centroids[name]
        zone_data[name] = {
            "coordinates": ix["geometry"]["coordinates"],
            "centroid": centroid,
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


def point_in_polygon(x, y, polygon):
    """
    Determine whether a point is inside a polygon using ray casting.

    Parameters
    ----------
    x, y : float
        Point coordinates.
    polygon : list of [x, y]
        Outer ring of the polygon. The polygon should be closed or open.

    Returns
    -------
    bool
        True if point is inside the polygon, False otherwise.
    """
    inside = False
    n = len(polygon)

    if polygon[0] != polygon[-1]:
        polygon = polygon + [polygon[0]]

    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]

        intersects = ((y0 > y) != (y1 > y)) and (
            x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-15) + x0
        )
        if intersects:
            inside = not inside

    return inside


def find_offset_point(
    centroid, polygon, used_points=None, step=0.0005, max_radius=0.01, num_angles=16
):
    """
    Find a point near centroid that lies inside polygon and is not already used.

    Parameters
    ----------
    centroid : tuple
        (x, y)
    polygon : list
        Outer ring of polygon coordinates.
    used_points : set or list
        Previously used points, rounded tuples like (x, y).
    step : float
        Radial step size.
    max_radius : float
        Maximum search radius.
    num_angles : int
        Number of angles to test at each radius.

    Returns
    -------
    tuple
        (x, y) point inside polygon, or None if not found.
    """
    if used_points is None:
        used_points = set()

    cx, cy = centroid

    # First try the centroid itself
    candidate = (cx, cy)
    if point_in_polygon(cx, cy, polygon) and candidate not in used_points:
        return candidate

    radius = step
    while radius <= max_radius:
        for i in range(num_angles):
            angle = 2 * math.pi * i / num_angles
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            candidate = (round(x, 8), round(y, 8))

            if candidate in used_points:
                continue

            if point_in_polygon(x, y, polygon):
                return candidate
        radius += step

    return None


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
    zone_used = []
    for bus_name, bus_dict in bus_data.items():
        if bus_dict["zone"] in zone_data.keys():
            if bus_dict["zone"] not in zone_used:
                bus_by_centroid[bus_name] = zone_data[bus_dict["zone"]]["centroid"]
                zone_used.append(bus_dict["zone"])
            else:
                og_centroid = zone_data[bus_dict["zone"]]["centroid"]
                new_centroid = (og_centroid[0] + 1.0, og_centroid[1] + 1.0)
                bus_by_centroid[bus_name] = new_centroid
        else:
            no_loc_data.append(bus_dict["zone"])

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
        lats = [pt[0] for pt in bus_data.values()]
        lons = [pt[1] for pt in bus_data.values()]
        for bus, loc in bus_data.items():
            ax.scatter(loc[0], loc[1], color="black", s=30, zorder=4, label=bus)

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


if __name__ == "__main__":
    # read location data
    geojson_data = read_geojson(
        "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"
    )
    data = get_features(geojson_data)
    centroids = calculate_zone_centroids_from_geojson(geojson_data)

    zone_data = make_zone_dict(data, centroids)

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
    bus_data = grid_data["elements"]["bus"]
    branch_data = grid_data["elements"]["branch"]

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

    bus_by_centroid = assign_centroid_to_bus(bus_data, filt_zone)

    branch_by_centroid = assign_loc_to_branches(branch_data, bus_by_centroid)

    plot_grid(filt_zone, bus_by_centroid, branch_by_centroid)
    pass
