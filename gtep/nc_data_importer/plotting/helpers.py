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

def dedupe_ring(ring):
    """
    Remove consecutive duplicate points.
    """
    if not ring:
        return ring

    out = [ring[0]]
    for pt in ring[1:]:
        if normalize_pt(pt) != normalize_pt(out[-1]):
            out.append(pt)

    # Also remove last point if same as first before closing
    if len(out) > 1 and normalize_pt(out[0]) == normalize_pt(out[-1]):
        out.pop()

    return out

def normalize_pt(pt):
    return (round(pt[0], 10), round(pt[1], 10))

def close_ring(coords):
    """
    Ensure a ring is closed.
    """
    if not coords:
        return coords
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    return coords

def get_outer_rings_from_multipolygon(multipolygon_coords):
    """
    Extract outer rings from a GeoJSON MultiPolygon coordinate structure.
    Returns a list of flat rings.
    """
    return [polygon[0] for polygon in multipolygon_coords if polygon and polygon[0]]


def ring_area(coords):
    """
    Signed area of a closed ring using the shoelace formula.
    """
    coords = close_ring(coords)
    area2 = 0.0
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        area2 += x0 * y1 - x1 * y0
    return area2 / 2.0


def polygon_area(polygon):
    """
    Area of a GeoJSON polygon structure:
    polygon = [outer_ring, hole1, hole2, ...]
    """
    if not polygon or not polygon[0]:
        return 0.0

    outer = abs(ring_area(polygon[0]))
    holes = sum(abs(ring_area(hole)) for hole in polygon[1:] if hole)
    return outer - holes

def multipolygon_area(multipolygon_coords):
    """
    Total area of all polygons in a MultiPolygon.
    """
    return sum(polygon_area(poly) for poly in multipolygon_coords if poly)

def polygon_centroid(coords):
    """
    Compute centroid of a single polygon ring using the shoelace formula.
    Returns (cx, cy, abs(area)).
    """
    coords = close_ring(coords)

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
        if not polygon or not polygon[0]:
            continue
        outer_ring = polygon[0]
        cx, cy, area = polygon_centroid(outer_ring)

        if area > 0:
            total_area += area
            weighted_cx += cx * area
            weighted_cy += cy * area

    if total_area == 0:
        centroids = [polygon_centroid(poly[0])[:2] for poly in multipolygon_coords if poly and poly[0]]
        xs = [c[0] for c in centroids]
        ys = [c[1] for c in centroids]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    return weighted_cx / total_area, weighted_cy / total_area

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

def intersect_vertical(p1, p2, xcut):
    """
    Intersection of segment p1->p2 with vertical line x = xcut.
    """
    x1, y1 = p1
    x2, y2 = p2

    if abs(x2 - x1) < 1e-12:
        return (xcut, y1)

    t = (xcut - x1) / (x2 - x1)
    y = y1 + t * (y2 - y1)
    return (xcut, y)


def intersect_horizontal(p1, p2, ycut):
    """
    Intersection of segment p1->p2 with horizontal line y = ycut.
    """
    x1, y1 = p1
    x2, y2 = p2

    if abs(y2 - y1) < 1e-12:
        return (x1, ycut)

    t = (ycut - y1) / (y2 - y1)
    x = x1 + t * (x2 - x1)
    return (x, ycut)

def clip_ring_to_left_of_vertical(ring, xcut):
    """
    Clip a ring to x <= xcut.
    Returns a new ring or [] if empty.
    """
    ring = close_ring(ring)
    output = []

    for i in range(len(ring) - 1):
        curr = ring[i]
        nxt = ring[i + 1]

        curr_inside = curr[0] <= xcut
        next_inside = nxt[0] <= xcut

        if curr_inside and next_inside:
            output.append(nxt)
        elif curr_inside and not next_inside:
            inter = intersect_vertical(curr, nxt, xcut)
            output.append(inter)
        elif not curr_inside and next_inside:
            inter = intersect_vertical(curr, nxt, xcut)
            output.append(inter)
            output.append(nxt)

    output = dedupe_ring(output)
    if len(output) < 3:
        return []
    return close_ring(output)


