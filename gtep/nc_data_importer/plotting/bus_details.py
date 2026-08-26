# get a csv of bus status
from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
import gtep.nc_data_importer.plotting.mapping_plots as mp_plt
import numpy as np
import pandas as pd

bus_info = {}


# get initial bus info from data file
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

# iterate through buses to get starting bus info
bus_data = data_object.md.data["elements"]["bus"]
load_data = data_object.md.data["elements"]["load"]
gen_data = data_object.md.data["elements"]["generator"]
for bus_name, info in bus_data.items():
    bus_info[bus_name] = {
        "zone_from_data": info["area"],
        "country_from_data": info["zone"],
        "average_load": None,
        "gen_capacity": None,
    }
    if bus_name in load_data.keys():
        load_info = load_data[bus_name]
        avg_load = np.mean(load_info["p_load"]["values"])
        bus_info[bus_name]["average_load"] = avg_load
bus_gen_cap = {}
for gen_name, gen_info in gen_data.items():
    if "-c" in gen_name:
        continue
    if gen_info["bus"] not in bus_gen_cap.keys():
        bus_gen_cap[gen_info["bus"]] = 0
    bus_gen_cap[gen_info["bus"]] += gen_info["p_max"]

for bus, capacity in bus_gen_cap.items():
    missing_buses = []
    if bus in bus_info.keys():
        bus_info[bus]["gen_capacity"] = capacity
    else:
        missing_buses.append(bus)

# grab the GeoJson data
geojson_path = (
    "/Users/bstorm/idaes-gtep/gtep/data/nc_data/bidding_zones_electricitymaps.geojson"
)

zone_data = mp_plt.load_zones(geojson_path)

# Map buses to zones
filtered_zones, matches = mp_plt.components_by_zone(zone_data, data_object.md.data)

# combine dictionaries
merged = {}
for k, v in bus_info.items():
    merged[k] = v
    if k in matches.keys():
        for key, value in matches[k].items():
            merged[k][key] = value

df = pd.DataFrame(merged).T

df.to_csv("bus_zone_mapping.csv", index=True, header=True)

pass
