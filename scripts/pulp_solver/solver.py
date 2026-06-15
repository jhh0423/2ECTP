import pulp as pl

from read import read_2e_ctp_instance
from pulp_solver.model_builder import build_model


def _status_name(status):
    return pl.LpStatus.get(status, f"UNKNOWN_STATUS({status})")


def _print_failure_reason(model):
    status = model.status
    status_name = _status_name(status)
    print(f"No optimal solution found: status={status_name} ({status})")

    if status == pl.LpStatusInfeasible:
        print("Model is infeasible. The constraints conflict with each other.")
    elif status == pl.LpStatusUnbounded:
        print("Model is unbounded. The objective can improve without limit.")
    elif status == pl.LpStatusNotSolved:
        print("Solver did not finish or no feasible solution was found.")
    elif status == pl.LpStatusUndefined:
        print("Solver returned an undefined status.")


def run(instance_file, write_lp=True):
    instance = read_2e_ctp_instance(instance_file)
    model = build_model(instance, write_lp=False)

    try:
        #model.solve(pl.SCIP_PY())
        model.solve(pl.HiGHS())
    except Exception as exc:
        print(f"Solver failed with unexpected error: {exc}")
        return None

    if model.status != pl.LpStatusOptimal:
        _print_failure_reason(model)
        return None

    for v in model.variables():
        value = v.varValue if v.varValue is not None else 0.0
        try:
            v.x = value
            v.X = value
        except Exception:
            pass
        if abs(value) > 1e-6:
            print(v.name, round(value, 5))

    return model