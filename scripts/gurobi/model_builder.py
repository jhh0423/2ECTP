import gurobipy as gp
from gurobipy import GRB

from utils import prepare_data


def create_variables(m, instance):
    N1 = instance.N1
    N2 = instance.N2

    x1 = {}
    y1 = {}
    for i in N1:
        for j in N1:
            if i == j:
                continue
            x1[(i, j)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f'x1_{i}_{j}')
            y1[(i, j)] = m.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f'y1_{i}_{j}')

    x2 = {}
    y2 = {}
    for h in instance.hubs:
        for i in N2[h]:
            for j in N2[h]:
                if i == j:
                    continue
                x2[(i, j, h)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f'x2_{i}_{j}_{h}')
                y2[(i, j, h)] = m.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f'y2_{i}_{j}_{h}')

    z = {}
    for d in instance.demands:
        for i in instance.N_HC:
            z[(d, i)] = m.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f'z_{d}_{i}')

    m.update()
    
    return {'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2, 'z': z}


def create_objectives(m, instance, vars_):
    x1 = vars_['x1']
    x2 = vars_['x2']
    y1 = vars_['y1']
    y2 = vars_['y2']
    z = vars_['z']
    C1 = instance.C1
    C2 = instance.C2
    T1 = instance.T1
    T2 = instance.T2
    T3 = instance.T3
    demands = instance.demands
    hubs = instance.hubs
    covers = instance.covers

    obj_cost = gp.quicksum(C1[(i, j)] * x1[(i, j)] for (i, j) in x1.keys())
    obj_cost += gp.quicksum(C2[(i, j, h)] * x2[(i, j, h)] for (i, j, h) in x2.keys())
    m.setObjectiveN(obj_cost, index=0, priority=1, weight=1, name='routing_cost')

    obj_time = gp.quicksum(T1[(i, j)] * y1[(i, j)] for (i, j) in y1.keys())
    obj_time += gp.quicksum(T2[(i, j, h)] * y2[(i, j, h)] for (i, j, h) in y2.keys())
    obj_time += gp.quicksum(T3[(d, c)] * demands[d].demand * z[(d, c)] for d in demands for c in covers)
    obj_time += gp.quicksum(hubs[h].service_time * gp.quicksum(y1[(i, h)] for i in instance.N1 if i != h) for h in hubs)
    obj_time += gp.quicksum(covers[c].service_time * gp.quicksum(y1[(i, c)] for i in instance.N1 if i != c) for c in covers)
    obj_time += gp.quicksum(covers[j].service_time * gp.quicksum(y2[(i, j, h)] for i in instance.N2[h] if i != j) for j in covers for h in hubs)
    obj_time += gp.quicksum(demands[j].service_time * gp.quicksum(y2[(i, j, h)] for i in instance.N2[h] if i != j) for j in demands for h in hubs)
    m.setObjectiveN(obj_time, index=1, priority=1, weight=1, name='total_time')


def add_flow_constraints(m, instance):
    vars_ = m._vars
    N1 = instance.N1

    x1 = vars_['x1']
    x2 = vars_['x2']

    for j in N1:
        lhs = gp.quicksum(x1[(i, j)] for i in N1 if i != j)
        rhs = gp.quicksum(x1[(j, i)] for i in N1 if i != j)
        m.addConstr(lhs == rhs, name=f'flow_x1_{j}')

    for h in instance.hubs:
        for j in instance.N2[h]:
            lhs = gp.quicksum(x2[(i, j, h)] for i in instance.N2[h] if i != j)
            rhs = gp.quicksum(x2[(j, i, h)] for i in instance.N2[h] if i != j)
            m.addConstr(lhs == rhs, name=f'flow_x2_{h}_{j}')


def add_assignment_constraints(m, instance):
    vars_ = m._vars

    y1 = vars_['y1']
    y2 = vars_['y2']
    z = vars_['z']

    total_demand = sum(d.demand for d in instance.demands.values())

    lhs = gp.quicksum(y1[(0, i)] for i in instance.N1 if i != 0)
    m.addConstr(lhs == total_demand, name='y1_depot_out_eq_total_demand')

    lhs = gp.quicksum(y1[(i, 0)] for i in instance.N1 if i != 0)
    m.addConstr(lhs == 0, name='y1_depot_in_zero')
    
    #for h in instance.hubs:
    #    lhs = gp.quicksum(y2[(h, i, h)] for i in instance.N2[h] if h != i)
    #    rhs = gp.quicksum(instance.demands[d_id].demand * z[(d_id, h)] for d_id in instance.demands)
    #    m.addConstr(lhs == rhs, name=f'y2_hub_{h}_out_eq_demand_assignment')
        
    for h in instance.hubs:
        lhs = gp.quicksum(y2[(i, h, h)] for i in instance.N2[h] if h != i)
        m.addConstr(lhs == 0, name=f'y2_hub_{h}_in_zero')

    for d_id in instance.demands:
        lhs = gp.quicksum(z[(d_id, i)] for i in instance.N_HC if (d_id, i) in z)
        m.addConstr(lhs == 1, name=f'z_assign_{d_id}')


def add_balance_constraints(m, instance):
    vars_ = m._vars
    N1 = instance.N1
    N2 = instance.N2
    N_HC = instance.N_HC
    hubs = instance.hubs
    covers = instance.covers
    demands = instance.demands
    
    x1 = vars_['x1']
    x2 = vars_['x2']
    y1 = vars_['y1']
    y2 = vars_['y2']
    z = vars_['z']

    for h in hubs:
        lhs = gp.quicksum(y2[(h, i, h)] for i in N2[h] if h != i)
        rhs_in = gp.quicksum(y1[(i, h)] for i in N1 if i != h)
        rhs_out = gp.quicksum(y1[(h, i)] for i in N1 if h != i)
        m.addConstr(lhs <= rhs_in - rhs_out, name=f'y2_out_le_net_y1_{h}')

    for i in covers:
        lhs = gp.quicksum(demands[d].demand * z[(d, i)] for d in demands)
        rhs_y1_in = gp.quicksum(y1[(j, i)] for j in N1 if i != j)
        rhs_y1_out = gp.quicksum(y1[(i, j)] for j in N1 if i != j)
        rhs_y2_in = gp.quicksum(y2[(j, i, h)] for h in hubs for j in N2[h] if j != i)
        rhs_y2_out = gp.quicksum(y2[(i, j, h)] for h in hubs for j in N2[h] if j != i)
        m.addConstr(lhs <= rhs_y1_in - rhs_y1_out + rhs_y2_in - rhs_y2_out, name=f'cover_balance_{i}')

    for i in N_HC:
        lhs = gp.quicksum(y1[(i, j)] for j in N1 if i != j)
        rhs = gp.quicksum(y1[(j, i)] for j in N1 if i != j)
        m.addConstr(lhs <= rhs, name=f'y1_out_le_in_{i}')

    for h in hubs:
        for i in N2[h]:
            if i == h:
                continue
            lhs = gp.quicksum(y2[(i, j, h)] for j in N2[h] if i != j)
            rhs = gp.quicksum(y2[(j, i, h)] for j in N2[h] if j != i)
            m.addConstr(lhs <= rhs, name=f'y2_out_le_in_{h}_{i}')

    for d in demands:
        for h in hubs:
            lhs = demands[d].demand * z[(d, h)]
            rhs_in = gp.quicksum(y2[(i, d, h)] for i in N2[h] if i != d)
            rhs_out = gp.quicksum(y2[(d, i, h)] for i in N2[h] if i != d)
            m.addConstr(lhs <= rhs_in - rhs_out, name=f'demand_net_in_{d}_{h}')

    for key, yvar in y1.items():
        m.addConstr(yvar <= instance.CAPACITY1 * x1[key], name=f'cap_y1_{key[0]}_{key[1]}')

    for key, yvar in y2.items():
            m.addConstr(yvar <= instance.CAPACITY2 * x2[key], name=f'cap_y2_{key[0]}_{key[1]}_{key[2]}')


def build_model(instance, write_lp=False):
    instance = prepare_data(instance)

    m = gp.Model('two_echelon_ctp')
    m.setParam('OutputFlag', 0)

    vars_ = create_variables(m, instance)
    create_objectives(m, instance, vars_)

    m._vars = vars_
    
    add_flow_constraints(m, instance)
    add_assignment_constraints(m, instance)
    add_balance_constraints(m, instance)

    if write_lp:
        m.write('two_echelon_ctp.lp')

    return m