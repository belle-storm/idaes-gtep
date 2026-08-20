"""
gtep.nc_data_importer.geojson_reader

Read and Format GeoJson data
"""

import json


def read_geojson(filepath):
    """
    Read a GeoJSON file and return its contents as a Python dict.
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


def polygon_centroid(coords):
    """
    Compute centroid of a single polygon using the shoelace formula.
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


def make_zone_dict(geojson_data, centroids):
    zone_data = {}
    for ix in geojson_data:
        name = ix["properties"]["zoneName"]
        centroid = None
        if name in centroids.keys():
            centroid = centroids[name]
        zone_data[name] = {
            "geometry": ix["geometry"],
            "centroid": centroid,
        }
        if "countryName" in ix["properties"].keys():
            zone_data[name]["countryName"] = ix["properties"]["countryName"]
        if "countryKey" in ix["properties"].keys():
            zone_data[name]["countryKey"] = ix["properties"]["countryKey"]
    return zone_data


def retrieve_zone_loc_data(geojson_path, zone_name_key="zoneName"):
    # read location data
    geojson_data = read_geojson(geojson_path)
    data = get_features(geojson_data)
    centroids = calculate_zone_centroids_from_geojson(geojson_data, zone_name_key)

    zone_data = make_zone_dict(data, centroids)
    return zone_data


if __name__ == "__main__":

    geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"

    zone_data = retrieve_zone_loc_data(geojson_path)

    pass
