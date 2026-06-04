import sys

from gurobipy import GRB

from read import read_2e_ctp_instance
from gurobi.model_builder import build_model


def run(instance_file, write_lp=True):
    instance = read_2e_ctp_instance(instance_file)
    model = build_model(instance, write_lp=False)

    if write_lp:
        try:
            model.write('two_echelon_ctp.lp')
        except Exception:
            pass

    try:
        model.optimize()
    except Exception:
        print('Solver not available or optimize failed')
        return

    if model.status != GRB.OPTIMAL:
        print('No optimal solution found, status', model.status)
        return None

    for v in model.getVars():
        if abs(v.x) > 1e-6:
            print(v.varName, v.x)

    return model
