import sys

import gurobipy as gp
from gurobipy import GRB

from read import read_2e_ctp_instance
from gurobi.model_builder import build_model


def _status_name(status):
    for name in (
        'LOADED',
        'OPTIMAL',
        'INFEASIBLE',
        'INF_OR_UNBD',
        'UNBOUNDED',
        'CUTOFF',
        'ITERATION_LIMIT',
        'NODE_LIMIT',
        'TIME_LIMIT',
        'SOLUTION_LIMIT',
        'INTERRUPTED',
        'NUMERIC',
        'SUBOPTIMAL',
        'USER_OBJ_LIMIT',
        'WORK_LIMIT',
    ):
        value = getattr(GRB, name, None)
        if value == status:
            return name
    return f'UNKNOWN_STATUS({status})'


def _print_failure_reason(model):
    status = model.status
    status_name = _status_name(status)
    print(f'No optimal solution found: status={status_name} ({status})')

    if status == GRB.INFEASIBLE:
        print('Model is infeasible. The constraints conflict with each other.')
    elif status == GRB.INF_OR_UNBD:
        print('Model is infeasible or unbounded. Re-run with InfUnbdInfo=1 for more detail.')
    elif status == GRB.UNBOUNDED:
        print('Model is unbounded. The objective can improve without limit.')
    elif status == GRB.TIME_LIMIT:
        print('Time limit reached before proving optimality.')
    elif status == GRB.NODE_LIMIT:
        print('Node limit reached before proving optimality.')
    elif status == GRB.ITERATION_LIMIT:
        print('Iteration limit reached before proving optimality.')
    elif status == GRB.SOLUTION_LIMIT:
        print('Solution limit reached before proving optimality.')
    elif status == GRB.INTERRUPTED:
        print('Optimization was interrupted before completion.')
    elif status == GRB.NUMERIC:
        print('Numerical issues prevented Gurobi from finishing cleanly.')
    elif status == GRB.SUBOPTIMAL:
        print('Gurobi found a suboptimal solution but could not prove optimality.')
    elif status == GRB.CUTOFF:
        print('The model was cut off by the objective cutoff.')
    elif status == GRB.USER_OBJ_LIMIT:
        print('The user objective limit was reached before optimality.')
    elif status == GRB.WORK_LIMIT:
        print('Work limit reached before proving optimality.')


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
    except gp.GurobiError as exc:
        print(f'Gurobi optimization failed: {exc}')
        if getattr(exc, 'errno', None) is not None:
            print(f'Error code: {exc.errno}')
        return None
    except Exception as exc:
        print(f'Solver failed with unexpected error: {exc}')
        return None

    if model.status != GRB.OPTIMAL:
        _print_failure_reason(model)
        return None

    for v in model.getVars():
        if abs(v.x) > 1e-6:
            print(v.varName, v.x)

    return model