def clip_ring_to_right_of_vertical(ring, xcut):
    """
    Clip a ring to x >= xcut.
    """
    ring = close_ring(ring)
    output = []

    for i in range(len(ring) - 1):
        curr = ring[i]
        nxt = ring[i + 1]

        curr_inside = curr[0] >= xcut
        next_inside = nxt[0] >= xcut

        if curr_inside and next_inside:
            output.append(nxt)
        elif curr_inside and not next_inside:
            inter = intersect_vertical(curr, nxt, xcut)
            output.append(inter)
        elif not curr_inside and next_inside:
            inter = intersect_vertical(curr, nxt, xcut)
            output.append(inter)
            output.append(nxt)

    output = dedupe_ring(output)
    if len(output) < 3:
        return []
    return close_ring(output)

def clip_ring_to_bottom_of_horizontal(ring, ycut):
    """
    Clip a ring to y <= ycut.
    """
    ring = close_ring(ring)
    output = []

    for i in range(len(ring) - 1):
        curr = ring[i]
        nxt = ring[i + 1]

        curr_inside = curr[1] <= ycut
        next_inside = nxt[1] <= ycut

        if curr_inside and next_inside:
            output.append(nxt)
        elif curr_inside and not next_inside:
            inter = intersect_horizontal(curr, nxt, ycut)
            output.append(inter)
        elif not curr_inside and next_inside:
            inter = intersect_horizontal(curr, nxt, ycut)
            output.append(inter)
            output.append(nxt)

    output = dedupe_ring(output)
    if len(output) < 3:
        return []
    return close_ring(output)


def clip_ring_to_top_of_horizontal(ring, ycut):
    """
    Clip a ring to y >= ycut.
    """
    ring = close_ring(ring)
    output = []

    for i in range(len(ring) - 1):
        curr = ring[i]
        nxt = ring[i + 1]

        curr_inside = curr[1] >= ycut
        next_inside = nxt[1] >= ycut

        if curr_inside and next_inside:
            output.append(nxt)
        elif curr_inside and not next_inside:
            inter = intersect_horizontal(curr, nxt, ycut)
            output.append(inter)
        elif not curr_inside and next_inside:
            inter = intersect_horizontal(curr, nxt, ycut)
            output.append(inter)
            output.append(nxt)

    output = dedupe_ring(output)
    if len(output) < 3:
        return []
    return close_ring(output)

def clip_polygon_left_of_vertical(polygon, xcut):
    """
    Clip a polygon (outer ring only) to x <= xcut.
    Returns a polygon-like structure: [outer_ring].
    """
    if not polygon or not polygon[0]:
        return []

    clipped_outer = clip_ring_to_left_of_vertical(polygon[0], xcut)
    if not clipped_outer:
        return []
    return [clipped_outer]


def clip_polygon_right_of_vertical(polygon, xcut):
    if not polygon or not polygon[0]:
        return []

    clipped_outer = clip_ring_to_right_of_vertical(polygon[0], xcut)
    if not clipped_outer:
        return []
    return [clipped_outer]


def clip_polygon_bottom_of_horizontal(polygon, ycut):
    if not polygon or not polygon[0]:
        return []

    clipped_outer = clip_ring_to_bottom_of_horizontal(polygon[0], ycut)
    if not clipped_outer:
        return []
    return [clipped_outer]


def clip_polygon_top_of_horizontal(polygon, ycut):
    if not polygon or not polygon[0]:
        return []

    clipped_outer = clip_ring_to_top_of_horizontal(polygon[0], ycut)
    if not clipped_outer:
        return []
    return [clipped_outer]

def multipolygon_area_simple(multipolygon_coords):
    """
    Total area using only outer rings.
    """
    total = 0.0
    for poly in multipolygon_coords:
        if poly and poly[0]:
            total += abs(ring_area(poly[0]))
    return total

