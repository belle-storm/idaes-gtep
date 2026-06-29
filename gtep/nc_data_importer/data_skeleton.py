import egret.data.model_data as md


def create_skeleton():
    model_data = md.ModelData.empty_model_data_dict()
    elements = model_data["elements"]
    system = model_data["system"]

    _build_elements(elements)
    _build_system(system)

    return model_data


def _build_system(system):
    system["name"] = "NC"
    system["baseMVA"] = None
    system["reference_bus"] = None
    system["reference_bus_angle"] = None
    system["time_period_length_minutes"] = None
    system["time_keys"] = []
    system["min_operating_reserve"] = None
    system["min_spinning_reserve"] = None


def _build_elements(elements):
    elements["bus"] = {}
    elements["load"] = {}
    elements["shunt"] = {}

    elements["branch"] = {}
    elements["dc_branch"] = {}

    elements["generator"] = {}

    elements["storage"] = {}


def _add_basic_dict():
    data_dict = {}
    data_dict["data_type"] = None
    data_dict["values"] = []
    return data_dict


def _add_area_dict(areas, area_data):
    for i in area_data:
        areas[i] = {}


def add_storage_data(stores, storage_data):

    for i, name in enumerate(storage_data["i"]):
        storage_dict = {}
        storage_dict["bus"] = storage_data["bus"][i]
        storage_dict["generator"] = None
        storage_dict["storage_type"] = storage_data["carrier"][i]
        storage_dict["energy_capacity"] = None
        storage_dict["initial_state_of_charge"] = None
        storage_dict["end_state_of_charge"] = None
        storage_dict["minimum_state_of_charge"] = None
        storage_dict["charge_efficiency"] = None
        storage_dict["discharge_efficiency"] = None
        storage_dict["max_discharge_rate"] = None
        storage_dict["min_discharge_rate"] = None
        storage_dict["max_charge_rate"] = None
        storage_dict["min_charge_rate"] = None
        storage_dict["initial_charge_rate"] = None
        storage_dict["initial_discharge_rate"] = None
        storage_dict["charge_cost"] = None
        storage_dict["discharge_cost"] = None
        storage_dict["retention_rate_60min"] = None
        storage_dict["ramp_up_input_60min"] = None
        storage_dict["ramp_down_input_60min"] = None
        storage_dict["ramp_up_output_60min"] = None
        storage_dict["ramp_down_output_60min"] = None
        storage_dict["in_service"] = True
        storage_dict["capital_multiplier"] = None
        storage_dict["extension_multiplier"] = None
        storage_dict["investment_cost"] = storage_data["capital_cost"][i]
        storage_dict["investment_cost_kwh"] = None

        # included in data but no match here
        storage_dict["e_nom_extendable"] = bool(storage_data["e_nom_extendable"][i])
        storage_dict["e_cyclic"] = bool(storage_data["e_cyclic"][i])
        storage_dict["lifetime"] = storage_data["lifetime"][i]

        stores[name] = storage_dict


def add_buses(buses, bus_data):
    for i, bus_name in enumerate(bus_data["i"]):
        bus_dict = {}
        bus_dict["id"] = bus_name
        bus_dict["base_kv"] = None
        bus_dict["matpower_bustype"] = bus_data["control"][i]
        bus_dict["vm"] = None
        bus_dict["va"] = None
        bus_dict["v_min"] = None
        bus_dict["v_max"] = None
        bus_dict["area"] = bus_data["location"][i]
        bus_dict["zone"] = bus_data["country"][i]

        # included in data but seemingly no match here
        bus_dict["v_nom"] = bus_data["v_nom"][i]
        bus_dict["x"] = bus_data["x"][i]
        bus_dict["y"] = bus_data["y"][i]
        bus_dict["carrier"] = bus_data["carrier"][i]
        bus_dict["sub_network"] = bus_data["sub_network"][i]
        bus_dict["substation_lv"] = bus_data["substation_lv"][i]
        bus_dict["substation_off"] = bus_data["substation_off"][i]

        buses[bus_name] = bus_dict


def add_branches(branches, dc_branch, branch_data):

    for ind, branch_name in enumerate(branch_data["i"]):
        if branch_data["carrier"][ind] != "DC":
            branch_dict = {}
            branch_dict["from_bus"] = branch_data["bus0"][ind]
            branch_dict["to_bus"] = branch_data["bus1"][ind]
            branch_dict["in_service"] = None
            branch_dict["resistance"] = None
            branch_dict["reactance"] = None
            branch_dict["charging_susceptance"] = None
            branch_dict["rating_long_term"] = None
            branch_dict["rating_short_term"] = None
            branch_dict["rating_emergency"] = None
            branch_dict["angle_diff_min"] = None
            branch_dict["angle_diff_max"] = None
            branch_dict["pf"] = None
            branch_dict["qf"] = None
            branch_dict["pt"] = None
            branch_dict["qt"] = None
            branch_dict["branch_type"] = branch_data["carrier"][ind]
            branch_dict["loss_rate"] = branch_data["efficiency"][ind]
            branch_dict["distance"] = branch_data["length"][ind]
            branch_dict["capital_cost"] = branch_data["capital_cost"][ind]
            branch_dict["capital_multiplier"] = None
            branch_dict["extension_multiplier"] = None

            # included in data but seemingly no match here
            branch_dict["p_nom"] = branch_data["p_nom"][ind]
            branch_dict["p_nom_extendable"] = bool(branch_data["p_nom_extendable"][ind])
            branch_dict["p_min_pu"] = branch_data["p_min_pu"][ind]
            branch_dict["lifetime"] = branch_data["lifetime"][ind]
            branch_dict["underground"] = bool(branch_data["underground"][ind])
            branch_dict["underwater_fraction"] = branch_data["underwater_fraction"][ind]
            branch_dict["under_construction"] = bool(
                branch_data["under_construction"][ind]
            )
            branch_dict["geometry"] = branch_data["geometry"][ind]
            branch_dict["dc"] = branch_data["dc"][ind]
            branch_dict["tags"] = branch_data["tags"][ind]

            branches[branch_name] = branch_dict

        else:
            # dc branch
            dc_branch_dict = {}
            dc_branch_dict["from_bus"] = branch_data["bus0"][ind]
            dc_branch_dict["to_bus"] = branch_data["bus1"][ind]
            dc_branch_dict["rating_short_term"] = None
            dc_branch_dict["rating_long_term"] = None
            dc_branch_dict["rating_emergency"] = None

            dc_branch[branch_name] = branch_dict


