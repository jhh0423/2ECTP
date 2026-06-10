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
            
            for d in instance.demands:
                y1[(i, j, d)] = m.addVar(vtype=GRB.BINARY, name=f'y1_{i}_{j}_{d}')

    x2 = {}
    y2 = {}
    for i in N2:
        for j in N2:
            if i == j:
                continue
            x2[(i, j)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f'x2_{i}_{j}')
            
            for d in instance.demands:
                y2[(i, j, d)] = m.addVar(vtype=GRB.BINARY, name=f'y2_{i}_{j}_{d}')

    z = {}
    for d in instance.demands:
        for i in instance.N_HC:
            z[(d, i)] = m.addVar(vtype=GRB.BINARY, name=f'z_{d}_{i}')

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
    obj_cost += gp.quicksum(C2[(i, j)] * x2[(i, j)] for (i, j) in x2.keys())
    m.setObjectiveN(obj_cost, index=0, priority=1, weight=1, name='routing_cost')

    obj_time = gp.quicksum(T1[(i, j)] * y1[(i, j, d)] for (i, j, d) in y1.keys())
    obj_time += gp.quicksum(T2[(i, j)] * y2[(i, j, d)] for (i, j, d) in y2.keys())
    obj_time += gp.quicksum(T3[(d, c)] * z[(d, c)] for d in demands for c in covers)
    obj_time += gp.quicksum(hubs[h].service_time * gp.quicksum(y1[(i, h, d)] for i in instance.N1 if i != h) for h in hubs for d in demands)
    obj_time += gp.quicksum(covers[c].service_time * gp.quicksum(y1[(i, c, d)] for i in instance.N1 if i != c) for c in covers for d in demands)
    obj_time += gp.quicksum(covers[j].service_time * gp.quicksum(y2[(i, j, d)] for i in instance.N2 if i != j) for j in covers for d in demands)
    obj_time += gp.quicksum(demands[j].service_time * gp.quicksum(y2[(i, j, d)] for i in instance.N2 if i != j) for j in demands for d in demands)
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

    for j in instance.N2:
        lhs = gp.quicksum(x2[(i, j)] for i in instance.N2 if i != j)
        rhs = gp.quicksum(x2[(j, i)] for i in instance.N2 if i != j)
        m.addConstr(lhs == rhs, name=f'flow_x2_{j}')


def add_assignment_constraints(m, instance):
    vars_ = m._vars

    y1 = vars_['y1']
    y2 = vars_['y2']
    z = vars_['z']

    for d in instance.demands:
        lhs = gp.quicksum(y1[(0, i, d)] for i in instance.N1 if i != 0)
        m.addConstr(lhs == 1, name=f'y1_depot_out_eq_demand_{d}')

    for i in instance.N1:
        if i == 0:
            continue
        for d in instance.demands:
            m.addConstr(y1[(i, 0, d)] == 0, name=f'y1_depot_in_zero_{i}_{d}')
            
    for h in instance.hubs:
        for d in instance.demands:
            for i in instance.N2:
                if i == h:
                    continue
                m.addConstr(y2[(i, h, d)] == 0, name=f'y2_hub_in_zero_{h}_{d}')
                
    for d in instance.demands:
        lhs = gp.quicksum(z[(d, i)] for i in instance.N_HC)
        m.addConstr(lhs == 1, name=f'z_assign_{d}')
        

def add_balance_constraints(m, instance):
    vars_ = m._vars
    N1 = instance.N1
    N2 = instance.N2
    hubs = instance.hubs
    covers = instance.covers
    demands = instance.demands
    
    x1 = vars_['x1']
    x2 = vars_['x2']
    y1 = vars_['y1']
    y2 = vars_['y2']
    z = vars_['z']

    for h in hubs:
        for d in demands:
            lhs = gp.quicksum(y2[(h, i, d)] for i in N2 if h != i)
            rhs_in = gp.quicksum(y1[(i, h, d)] for i in N1 if i != h)
            rhs_out = gp.quicksum(y1[(h, i, d)] for i in N1 if h != i)
            m.addConstr(lhs == rhs_in - rhs_out, name=f'y2_out_net_y1_{h}')
    
    for h in hubs:
        for d in demands:
            rhs = gp.quicksum(y2[(h, i, d)] for i in N2 if h != i)
            m.addConstr(z[(d, h)] == rhs, name=f'z_leq_y2_hub_{h}_{d}')
    
    for c in covers:
        for d in demands:
            rhs_in = gp.quicksum(y1[(i, c, d)] for i in N1 if c != i)
            rhs_out = gp.quicksum(y1[(c, i, d)] for i in N1 if c != i)
            rhs_in += gp.quicksum(y2[(i, c, d)] for i in N2 if c != i)
            rhs_out += gp.quicksum(y2[(c, i, d)] for i in N2 if c != i)
            m.addConstr(z[(d, c)] == rhs_in - rhs_out, name=f'z_eq_net_y_{c}_{d}')
    
    for d in demands:
        for j in N2:
            if j == d:
                continue
            lhs = gp.quicksum(y2[(i, j, d)] for i in N2 if i != j)
            rhs = gp.quicksum(y2[(j, i, d)] for i in N2 if i != j)
            m.addConstr(lhs == rhs, name=f'y2_flow_balance_{j}_{d}')
            
    for d in demands:
        lhs1 = gp.quicksum(y2[(i, d, d)] for i in N2 if i != d)
        lhs2 = gp.quicksum(z[(d, i)] for i in covers)
        m.addConstr(lhs1 + lhs2 == 1, name=f'y2_in_plus_z_cover_eq_one_{d}')

    for d in demands:
        for i in N2:
            if i == d:
                continue
            m.addConstr(y2[(i, d, d)] == x2[(i, d)], name=f'y2_demand_in_eq_one_{d}')
            m.addConstr(y2[(d, i, d)] == 0, name=f'y2_demand_out_eq_zero_{d}')

    for arc in x1.keys():
        i, j = arc
        lhs = gp.quicksum(demands[d].demand * y1[(i, j, d)] for d in demands)
        m.addConstr(lhs <= instance.CAPACITY1 * x1[(i, j)], name=f'cap_x1_{i}_{j}')
            
    for arc in x2.keys():
        i, j = arc
        lhs = gp.quicksum(demands[d].demand * y2[(i, j, d)] for d in demands)
        m.addConstr(lhs <= instance.CAPACITY2 * x2[(i, j)], name=f'cap_x2_{i}_{j}')


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