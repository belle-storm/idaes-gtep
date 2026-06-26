import egret.data.model_data as md


def _create_skeleton():
    model_data = md.ModelData.empty_model_data_dict()
    elements = model_data["elements"]
    model_data["system"]

    elements["bus"] = {}
    elements["load"] = {}
    elements["shunt"] = {}

    elements["branch"] = {}
    elements["dc_branch"] = {}

    elements["generator"] = {}

    elements["storage"] = {}

    return model_data


def _build_system(system):
    system["name"] = "NC"
    system["baseMVA"] = None
    system["reference_bus"] = None
    system["reference_bus_angle"] = None
    system["time_period_length_minutes"] = None
    system["time_keys"] = []
    system["min_operating_reserve"] = (
        None  # NOTE in default data #used per region (fraction of load within region)
    )
    system["min_spinning_reserve"] = (
        None  # NOTE in default data #used (fraction of load per region)
    )


def _add_basic_dict(data):
    data_dict = {}
    data_dict["data_type"] = None
    data_dict["values"] = []
    return data_dict


def _add_bus_dict(buses, bus_data):
    for bus_name in bus_data:  # used
        bus_dict = {}
        bus_dict["id"] = None
        bus_dict["base_kv"] = None
        bus_dict["matpower_bustype"] = None
        bus_dict["vm"] = None
        bus_dict["va"] = None
        bus_dict["v_min"] = None
        bus_dict["v_max"] = None
        bus_dict["area"] = None  # used
        bus_dict["zone"] = None

        buses[bus_name] = bus_dict


def _add_load_dict(loads, load_data):
    for bus_name in load_data:
        load_dict = {}
        load_dict["bus"] = None
        load_dict["in_service"] = None
        load_dict["p_load"] = {}
        load_dict["q_load"] = {}
        load_dict["area"] = None
        load_dict["zone"] = None

        loads[bus_name] = load_dict


def _add_area_dict(areas, area_data):
    for i in area_data:
        areas[i] = {}


def _add_branch_dict(branches, branch_data):
    for branch_name in branch_data:  # used
        branch_dict = {}
        branch_dict["from_bus"] = None  # used (start bus)
        branch_dict["to_bus"] = None  # used (end bus)
        branch_dict["in_service"] = None
        branch_dict["resistance"] = None
        branch_dict["reactance"] = None  # used (reactance for each line in ohms)
        branch_dict["charging_susceptance"] = None
        branch_dict["rating_long_term"] = None  # used (long term thermal rating)
        branch_dict["rating_short_term"] = None
        branch_dict["rating_emergency"] = None
        branch_dict["angle_diff_min"] = None
        branch_dict["angle_diff_max"] = None
        branch_dict["pf"] = None
        branch_dict["qf"] = None
        branch_dict["pt"] = None
        branch_dict["qt"] = None
        branch_dict["branch_type"] = None
        branch_dict["loss_rate"] = None  # NOTE in default data
        branch_dict["distance"] = (
            None  # NOTE in default data #used (distance between terminal buses for branch)
        )
        branch_dict["capital_cost"] = (
            None  # NOTE in default data #used (investment cost for each new branch)
        )
        branch_dict["capital_multiplier"] = None  # used
        branch_dict["extension_multiplier"] = (
            None  # used (cost of life extension as fraction of initial investment)
        )

        branches[branch_name] = branch_dict


def _add_dc_branch_dict(branches, branch_data):
    for branch in branch_data:
        branch_dict = {}
        branch_data["from_bus"] = None
        branch_data["to_bus"] = None
        branch_data["rating_short_term"] = None
        branch_data["rating_long_term"] = None
        branch_data["rating_emergency"] = None

        branches[branch] = branch_dict


def _add_generator_dict(gens, gen_data):
    for gen_name in gen_data:  # used
        gen_dict = {}
        gen_dict["bus"] = None
        gen_dict["in_service"] = None  # NOTE in default data
        gen_dict["mbase"] = None
        gen_dict["pg"] = None
        gen_dict["gg"] = None
        gen_dict["p_min"] = None  # used for thermals (min output)
        gen_dict["p_max"] = None  # Used (max output)
        gen_dict["q_min"] = None
        gen_dict["q_max"] = None
        gen_dict["ramp_q"] = None
        gen_dict["fuel"] = None
        gen_dict["unit_type"] = None
        gen_dict["area"] = None
        gen_dict["zone"] = None
        gen_dict["generator_type"] = None  # used
        gen_dict["p_fuel"] = None
        gen_dict["startup_fuel"] = None
        gen_dict["non_fuel_startup_cost"] = (
            None  # used (flat startup cost for thermals)
        )
        gen_dict["shutdown_cost"] = None
        gen_dict["agc_capable"] = None
        gen_dict["p_min_agc"] = None
        gen_dict["p_max_agc"] = None
        gen_dict["ramp_agc"] = None
        gen_dict["ramp_up_60min"] = None
        gen_dict["ramp_down_60min"] = None
        gen_dict["fuel_cost"] = None  # used if RTS_GMLC
        gen_dict["p_cost"] = (
            None  # basic dict #used if not RTS_GMLC (cost per unit of fuel per gen) $/Mw*hr
        )
        gen_dict["startup_capacity"] = None
        gen_dict["shutdown_capacity"] = None
        gen_dict["min_up_time"] = None
        gen_dict["min_down_time"] = None
        gen_dict["initial_status"] = None
        gen_dict["initial_p_output"] = None
        gen_dict["initial_q_output"] = None
        gen_dict["lifetime"] = None  # NOTE in default data #used (year)
        gen_dict["spinning_reserve_frac"] = (
            None  # NOTE in default data #used (max fraction of termal gen output) for thermal
        )
        gen_dict["quickstart_reserve_frac"] = (
            None  # NOTE in default data #used (max fraction of thermal gen output by quickstart)
        )
        gen_dict["capital_multiplier"] = (
            None  # NOTE in default data #used (multiplier for new gen investments)
        )
        gen_dict["extension_multiplier"] = (
            None  # NOTE in default data #used (cost of life extension as fraction of initial investment)
        )
        gen_dict["max_operating_reserve"] = None  # NOTE in default data
        gen_dict["max_spinning_reserve"] = (
            None  # NOTE in default data #used in thermals (max spinning reserve available for gen as fraction of max generation output)
        )
        gen_dict["max_quickstart_reserve"] = None  # NOTE in default data
        gen_dict["ramp_up_rate"] = None  # NOTE in default data
        gen_dict["ramp_down_rate"] = None  # NOTE in default data
        gen_dict["emissions_factor"] = (
            None  # NOTE in default data #used (full lifecycle co_2 emission factor)
        )
        gen_dict["start_fuel"] = None  # NOTE in default data
        gen_dict["investment_cost"] = None  # NOTE in default data

        gens[gen_name] = gen_dict


def _add_storage_dict(element_stor, storage_data):
    for name in storage_data:
        storage_dict = {}
        storage_dict["bus"] = None
        storage_dict["generator"] = None
        storage_dict["storage_type"] = None
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
        storage_dict["in_service"] = None
        storage_dict["capital_multiplier"] = None
        storage_dict["extension_multiplier"] = None
        storage_dict["investment_cost"] = None
        storage_dict["investment_cost_kwh"] = None

        element_stor[name] = storage_dict