def find_vertical_cut_for_half_area(multipolygon_coords, tol=1e-9, max_iter=80):
    """
    Find xcut such that area left of xcut is approximately half the total area.
    """
    minx, miny, maxx, maxy = multipolygon_bounds(multipolygon_coords)
    total_area = multipolygon_area_simple(multipolygon_coords)
    target = total_area / 2.0

    low = minx
    high = maxx

    for _ in range(max_iter):
        mid = (low + high) / 2.0

        left_parts = []
        for poly in multipolygon_coords:
            clipped = clip_polygon_left_of_vertical(poly, mid)
            if clipped:
                left_parts.append(clipped)

        left_area = multipolygon_area_simple(left_parts)

        if abs(left_area - target) <= tol * max(1.0, total_area):
            return mid

        if left_area < target:
            low = mid
        else:
            high = mid

    return (low + high) / 2.0


def find_horizontal_cut_for_half_area(multipolygon_coords, tol=1e-9, max_iter=80):
    """
    Find ycut such that area below ycut is approximately half the total area.
    """
    minx, miny, maxx, maxy = multipolygon_bounds(multipolygon_coords)
    total_area = multipolygon_area_simple(multipolygon_coords)
    target = total_area / 2.0

    low = miny
    high = maxy

    for _ in range(max_iter):
        mid = (low + high) / 2.0

        bottom_parts = []
        for poly in multipolygon_coords:
            clipped = clip_polygon_bottom_of_horizontal(poly, mid)
            if clipped:
                bottom_parts.append(clipped)

        bottom_area = multipolygon_area_simple(bottom_parts)

        if abs(bottom_area - target) <= tol * max(1.0, total_area):
            return mid

        if bottom_area < target:
            low = mid
        else:
            high = mid

    return (low + high) / 2.0

def split_multipolygon_into_two(multipolygon_coords):
    """
    Split into two approximately equal-area parts.
    Returns [part1, part2].
    """
    minx, miny, maxx, maxy = multipolygon_bounds(multipolygon_coords)
    dx = maxx - minx
    dy = maxy - miny

    if dx >= dy:
        xcut = find_vertical_cut_for_half_area(multipolygon_coords)

        left = []
        right = []

        for poly in multipolygon_coords:
            lp = clip_polygon_left_of_vertical(poly, xcut)
            rp = clip_polygon_right_of_vertical(poly, xcut)
            if lp:
                left.append(lp)
            if rp:
                right.append(rp)

        return left, right

    else:
        ycut = find_horizontal_cut_for_half_area(multipolygon_coords)

        bottom = []
        top = []

        for poly in multipolygon_coords:
            bp = clip_polygon_bottom_of_horizontal(poly, ycut)
            tp = clip_polygon_top_of_horizontal(poly, ycut)
            if bp:
                bottom.append(bp)
            if tp:
                top.append(tp)

        return bottom, top

def split_multipolygon_into_n_equal_parts(multipolygon_coords, n):
    """
    Recursively split the largest part until n parts are created.
    Returns a list of MultiPolygon-like parts.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    parts = [multipolygon_coords]

    while len(parts) < n:
        # split the largest part next
        parts.sort(key=multipolygon_area_simple, reverse=True)
        largest = parts.pop(0)

        p1, p2 = split_multipolygon_into_two(largest)

        # If split failed, put it back and stop
        if not p1 or not p2:
            parts.append(largest)
            break

        parts.append(p1)
        parts.append(p2)

    return parts[:n]


def point_in_polygon(x, y, polygon):
    """
    Ray casting point-in-polygon test for a flat ring.
    """
    if not polygon or len(polygon) < 3:
        return False

    inside = False
    ring = close_ring(ring)
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]

    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]

        intersects = ((y1 > y) != (y2 > y)) and \
                     (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-20) + x1)

        if intersects:
            inside = not inside

    return inside

def ensure_centroid_inside_zone(cx, cy, zone_outer_ring):
    if point_in_polygon((cx, cy), zone_outer_ring):
        return cx, cy

    # fallback: use a vertex or average of vertices
    for vx, vy in zone_outer_ring[:-1]:
        if point_in_polygon((vx, vy), zone_outer_ring):
            return vx, vy

    # final fallback: original centroid
    return cx, cy



def point_in_multipolygon(x, y, multipolygon_coords):
    """
    True if the point is inside any polygon part.
    """
    for ring in get_outer_rings_from_multipolygon(multipolygon_coords):
        if point_in_polygon(x, y, ring):
            return True
    return False


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
