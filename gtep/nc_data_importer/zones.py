import gtep.nc_data_importer.plotting.helpers as plt_help


class Zone:
    def __init__(self, zoneName, countryKey=None, countryName=None):
        self.zoneName = zoneName
        self.countryKey = countryKey
        self.countryName = countryName
        self.type = None
        self.coordinates = None
        self.centroid = {}  # to support section-based centroids
        self.buses = []
        self.generators = []
        self.branches = []
        self.capacity = 0
        self.renewable_capacity = 0
        self.thermal_capacity = 0
        self.fuel_types = {}

    def load_location_data(self, geojson_data):
        self.coordinates = geojson_data["geometry"]["coordinates"]
        self.type = geojson_data["geometry"]["type"]

    @staticmethod
    def polygon_centroid(coords):
        """
        Compute centroid of a single polygon ring using the shoelace formula.
        coords must be a list of [x, y] points.
        """
        if not coords:
            raise ValueError("Empty coordinate list passed to polygon_centroid")

        # If coords is a single point like [x, y], fail clearly
        if len(coords) < 3 or not isinstance(coords[0], (list, tuple)):
            raise ValueError(
                f"polygon_centroid expected ring coordinates, got: {coords}"
            )

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
            xs = [p[0] for p in coords[:-1]]
            ys = [p[1] for p in coords[:-1]]
            return sum(xs) / len(xs), sum(ys) / len(ys), 0.0

        cx /= 3.0 * area2
        cy /= 3.0 * area2

        return cx, cy, abs(area)

    @staticmethod
    def multipolygon_centroid(multipolygon_coords):
        """
        Compute centroid for a MultiPolygon or Polygon-like structure by area-weighting each polygon centroid.
        Expected input:
        - MultiPolygon: [ [outer_ring], [outer_ring], ... ]
        - Polygon:      [ outer_ring ]
        """
        if not multipolygon_coords:
            raise ValueError("Empty input to multipolygon_centroid")

        # If this looks like a single polygon ring, wrap it
        # Example: [[x,y], [x,y], ...]
        if isinstance(multipolygon_coords[0][0], (int, float)):
            # This is a single ring
            multipolygon_coords = [[multipolygon_coords]]

        # If this looks like a Polygon: [outer_ring, hole1, ...]
        # wrap as a multipolygon with one polygon
        elif isinstance(multipolygon_coords[0][0], (list, tuple)) and isinstance(
            multipolygon_coords[0][0][0], (int, float)
        ):
            multipolygon_coords = [multipolygon_coords]

        total_area = 0.0
        weighted_cx = 0.0
        weighted_cy = 0.0

        for polygon in multipolygon_coords:
            if not polygon or not polygon[0]:
                continue

            outer_ring = polygon[0]
            cx, cy, area = Zone.polygon_centroid(outer_ring)

            if area > 0:
                total_area += area
                weighted_cx += cx * area
                weighted_cy += cy * area

        if total_area == 0:
            centroids = [
                Zone.polygon_centroid(poly[0])[:2]
                for poly in multipolygon_coords
                if poly and poly[0]
            ]
            xs = [c[0] for c in centroids]
            ys = [c[1] for c in centroids]
            return sum(xs) / len(xs), sum(ys) / len(ys)

        return weighted_cx / total_area, weighted_cy / total_area

    def calculate_centroid(self):
        """
        Calculate centroid coordinates from coordinates
        """

        if self.type == "Polygon":
            cx, cy, _ = self.polygon_centroid(self.coordinates[0])
        elif self.type == "MultiPolygon":
            cx, cy = self.multipolygon_centroid(self.coordinates)

        self.centroid[0] = (cx, cy)

    def centroids_for_parts(self, parts):
        """
        Compute centroid for each split part.
        Returns a list of (cx, cy).
        """
        centroids = []
        for part in parts:
            cx, cy = self.multipolygon_centroid(part)
            centroids.append((cx, cy))
        return centroids

    @staticmethod
    def point_in_ring(point, ring):
        """
        Ray casting point-in-polygon test.
        Returns True if point is inside the ring.
        """
        x, y = point
        inside = False

        ring = plt_help.close_ring(ring)

        for i in range(len(ring) - 1):
            x1, y1 = ring[i]
            x2, y2 = ring[i + 1]

            # Check if edge crosses horizontal ray to the right of point
            intersects = ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-20) + x1
            )

            if intersects:
                inside = not inside

        return inside

    @staticmethod
    def representative_point_for_ring(ring):
        """
        Return a point that is inside the ring if possible.
        This is a base-Python fallback, not a true geometric interior-point algorithm.
        """
        ring = plt_help.close_ring(ring)

        # 1. Try centroid
        cx, cy, _ = Zone.polygon_centroid(ring)
        if Zone.point_in_ring((cx, cy), ring):
            return cx, cy

        # 2. Try average of vertices
        xs = [p[0] for p in ring[:-1]]
        ys = [p[1] for p in ring[:-1]]
        avgx = sum(xs) / len(xs)
        avgy = sum(ys) / len(ys)
        if Zone.point_in_ring((avgx, avgy), ring):
            return avgx, avgy

        # 3. Try any vertex that is inside
        for vx, vy in ring[:-1]:
            if Zone.point_in_ring((vx, vy), ring):
                return vx, vy

        # 4. Last resort: return first vertex
        return ring[0][0], ring[0][1]

    @staticmethod
    def representative_point_for_part(part):
        """
        Return a representative point for a split part.
        Assumes part is MultiPolygon-like:
            [ [outer_ring], [outer_ring], ... ]
        """
        if not part:
            raise ValueError("Empty part passed to representative_point_for_part")

        # Try each polygon in the part, choose the largest one
        largest_polygon = None
        largest_area = -1.0

        for polygon in part:
            if not polygon or not polygon[0]:
                continue

            outer_ring = polygon[0]
            _, _, area = Zone.polygon_centroid(outer_ring)

            if area > largest_area:
                largest_area = area
                largest_polygon = outer_ring

        if largest_polygon is None:
            raise ValueError("No valid polygon found in part")

        return Zone.representative_point_for_ring(largest_polygon)

    def split_into_parts(self):
        num_buses = len(self.buses)
        if num_buses == 1:
            self.buses[0].coordinates = self.centroid[0]
        # split the geometry into a section for each bus
        if num_buses > 1:
            parts = plt_help.split_multipolygon_into_n_equal_parts(
                self.coordinates, num_buses
            )
            if len(parts) != num_buses:
                raise ValueError(f"Expected {num_buses} parts, but got {len(parts)}")
            # Compute centroid of each part

            # Use the first outer ring of the whole zone as the containment reference
            if self.type == "MultiPolygon":
                zone_outer_ring = self.coordinates[0][0]
            elif self.type == "Polygon":
                zone_outer_ring = self.coordinates[0]
            else:
                raise ValueError(f"Unsupported geometry type: {self.type}")

            for ix, part in enumerate(parts):
                # Compute a representative point for the part
                if self.type == "MultiPolygon":
                    cx, cy = self.representative_point_for_part(part)
                else:
                    # For a single polygon part
                    cx, cy = self.representative_point_for_ring(part[0])

                # Ensure point lies within the whole zone outer ring
                if not self.point_in_ring((cx, cy), zone_outer_ring):
                    # Try to correct by using the part's polygon representative point
                    cx, cy = (
                        self.representative_point_for_part(part)
                        if self.type == "MultiPolygon"
                        else self.representative_point_for_ring(part[0])
                    )

                self.centroid[ix] = (cx, cy)
                self.buses[ix].coordinates = (cx, cy)

    def assign_location_to_buses(self):
        bus_list = self.buses
        num_buses = len(bus_list)

        points = plt_help.generate_points_around_centroid(
            centroid=self.centroid,
            multipolygon_coords=self.coordinates,
            num_points=num_buses,
            min_sep=0.5,
        )

        # points is guaranteed to match num_buses
        for bus, pt in zip(bus_list, points):
            bus.coordinates = pt

    def collect_unit_types(self, percent=True):
        zone_units = {}
        zone_capacity = {}
        for gen in self.generators:
            unit_type = gen.unit_type
            capacity = gen.capacity
            if unit_type not in self.unit_types.keys():
                self.unit_types[unit_type] = 0
                # add unit type capacity
                gen_cap = capacity
                if percent:
                    gen_cap = 100.0 * capacity / self.capacity
                self.fuel_types += gen_cap


