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


def retrieve_zone_loc_data(geojson_path):
    # read location data
    geojson_data = read_geojson(geojson_path)
    data = get_features(geojson_data)

    return data


if __name__ == "__main__":

    geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"

    zone_data = retrieve_zone_loc_data(geojson_path)

    pass
