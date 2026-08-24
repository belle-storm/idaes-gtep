from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
import plotly.graph_objects as go
import plotly.colors as pc
import gtep.nc_data_importer.geojson_reader as geo
from gtep.nc_data_importer.zones import Zone, Bus, Branch, Generator


def load_zones(geojson_path, match_naming=True, zone_name_key="zoneName"):
    geojson_data = geo.retrieve_zone_loc_data(geojson_path)
    zone_data = {}
    for zone in geojson_data:
        # grab zone and country names
        name = zone["properties"][zone_name_key]
        countryName = None
        countryKey = None
        if "countryName" in zone["properties"].keys():
            countryName = zone["properties"]["countryName"]
        if "countryKey" in zone["properties"].keys():
            countryKey = zone["properties"]["countryKey"]
        # match naming convention to bus zones
        if match_naming:
            if "-" not in name:
                name = name + "1"
        # make a Zone object and save to dict
        zObj = Zone(name, countryKey, countryName)
        zone_data[name] = zObj
        # save location data to Zone object
        zone_data[name].load_location_data(zone)
        zObj.calculate_centroid()

    return zone_data


def bus_by_area(bus_data):
    # grab the bus in each area
    bus_areas = {}
    countries = []
    for bus_name, bus_dict in bus_data.items():
        country = bus_dict["zone"]
        area = bus_name.split(" ")[0]
        if area not in bus_areas.keys():
            bus_areas[area] = []
        countries.append(country)
        bus_areas[area].append(Bus(bus_name, country, area))
    countries = set(countries)

    return countries, bus_areas


def gen_by_area(gen_data):
    # grab the gen in each zone and area
    gen_areas = {}
    for gen_name, gen_dict in gen_data.items():
        if "c" in gen_name:
            continue
        country = gen_dict["zone"]
        area = gen_name.split(" ")[0]
        capacity = gen_dict["p_max"]
        gen_type = gen_dict["generator_type"]
        unit_type = gen_dict["unit_type"]

        gen = Generator(gen_name, country, area, capacity, gen_type, unit_type)

        # save area
        if area not in gen_areas.keys():
            gen_areas[area] = [gen]
        else:
            gen_areas[area].append(gen)

    return gen_areas


def collect_unit_types_total(gen_data):
    unit_types = {}

    for gen, gen_info in gen_data.items():
        unit_type = gen_info.get("unit_type", "Unknown")
        if unit_type != "Unknown" and unit_type not in unit_types.keys():
            # create the starting base
            unit_types[unit_type] = 0
        capacity = gen_info.get("p_max", 0)
        unit_types[unit_type] += capacity

    return unit_types


def adjust_bus_zone(filt_zones, countries):
    # if there is more than one bus in a zone,
    # check if there are empty zones in that country
    # move a bus to an empty zone
    # iterate through this until zone only has 1
    # or until all zones in that country are filled
    # combine zones into countries
    for country in countries:
        zones = {}
        # grab all the zones in this country
        for z in filt_zones.values():
            if z.countryKey == country:
                num_bus = len(z.buses)
                zones[z] = num_bus
        # check if there is an empty zone
        if max(zones.values()) > 1 and min(zones.values()) < 1:
            above = {k: v for k, v in zones.items() if v > 1}
            no = [k for k, v in zones.items() if v < 1]
            for zn in above.keys():
                for bus in zn.buses:
                    if no:
                        no_bus_zone = no[-1]
                        no_bus_zone.buses.append(bus)
                        # remove from their original lists
                        no.pop()
                        zn.buses.remove(bus)


def manually_adjust_zone_assignement(filt_zones):
    SE_buses = {}
    NO_buses = {}
    for name, zones in filt_zones.items():
        if zones.countryKey == "SE":
            for bus in zones.buses:
                SE_buses[bus] = name
        elif zones.countryKey == "NO":
            for bus in zones.buses:
                NO_buses[bus] = name
    for bus, og_zone in SE_buses.items():
        if bus.name == "SE2 0":
            filt_zones["SE-SE4"].buses.append(bus)
            filt_zones[og_zone].buses.remove(bus)
    for bus, og_zone in NO_buses.items():
        if bus.name == "NO2 0":
            filt_zones["NO-NO3"].buses.append(bus)
            filt_zones[og_zone].buses.remove(bus)


