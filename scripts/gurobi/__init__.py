"""Gurobi-specific model modules."""
# import os
# import gurobipy as gp

# # Change the hostname to avoid 502 bad gateway error
# os.environ['COMPUTERNAME'] = 'GurobiLocalClient'
# os.environ['HOSTNAME'] = 'GurobiLocalClient'

# WLS_CONFIG = {
#     'WLSACCESSID': '6adf5c98-6e47-4ca4-bb30-bed36b0cd499',
#     'WLSSECRET': 'aebdebf1-f12c-4f19-a8a5-8cc3cfd8cc7c',
#     'LICENSEID': 2834132,
# }

# def setup_gurobi_env():
#     env = gp.Env(params=WLS_CONFIG)
#     model = gp.Model('two_echelon_ctp', env=env)
#     return model