def add_gens(gens, gen_data, carrier_data):
    for ind, gen_name in enumerate(gen_data["i"]):
        gen_dict = {}
        gen_dict["bus"] = gen_data["bus"][ind]
        gen_dict["in_service"] = True
        gen_dict["mbase"] = None
        gen_dict["pg"] = None
        gen_dict["gg"] = None
        gen_dict["p_min"] = gen_data["p_nom_min"][ind]
        gen_dict["p_max"] = gen_data["p_nom_max"][ind]
        gen_dict["q_min"] = None
        gen_dict["q_max"] = None
        gen_dict["ramp_q"] = None
        gen_dict["fuel"] = gen_data["carrier"][ind]
        gen_dict["unit_type"] = None
        gen_dict["area"] = None
        gen_dict["zone"] = None
        gen_dict["generator_type"] = None
        gen_dict["p_fuel"] = None
        gen_dict["startup_fuel"] = None
        gen_dict["non_fuel_startup_cost"] = None
        gen_dict["shutdown_cost"] = None
        gen_dict["agc_capable"] = None
        gen_dict["p_min_agc"] = None
        gen_dict["p_max_agc"] = None
        gen_dict["ramp_agc"] = None
        gen_dict["ramp_up_60min"] = None
        gen_dict["ramp_down_60min"] = None
        gen_dict["fuel_cost"] = None
        p_cost = _add_basic_dict()
        p_cost["values"] = gen_data["marginal_cost"][ind]
        gen_dict["p_cost"] = p_cost
        gen_dict["startup_capacity"] = None
        gen_dict["shutdown_capacity"] = None
        gen_dict["min_up_time"] = None
        gen_dict["min_down_time"] = None
        gen_dict["initial_status"] = None
        gen_dict["initial_p_output"] = None
        gen_dict["initial_q_output"] = None
        gen_dict["lifetime"] = gen_data["lifetime"][ind]
        gen_dict["spinning_reserve_frac"] = None
        gen_dict["quickstart_reserve_frac"] = None
        gen_dict["capital_multiplier"] = None
        gen_dict["extension_multiplier"] = None
        gen_dict["max_operating_reserve"] = None
        gen_dict["max_spinning_reserve"] = None
        gen_dict["max_quickstart_reserve"] = None
        gen_dict["ramp_up_rate"] = None
        gen_dict["ramp_down_rate"] = None
        carrier_ind = carrier_data["i"].index(gen_data["carrier"][ind])
        gen_dict["emissions_factor"] = carrier_data["co2_emissions"][carrier_ind]
        gen_dict["start_fuel"] = None
        gen_dict["investment_cost"] = gen_data["capital_cost"][ind]

        # included in data but seemingly no match here
        gen_dict["p_nom"] = gen_dict["p_nom"][ind]
        gen_dict["p_nom_extendable"] = bool(gen_dict["p_nom_extendable"][ind])
        gen_dict["p_max_pu"] = gen_dict["p_max_pu"][ind]
        gen_dict["efficiency"] = gen_dict["efficiency"][ind]
        gen_dict["weight"] = gen_dict["weight"][ind]
        gen_dict["t_p_max_pu_i"] = gen_dict["t_p_max_pu_i"][ind]
        gen_dict["t_p_max_pu"] = gen_dict["t_p_max_pu"][ind]

        gens[gen_name] = gen_dict


def add_loads(loads, buses, load_data):
    for ind, load_name in enumerate(load_data["i"]):
        load_dict = {}
        load_dict["bus"] = load_data["bus"][ind]
        load_dict["in_service"] = True
        p_load = _add_basic_dict()
        load_dict["p_load"] = p_load
        q_load = _add_basic_dict()
        load_dict["q_load"] = q_load
        load_dict["area"] = buses[load_name]["area"]
        load_dict["zone"] = buses[load_name]["zone"]

        # included in data but seemingly no match here
        load_dict["t_p_set_i"] = load_data["t_p_set_i"][ind]
        load_dict["t_p_set"] = load_data["t_p_set"][ind]

        loads[load_name] = load_dict