def components_by_zone(zone_data, grid_data):
    # filter zones by matching countries and assign components to zone
    country_list, bus_area = bus_by_area(grid_data["elements"]["bus"])
    gen_area = gen_by_area(grid_data["elements"]["generator"])

    # filter zones to include full countries even if no buses in that area
    filt_zone = {}
    for z, info in zone_data.items():
        if info.countryKey in country_list:
            filt_zone[z] = info

    # save buses to their zones
    match_status = {i: False for i in bus_area.keys()}
    for z in zone_data.keys():
        for ix, Bus in bus_area.items():
            if ix in z:
                filt_zone[z].buses = bus_area[ix]
                match_status[ix] = True
        for g, Gen in gen_area.items():
            if g in z:
                filt_zone[z].generators = gen_area[g]
    # catch stragglers and assign to any country zone that matches
    for key, status in match_status.items():
        if not status:
            new_key = key[:-1]
            for z in filt_zone.keys():
                if new_key in z:
                    filt_zone[z].buses.extend(bus_area[key])
                    # debug check that everything found a home
                    match_status[key] = True
                    break

    # rework bus association
    adjust_bus_zone(filt_zone, country_list)
    manually_adjust_zone_assignement(filt_zone)

    return filt_zone


def gen_capacity_by_zone(filt_zones):
    # add capacity info by zone for each type
    for z, info in filt_zones.items():
        gen_data = info.generators
        capacity = {"renewable": 0, "thermal": 0, "total": 0}
        for g in gen_data:
            capacity["total"] += g.capacity
            capacity[g.gen_type] += g.capacity
        filt_zones[z].capacity = capacity["total"]
        filt_zones[z].renewable_capacity = capacity["renewable"]
        filt_zones[z].thermal_capacity = capacity["thermal"]


def assign_centroid_to_bus(filt_zones):
    for zone in filt_zones.values():
        zone.split_into_parts()
        # zone.assign_location_to_buses()


def grab_all_buses(filt_zones):
    all_buses = []
    for zone in filt_zones.values():
        all_buses.extend(zone.buses)
    return all_buses


def manually_adjust_bus_coords(all_buses):

    old_to_new = {
        "GB6 0 battery": "GB6 0 H2",
        "GB6 0 H2": "GB6 0",
        "GB6 0": "GB6 0 battery",
        "DE1 0": "DE1 1",
        "DE1 1": "DE1 0",
        "DE1 4": "DE1 2 H2",
        "DE1 2 H2": "DE1 4",
        "DK1 0": "DK1 0 H2",
        "DK1 0 H2": "DK1 0",
        "NL1 0": "NL1 0 battery",
        "NL1 0 battery": "NL1 0",
        "FI2 0": "FI2 0 battery",
        "FI2 0 battery": "FI2 0",
        "EE7 0": "EE7 0 battery",
        "EE7 0 battery": "EE7 0",
        "LV7 0": "LV7 0 battery",
        "LV7 0 battery": "LV7 0",
        "LT7 0": "LT7 0 battery",
        "LT7 0 battery": "LT7 0",
    }
    target_buses = {
        n: {"og": None, "new": None, "object": None} for n in old_to_new.keys()
    }
    for bus in all_buses:
        if bus.name in target_buses.keys():
            target_buses[bus.name]["og"] = bus.coordinates
            target_buses[bus.name]["object"] = bus
            target_buses[old_to_new[bus.name]]["new"] = bus.coordinates
    for item in target_buses.values():
        busObj = item["object"]
        busObj.coordinates = item["new"]


def make_branches(ac_branch_data, dc_branch_data, buses):
    branch_list = []
    for branch_data in [ac_branch_data, dc_branch_data]:
        for name, info in branch_data.items():
            b = Branch(name, info["carrier"])
            b.associate_bus(buses, info["from_bus"], info["to_bus"])
            branch_list.append(b)
    return branch_list


def collect_unit_by_zone(filt_zones, percent=True):
    zone_units = {}
    for zone in filt_zones.values():
        zone.collect_unit_types(percent)
        zone_units[zone] = zone.unit_types
    return zone_units


