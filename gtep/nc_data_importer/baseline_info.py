from gtep.nc_data_importer.nc_data import NCExpansionPlanningData
import matplotlib.pyplot as plt
import math

data_path = "/Users/bstorm/idaes-gtep/gtep/data/nc_data/"

#create data object
data_object = NCExpansionPlanningData(
    stages=2,
    num_reps=2,
    len_reps=1,
    num_commit=6,
    num_dispatch=4,
    duration_dispatch=15,
)
data_object.load_nc_data(data_path)

pass

#TODO
# - Create a pie chart of all fuel type distribution
# - Stacked bar chart, fuel type by zone
# - load by bus 
# - table of baseline details
#       -  num buses
#       -  num gens
#       -  num zones
