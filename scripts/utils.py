from math import hypot


def euclid(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def gather_coord_map(instance):
    COORD = {}
    if instance.DEPOT:
        COORD[0] = instance.DEPOT

    for d in instance.demands:
        COORD[d] = (instance.demands[d].x, instance.demands[d].y)

    for c in instance.covers:
        COORD[c] = (instance.covers[c].x, instance.covers[c].y)

    for h in instance.hubs:
        COORD[h] = (instance.hubs[h].x, instance.hubs[h].y)

    return COORD


def build_cost_matrices(instance, coord):
    COST1 = instance.COST1
    COST2 = instance.COST2
    TIME1 = instance.TIME1
    TIME2 = instance.TIME2
    TIME3 = instance.TIME3
    
    N1 = [0] + list(instance.covers.keys()) + list(instance.hubs.keys())  # depot + covers + hubs
    C1 = {}
    T1 = {}
    for i in N1:
        for j in N1:
            if i == j:
                continue
            
            C1[(i, j)] = COST1 * euclid(coord[i], coord[j])
            T1[(i, j)] = TIME1 * euclid(coord[i], coord[j])
    
    N2 = {}
    C2 = {}
    T2 = {}
    for h in instance.hubs.keys():
        N2[h] = [h] + list(instance.covers.keys()) + list(instance.demands.keys())
        for i in N2[h]:
            for j in N2[h]:
                if i == j:
                    continue

                C2[(i, j, h)] = COST2 * euclid(coord[i], coord[j])
                T2[(i, j, h)] = TIME2 * euclid(coord[i], coord[j])
        
    T3 = {}
    for c in instance.covers.keys():
        for d in instance.demands.keys():
            T3[(d, c)] = TIME3 * euclid(coord[d], coord[c])
    
    N_HC = list(instance.hubs.keys()) + list(instance.covers.keys())

    return {'N1': N1, 'N2': N2, 'N_HC': N_HC, 'C1': C1, 'C2': C2, 'T1': T1, 'T2': T2, 'T3': T3}


def prepare_data(instance):
    COORD = gather_coord_map(instance)
    result = build_cost_matrices(instance, COORD)
    
    instance.COORD = COORD
    instance.N1 = result['N1']
    instance.N2 = result['N2']
    instance.N_HC = result['N_HC']
    instance.C1 = result['C1']
    instance.C2 = result['C2']
    instance.T1 = result['T1']
    instance.T2 = result['T2']
    instance.T3 = result['T3']

    return instance