def plot_zones_and_buses_mapbox(
    zone_data,
    branch_data=None,
    zone_colors=None,
    map_style="open-street-map",
):
    """
    Plot MultiPolygon zones and bus points on a Mapbox/Plotly map.
    """
    fig = go.Figure()

    first_trace_for_zone = True
    # Add bus points
    bus_lons = []
    bus_lats = []
    bus_text = []

    # Add zones as filled polygon traces
    for i, (zone_name, zone_info) in enumerate(zone_data.items()):
        coords = zone_info.coordinates
        country = zone_info.countryName
        color = zone_colors.get(zone_name, None) if zone_colors else None
        if color is None:
            color = (
                f"rgba({50 + (i*40)%200}, {100 + (i*70)%155}, {180 + (i*30)%75}, 0.35)"
            )

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
                    name="Zones",
                    hoverinfo="text",
                    text=zone_name,
                    showlegend=first_trace_for_zone,
                )
            )
            first_trace_for_zone = False

        for bus in zone_info.buses:
            lon = bus.coordinates[0]
            lat = bus.coordinates[1]
            bus_lons.append(lon)
            bus_lats.append(lat)
            bus_text.append(bus.name)

    # plot all buses
    fig.add_trace(
        go.Scattermapbox(
            lon=bus_lons,
            lat=bus_lats,
            mode="markers",
            marker=dict(size=5, color="rgba(255, 0, 0, 0.5)"),
            hoverinfo="text",
            text=bus_text,
            # textposition="top center",
            name="Buses",
        )
    )

    # plot branch data
    if branch_data:
        branch_legend_added = False
        for branch in branch_data:
            loc = branch.coordinates
            fig.add_trace(
                go.Scattermapbox(
                    lon=loc[0],
                    lat=loc[1],
                    mode="lines",
                    line=dict(color="rgba(0, 0, 0, 0.5)", width=2),
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
        for poly in zone_info.coordinates:
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
    zone_renewables = {}
    if not percent:
        title = "Renewable Generation Capacity by Zone"
        unit_label = "Capacity (MW)"
        # Gather renewable capacities
        for zone_name, zone_info in zone_data.items():
            renewable_capacity = zone_info.renewable_capacity
            zone_renewables[zone_name] = renewable_capacity

    else:
        title = "Percentage of Generation Capacity from Renewables by Zone"
        unit_label = "%"
        # Gather renewable percentages
        for zone_name, zone_info in zone_data.items():
            renewable_count = zone_info.renewable_capacity
            total_count = zone_info.capacity

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
        coords = zone_info.coordinates
        country = zone_info.countryName
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
                    text=country,
                    # text=f"{country}<br>Renewable: {pct:.1f}{unit_label}",
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
        for poly in zone_info.coordinates:
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


def plot_fuel_pie(capacity_by_type, title=None):
    total_capacity = sum(capacity_by_type.values())

    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(capacity_by_type.keys()),
                values=list(capacity_by_type.values()),
                textinfo="label+percent",
                hovertemplate=("%{label}: %{value} MW<br>" "%{percent}<extra></extra>"),
            )
        ]
    )
    if title is None:
        title = f"Distribution of Generation Capacity by Unit Type (Total: {total_capacity} MW)"

    fig.update_layout(title=title)
    fig.show()


def plot_fuel_by_zone(zone_units, percent=True):
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

    yaxis_title = "Generation Capacity (MW) by Unit Type"
    if percent:
        yaxis_title = "Percent of Generation Capacity (MW) by Unit Type"

    fig.update_layout(
        barmode="stack",
        title="Distribution of Capacity by Zone and Unit Type",
        xaxis_title="Zone",
        yaxis_title=yaxis_title,
        legend_title="Unit Type",
    )

    fig.show()


def run_grid_location_workflow(geojson_path=None, percent=True):
    if geojson_path is None:
        geojson_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"

    zone_data = load_zones(geojson_path)
    filtered_zones = components_by_zone(zone_data, grid_data)
    gen_capacity_by_zone(filtered_zones)
    assign_centroid_to_bus(filtered_zones)
    buses = grab_all_buses(filtered_zones)
    bus_names = [bus.name for bus in buses]
    manually_adjust_bus_coords(buses)
    branch_data = make_branches(
        grid_data["elements"]["branch"],
        grid_data["elements"]["dc_branch"],
        buses,
    )
    plot_zones_and_buses_mapbox(filtered_zones, branch_data)
    plot_renewable_percentage_map(filtered_zones)
    pass


def run_unit_type_plotting_workflow(gen_data, plot_type="pie", percent=True):
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
        zone_units = collect_unit_by_zone(gen_data, percent)
        plot_fuel_by_zone(zone_units, percent)


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

    run_grid_location_workflow(geojson_path)

    pass
