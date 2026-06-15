import pulp as pl

from utils import prepare_data


def create_variables(model, instance):
    N1 = instance.N1
    N2 = instance.N2

    x1 = {}
    y1 = {}
    for i in N1:
        for j in N1:
            if i == j:
                continue
            x1[(i, j)] = pl.LpVariable(f"x1_{i}_{j}", lowBound=0, cat=pl.LpInteger)

            for d in instance.demands:
                y1[(i, j, d)] = pl.LpVariable(f"y1_{i}_{j}_{d}", cat=pl.LpBinary)

    x2 = {}
    y2 = {}
    for i in N2:
        for j in N2:
            if i == j:
                continue
            x2[(i, j)] = pl.LpVariable(f"x2_{i}_{j}", lowBound=0, cat=pl.LpInteger)

            for d in instance.demands:
                y2[(i, j, d)] = pl.LpVariable(f"y2_{i}_{j}_{d}", cat=pl.LpBinary)

    w1 = {}
    for i in N1:
        for j in N1:
            if i == j:
                continue
            for d in instance.demands:
                w1[(i, j, d)] = pl.LpVariable(f"w1_{i}_{j}_{d}", lowBound=0, cat=pl.LpContinuous)

    w2 = {}
    for i in N2:
        for j in instance.covers:
            if i == j:
                continue
            for d in instance.demands:
                w2[(i, j, d)] = pl.LpVariable(f"w2_{i}_{j}_{d}", lowBound=0, cat=pl.LpContinuous)

    z = {}
    for d in instance.demands:
        for i in instance.N_HC:
            z[(d, i)] = pl.LpVariable(f"z_{d}_{i}", cat=pl.LpBinary)

    print(
        f"Number of variables: {len(x1) + len(x2) + len(y1) + len(y2) + len(w1) + len(w2) + len(z)}"
    )

    return {"x1": x1, "x2": x2, "y1": y1, "y2": y2, "w1": w1, "w2": w2, "z": z}


def create_objectives(model, instance, vars_):
    x1 = vars_["x1"]
    x2 = vars_["x2"]
    y1 = vars_["y1"]
    y2 = vars_["y2"]
    z = vars_["z"]
    C1 = instance.C1
    C2 = instance.C2
    T1 = instance.T1
    T2 = instance.T2
    T3 = instance.T3
    demands = instance.demands
    hubs = instance.hubs
    covers = instance.covers

    obj_cost = pl.lpSum(C1[(i, j)] * x1[(i, j)] for (i, j) in x1.keys())
    obj_cost += pl.lpSum(C2[(i, j)] * x2[(i, j)] for (i, j) in x2.keys())

    obj_time = pl.lpSum(T1[(i, j)] * y1[(i, j, d)] for (i, j, d) in y1.keys())
    obj_time += pl.lpSum(T2[(i, j)] * y2[(i, j, d)] for (i, j, d) in y2.keys())
    obj_time += pl.lpSum(T3[(d, c)] * z[(d, c)] for d in demands for c in covers)
    obj_time += pl.lpSum(
        hubs[h].service_time * pl.lpSum(y1[(i, h, d)] for i in instance.N1 if i != h)
        for h in hubs
        for d in demands
    )
    obj_time += pl.lpSum(
        covers[c].service_time * pl.lpSum(y1[(i, c, d)] for i in instance.N1 if i != c)
        for c in covers
        for d in demands
    )
    obj_time += pl.lpSum(
        covers[j].service_time * pl.lpSum(y2[(i, j, d)] for i in instance.N2 if i != j)
        for j in covers
        for d in demands
    )
    obj_time += pl.lpSum(
        demands[j].service_time * pl.lpSum(y2[(i, j, d)] for i in instance.N2 if i != j)
        for j in demands
        for d in demands
    )

    model += obj_cost + 0.13 * obj_time


def add_flow_constraints(model, instance):
    vars_ = model._vars
    N1 = instance.N1

    x1 = vars_["x1"]
    x2 = vars_["x2"]

    for j in N1:
        lhs = pl.lpSum(x1[(i, j)] for i in N1 if i != j)
        rhs = pl.lpSum(x1[(j, i)] for i in N1 if i != j)
        model += lhs == rhs, f"flow_x1_{j}"

    for j in instance.N2:
        lhs = pl.lpSum(x2[(i, j)] for i in instance.N2 if i != j)
        rhs = pl.lpSum(x2[(j, i)] for i in instance.N2 if i != j)
        model += lhs == rhs, f"flow_x2_{j}"


def add_assignment_constraints(model, instance):
    vars_ = model._vars

    y1 = vars_["y1"]
    y2 = vars_["y2"]
    z = vars_["z"]

    for d in instance.demands:
        lhs = pl.lpSum(y1[(0, i, d)] for i in instance.N1 if i != 0)
        model += lhs == 1, f"y1_depot_out_eq_demand_{d}"

    for i in instance.N1:
        if i == 0:
            continue
        for d in instance.demands:
            model += y1[(i, 0, d)] == 0, f"y1_depot_in_zero_{i}_{d}"

    for h in instance.hubs:
        for d in instance.demands:
            for i in instance.N2:
                if i == h:
                    continue
                model += y2[(i, h, d)] == 0, f"y2_hub_in_zero_{h}_{d}_{i}"

    for d in instance.demands:
        lhs = pl.lpSum(z[(d, i)] for i in instance.N_HC)
        model += lhs == 1, f"z_assign_{d}"


