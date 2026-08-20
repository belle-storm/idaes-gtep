import colorsys
import random
import math
import gtep.nc_data_importer.geojson_reader as geo


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


### CENTROID LOCATION HELPERS ###
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
        cx, cy, _ = geo.polygon_centroid(polygon[0])
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


def _iter_rings(coords):
    """
    Yield all rings from a GeoJSON-like Polygon or MultiPolygon geometry.
    Each ring is a list of [lon, lat] coordinate pairs.
    """
    for polygon in coords:
        for ring in polygon:
            yield ring