class Bus:
    def __init__(self, name, countryKey, zoneName):
        self.name = name
        self.countryKey = countryKey
        self.zoneName = zoneName
        self.coordinates = None
        self.branches = []


class Branch:
    def __init__(self, name, br_type):
        self.name = name
        self.from_bus = None
        self.to_bus = None
        self.from_country = None
        self.to_country = None
        self.coordinates = None
        self.type = br_type

    def associate_bus(self, buses, from_bus, to_bus):
        self.from_bus = from_bus
        self.to_bus = to_bus
        from_lat = None
        from_lon = None
        to_lat = None
        to_lon = None
        for bus in buses:
            if from_bus == bus.name:
                from_lat = bus.coordinates[0]
                from_lon = bus.coordinates[1]
                bus.branches.append(self)
                self.from_country = bus.countryKey
            if to_bus == bus.name:
                to_lat = bus.coordinates[0]
                to_lon = bus.coordinates[1]
                bus.branches.append(self)
                self.to_country = bus.countryKey
        lat = [from_lat, to_lat]
        lon = [from_lon, to_lon]
        self.coordinates = (lat, lon)


class Generator:
    def __init__(self, name, countryKey, zoneName, capacity, gen_type, unit_type):
        self.name = name
        self.countryKey = countryKey
        self.zoneName = zoneName
        self.capacity = capacity
        self.gen_type = gen_type
        self.unit_type = unit_type