def add_balance_constraints(model, instance):
    vars_ = model._vars
    N1 = instance.N1
    N2 = instance.N2
    hubs = instance.hubs
    covers = instance.covers
    demands = instance.demands

    x1 = vars_["x1"]
    x2 = vars_["x2"]
    y1 = vars_["y1"]
    y2 = vars_["y2"]
    z = vars_["z"]

    for h in hubs:
        for d in demands:
            lhs = pl.lpSum(y2[(h, i, d)] for i in N2 if h != i)
            rhs_in = pl.lpSum(y1[(i, h, d)] for i in N1 if i != h)
            rhs_out = pl.lpSum(y1[(h, i, d)] for i in N1 if h != i)
            model += lhs == rhs_in - rhs_out, f"y2_out_net_y1_{h}_{d}"

    for c in covers:
        for d in demands:
            rhs_in = pl.lpSum(y1[(i, c, d)] for i in N1 if c != i)
            rhs_out = pl.lpSum(y1[(c, i, d)] for i in N1 if c != i)
            rhs_in += pl.lpSum(y2[(i, c, d)] for i in N2 if c != i)
            rhs_out += pl.lpSum(y2[(c, i, d)] for i in N2 if c != i)
            model += z[(d, c)] == rhs_in - rhs_out, f"z_eq_net_y_{c}_{d}"

    for d in demands:
        for j in demands:
            if j == d:
                continue
            lhs = pl.lpSum(y2[(i, j, d)] for i in N2 if i != j)
            rhs = pl.lpSum(y2[(j, i, d)] for i in N2 if i != j)
            model += lhs == rhs, f"y2_flow_balance_{j}_{d}"
            
    # for d in demands:
    #     for j in N1:
    #         if j == 0:
    #             continue
    #         lhs = pl.lpSum(y1[(j, i, d)] for i in N1 if i != j)
    #         rhs = pl.lpSum(y1[(i, j, d)] for i in N1 if i != j)
    #         model += lhs <= rhs, f"y1_cover_flow_balance_{j}_{d}"

    for d in demands:
        for j in covers:
            lhs = pl.lpSum(y2[(j, i, d)] for i in N2 if i != j)
            rhs = pl.lpSum(y2[(i, j, d)] for i in N2 if i != j)
            model += lhs <= rhs, f"y2_cover_flow_balance_{j}_{d}"

    for d in demands:
        lhs1 = pl.lpSum(y2[(i, d, d)] for i in N2 if i != d)
        lhs2 = pl.lpSum(z[(d, i)] for i in covers)
        model += lhs1 + lhs2 == 1, f"y2_in_plus_z_cover_eq_one_{d}"

    for d in demands:
        for i in N2:
            if i == d:
                continue
            model += y2[(i, d, d)] == x2[(i, d)], f"y2_demand_in_eq_one_{d}_{i}"
            model += y2[(d, i, d)] == 0, f"y2_demand_out_eq_zero_{d}_{i}"

    for arc in x1.keys():
        i, j = arc
        lhs = pl.lpSum(demands[d].demand * y1[(i, j, d)] for d in demands)
        model += lhs <= instance.CAPACITY1 * x1[(i, j)], f"cap_x1_{i}_{j}"

    for arc in x2.keys():
        i, j = arc
        lhs = pl.lpSum(demands[d].demand * y2[(i, j, d)] for d in demands)
        model += lhs <= instance.CAPACITY2 * x2[(i, j)], f"cap_x2_{i}_{j}"


def add_coherency_constraints(model, instance):
    vars_ = model._vars
    N1 = instance.N1
    N2 = instance.N2
    covers = instance.covers
    demands = instance.demands

    x1 = vars_["x1"]
    x2 = vars_["x2"]
    y1 = vars_["y1"]
    y2 = vars_["y2"]
    z = vars_["z"]
    w1 = vars_["w1"]
    w2 = vars_["w2"]

    for i in N1:
        for j in N1:
            if i == j:
                continue
            if j == 0:
                continue

            model += x1[(i, j)] <= pl.lpSum(w1[(i, j, d)] for d in demands), f"coherency_x1_y1_{i}_{j}"

            for d in demands:
                model += w1[(i, j, d)] <= y1[(i, j, d)], f"coherency_w1_y1_{i}_{j}_{d}"
                model += w1[(i, j, d)] <= z[(d, j)], f"coherency_w1_z_{i}_{j}_{d}"

    for i in N2:
        for j in covers:
            if i == j:
                continue
            if j == 0:
                continue

            model += x2[(i, j)] <= pl.lpSum(w2[(i, j, d)] for d in demands), f"coherency_x2_y2_{i}_{j}"

            for d in demands:
                model += w2[(i, j, d)] <= y2[(i, j, d)], f"coherency_w2_y2_{i}_{j}_{d}"
                model += w2[(i, j, d)] <= z[(d, j)], f"coherency_w2_z_{i}_{j}_{d}"


def build_model(instance, write_lp=False):
    instance = prepare_data(instance)

    model = pl.LpProblem("two_echelon_ctp", pl.LpMinimize)

    vars_ = create_variables(model, instance)
    create_objectives(model, instance, vars_)

    model._vars = vars_

    add_flow_constraints(model, instance)
    add_assignment_constraints(model, instance)
    add_balance_constraints(model, instance)
    add_coherency_constraints(model, instance)

    # if write_lp:
    #     try:
    #         model.writeLP("two_echelon_ctp.lp")
    #     except Exception:
    #         pass

    return model