# zones = [
#     {
#         "name": "Zone A",
#         "boundary": [(lat1, lon1), (lat2, lon2), (lat3, lon3), ...],
#         "components": [
#             {"id": "C1", "lat": 35.1, "lon": -106.6, "status": "connected"},
#             {"id": "C2", "lat": 35.2, "lon": -106.7, "status": "disconnected_nearby"},
#         ],
#     },
#     {
#         "name": "Zone B",
#         "boundary": [(lat1, lon1), (lat2, lon2), ...],
#         "components": [...],
#     }
# ]

# edges = [
#     ("C1", "C3"),
#     ("C3", "C4"),
# ]

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import LineCollection

def plot_zones_and_components(zones, edges=None, figsize=(10, 8), title="Component Map"):
    """
    Plot zones, components, and connections on a latitude/longitude scatter map.

    Parameters
    ----------
    zones : list of dict
        Each dict should contain:
          - "name": str
          - "boundary": list of (lat, lon) tuples
          - "components": list of dicts with keys:
                - "id": str
                - "lat": float
                - "lon": float
                - "status": str, e.g. "connected" or "disconnected_nearby"
    edges : list of tuple, optional
        List of ("component_id_1", "component_id_2") connections.
    figsize : tuple
        Figure size.
    title : str
        Plot title.
    """
    if edges is None:
        edges = []

    fig, ax = plt.subplots(figsize=figsize)

    # Build lookup of component positions
    comp_lookup = {}
    for zone in zones:
        for comp in zone["components"]:
            comp_lookup[comp["id"]] = comp

    # Plot zone shading
    for i, zone in enumerate(zones):
        boundary = zone["boundary"]
        # Note: Polygon expects (x, y) -> (lon, lat)
        poly_coords = [(lon, lat) for lat, lon in boundary]
        polygon = Polygon(
            poly_coords,
            closed=True,
            facecolor=f"C{i}",
            alpha=0.15,
            edgecolor=f"C{i}",
            linewidth=2,
            label=zone["name"]
        )
        ax.add_patch(polygon)

    # Plot lines for connected components
    line_segments = []
    for a, b in edges:
        if a in comp_lookup and b in comp_lookup:
            c1 = comp_lookup[a]
            c2 = comp_lookup[b]
            line_segments.append([(c1["lon"], c1["lat"]), (c2["lon"], c2["lat"])])

    if line_segments:
        lc = LineCollection(line_segments, colors="black", linewidths=1.5, alpha=0.8)
        ax.add_collection(lc)

    # Plot components
    for zone in zones:
        connected_lats = []
        connected_lons = []
        nearby_lats = []
        nearby_lons = []

        for comp in zone["components"]:
            if comp.get("status") == "disconnected_nearby":
                nearby_lats.append(comp["lat"])
                nearby_lons.append(comp["lon"])
            else:
                connected_lats.append(comp["lat"])
                connected_lons.append(comp["lon"])

        # Connected components
        ax.scatter(
            connected_lons, connected_lats,
            s=60, marker="o", c="blue", edgecolors="white",
            linewidths=0.8, zorder=3
        )

        # Nearby disconnected components
        ax.scatter(
            nearby_lons, nearby_lats,
            s=80, marker="X", c="red", edgecolors="white",
            linewidths=0.8, zorder=4
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_aspect("equal", adjustable="box")

    plt.tight_layout()
    return fig, ax

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Polygon
from matplotlib.collections import LineCollection

def plot_zones_and_components_cartopy(zones, edges=None, title="Component Map",
                                      projection=ccrs.PlateCarree(),
                                      figsize=(12, 8)):
    """
    Plot zones, components, and connections using Cartopy.

    Parameters
    ----------
    zones : list of dict
        Each dict should contain:
          - "name": str
          - "boundary": list of (lat, lon) tuples
          - "components": list of dicts with keys:
                - "id": str
                - "lat": float
                - "lon": float
                - "status": str, e.g. "connected" or "disconnected_nearby"
    edges : list of tuple, optional
        List of ("component_id_1", "component_id_2") connections.
    title : str
        Plot title.
    projection : cartopy.crs projection
        Map projection used for the axes.
    figsize : tuple
        Figure size.
    """
    if edges is None:
        edges = []

    fig = plt.figure(figsize=figsize)
    ax = plt.axes(projection=projection)

    # Base map features
    ax.add_feature(cfeature.LAND, facecolor="lightgray", alpha=0.3)
    ax.add_feature(cfeature.OCEAN, facecolor="lightblue", alpha=0.15)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, alpha=0.5)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, alpha=0.5)
    ax.add_feature(cfeature.STATES, linewidth=0.4, alpha=0.4)

    # Build component lookup
    comp_lookup = {}
    for zone in zones:
        for comp in zone["components"]:
            comp_lookup[comp["id"]] = comp

    # Plot zone polygons
    for i, zone in enumerate(zones):
        boundary = zone["boundary"]
        lats = [p[0] for p in boundary]
        lons = [p[1] for p in boundary]

        poly_coords = list(zip(lons, lats))  # lon, lat for plotting

        polygon = Polygon(
            poly_coords,
            closed=True,
            facecolor=f"C{i}",
            edgecolor=f"C{i}",
            alpha=0.20,
            linewidth=2,
            transform=ccrs.PlateCarree(),
            label=zone["name"]
        )
        ax.add_patch(polygon)

    # Plot lines for connected components
    line_segments = []
    for a, b in edges:
        if a in comp_lookup and b in comp_lookup:
            c1 = comp_lookup[a]
            c2 = comp_lookup[b]
            line_segments.append([(c1["lon"], c1["lat"]), (c2["lon"], c2["lat"])])

    if line_segments:
        lc = LineCollection(
            line_segments,
            colors="black",
            linewidths=1.5,
            alpha=0.8,
            transform=ccrs.PlateCarree()
        )
        ax.add_collection(lc)

    # Plot components
    connected_lons, connected_lats = [], []
    nearby_lons, nearby_lats = [], []

    for zone in zones:
        for comp in zone["components"]:
            if comp.get("status") == "disconnected_nearby":
                nearby_lons.append(comp["lon"])
                nearby_lats.append(comp["lat"])
            else:
                connected_lons.append(comp["lon"])
                connected_lats.append(comp["lat"])

    ax.scatter(
        connected_lons, connected_lats,
        s=60, marker="o", c="blue",
        edgecolors="white", linewidths=0.8,
        transform=ccrs.PlateCarree(),
        zorder=5,
        label="Connected component"
    )

    ax.scatter(
        nearby_lons, nearby_lats,
        s=90, marker="X", c="red",
        edgecolors="white", linewidths=0.8,
        transform=ccrs.PlateCarree(),
        zorder=6,
        label="Nearby disconnected"
    )

    # Set map extent based on all points/boundaries
    all_lats = []
    all_lons = []
    for zone in zones:
        for lat, lon in zone["boundary"]:
            all_lats.append(lat)
            all_lons.append(lon)
        for comp in zone["components"]:
            all_lats.append(comp["lat"])
            all_lons.append(comp["lon"])

    if all_lats and all_lons:
        pad = 0.05
        ax.set_extent(
            [min(all_lons) - pad, max(all_lons) + pad,
             min(all_lats) - pad, max(all_lats) + pad],
            crs=ccrs.PlateCarree()
        )

    ax.set_title(title)
    ax.legend(loc="upper right")
    plt.tight_layout()
    return fig, ax

#EXAMPLE USAGE
# zones = [
#     {
#         "name": "Zone A",
#         "boundary": [(35.0, -106.8), (35.0, -106.5), (35.3, -106.5), (35.3, -106.8)],
#         "components": [
#             {"id": "C1", "lat": 35.10, "lon": -106.75, "status": "connected"},
#             {"id": "C2", "lat": 35.18, "lon": -106.70, "status": "connected"},
#             {"id": "C3", "lat": 35.22, "lon": -106.62, "status": "disconnected_nearby"},
#         ],
#     },
#     {
#         "name": "Zone B",
#         "boundary": [(35.35, -106.9), (35.35, -106.6), (35.55, -106.6), (35.55, -106.9)],
#         "components": [
#             {"id": "C4", "lat": 35.42, "lon": -106.80, "status": "connected"},
#             {"id": "C5", "lat": 35.47, "lon": -106.72, "status": "connected"},
#         ],
#     }
# ]

# edges = [("C1", "C2"), ("C2", "C4"), ("C4", "C5")]

# fig, ax = plot_zones_and_components_cartopy(zones, edges)
# plt.show()