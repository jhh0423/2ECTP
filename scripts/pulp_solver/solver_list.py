import pulp as pl

solver_list = pl.listSolvers(onlyAvailable=True)
print("Available solvers:")
for solver in solver_list:
    print(f"- {solver}")