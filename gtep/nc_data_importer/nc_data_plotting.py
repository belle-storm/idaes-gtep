import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import json


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


def _iter_rings(geometry):
    """
    Yield all rings from a GeoJSON-like Polygon or MultiPolygon geometry.
    Each ring is a list of [lon, lat] coordinate pairs.
    """
    gtype = geometry["type"]
    coords = geometry["coordinates"]

    if gtype == "Polygon":
        for ring in coords:
            yield ring
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield ring
    else:
        raise ValueError(f"Unsupported geometry type: {gtype}")


def plot_zones_matplotlib(
    zones,
    points=None,
    lines=None,
    figsize=(12, 8),
    extent=None,
    title="Zone Plot",
    alpha=0.4,
    edgecolor="black",
    linewidth=1.0,
):
    """
    Plot GeoJSON-like Polygon/MultiPolygon zones using matplotlib only.

    Parameters
    ----------
    zones : list
        List of dicts, each with:
            - "geometry": GeoJSON-like Polygon or MultiPolygon
            - optional "color": fill color
            - optional "name": label

    points : list, optional
        List of (lat, lon) tuples.

    lines : list, optional
        List of line coordinate sequences, each a list of (lat, lon) tuples.

    extent : list, optional
        [west, east, south, north] bounds for the plot.

    """
    fig, ax = plt.subplots(figsize=figsize)

    # Plot zones
    for zone in zones:
        geom = zone["geometry"]
        color = zone.get("color", "tab:blue")

        patches = []
        for ring in _iter_rings(geom):
            # GeoJSON uses [lon, lat], matplotlib expects x=lon, y=lat
            patches.append(MplPolygon(ring, closed=True))

        if patches:
            collection = PatchCollection(
                patches,
                facecolor=color,
                edgecolor=edgecolor,
                linewidth=linewidth,
                alpha=alpha,
            )
            ax.add_collection(collection)

    # Plot lines
    if lines:
        for line in lines:
            lats = [pt[0] for pt in line]
            lons = [pt[1] for pt in line]
            ax.plot(lons, lats, color="red", linewidth=2, zorder=3)

    # Plot points
    if points:
        lats = [pt[0] for pt in points]
        lons = [pt[1] for pt in points]
        ax.scatter(lons, lats, color="blue", s=30, zorder=4)

    # Set bounds
    if extent is not None:
        west, east, south, north = extent
        ax.set_xlim(west, east)
        ax.set_ylim(south, north)
    else:
        ax.autoscale()

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.grid(True, linewidth=0.3, alpha=0.5)

    plt.show()


if __name__ == "__main__":
    geojson_data = read_geojson(
        "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"
    )
    print(geojson_data.keys())
    data = get_features(geojson_data)
    pass
