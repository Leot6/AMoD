"""
compute all feasible schedules for given vehicle v and trip T.
"""

import copy
import time
import numpy as np
from numba import jit, prange
from lib.Configure import COEF_WAIT, DISPATCHER, IS_STOCHASTIC_CONSIDERED
from lib.S_Route import get_duration, get_path_from_SPtable, get_edge_std


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh_params, sub_S, req_params, T, K):
    # veh_params = [veh.nid, veh.t_to_nid, veh.n]
    # req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
    feasible_sches = []
    best_sche = None
    min_cost = np.inf
    viol = None

    n_s_c = 0  # the number of possible schedules algorithm considers

    for sub_sche in sub_S:
        l = len(sub_sche)
        for i in range(l + 1):
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                new_sche, new_sche_cost, viol = insert_req_to_sche(veh_params, sub_sche, req_params, i, j, T, K)
                n_s_c += 1
                if not new_sche_cost == np.inf:
                    feasible_sches.append(new_sche)
                    if new_sche_cost < min_cost:
                        best_sche = new_sche
                        min_cost = new_sche_cost
                # always return the first found feasible schedule (will speed up the computation)
                # if best_sche:
                if DISPATCHER == 'GI' and best_sche:
                    assert len(feasible_sches) == 1
                    return best_sche, min_cost, feasible_sches
                if viol > 0:
                    break
            if viol == 3:
                break
    return best_sche, min_cost, feasible_sches, n_s_c


def insert_req_to_sche(veh_params, sub_sche, req_params, idx_p, idx_d, T, K):
    [rid, r_onid, r_dnid, r_Tr, r_Ts, r_Clp, r_Cld] = req_params
    new_sche = None
    new_sche_cost = np.inf
    sub_sche.insert(idx_p, (rid, 1, r_onid, r_Tr, r_Clp))
    sub_sche.insert(idx_d, (rid, -1, r_dnid, r_Tr + r_Ts, r_Cld))
    flag, c, viol = test_constraints_get_cost(veh_params, sub_sche, rid, idx_p, idx_d, T, K)

    if flag:
        new_sche = copy.deepcopy(sub_sche)
        new_sche_cost = c
    sub_sche.pop(idx_d)
    sub_sche.pop(idx_p)
    return new_sche, new_sche_cost, viol


# test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no)
def test_constraints_get_cost(veh_params, sche, new_rid, idx_p, idx_d, T, K):
    [nid, t, n] = veh_params
    # test the capacity constraint during the whole schedule
    for (rid, pod, tnid, ept, ddl) in sche:
        n += pod
        if n > K:
            return False, np.inf, 1  # over capacity

    # test the pick-up and drop-off time constraint for each passenger on board
    idx = -1
    for (rid, pod, tnid, ept, ddl) in sche:
        idx += 1
        dt = get_duration(nid, tnid)
        t += dt

        # temp solution
        if IS_STOCHASTIC_CONSIDERED and T + t <= ddl:
            # solution 1
            path = get_path_from_SPtable(nid, tnid)
            variance = 0
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                variance += np.square(get_edge_std(u, v))
            standard_deviation = np.sqrt(variance)
        else:
            standard_deviation = 0

        if idx >= idx_p and T + t + 1 * standard_deviation > ddl:
            if rid == new_rid:
                # pod == -1 means a new pick-up insertion is needed, since later drop-off brings longer travel time
                # pod == 1 means no more feasible schedules is available, since later pick-up brings longer wait time
                return False, np.inf, 2 if pod == -1 else 3
            if idx < idx_d:
                # idx<=new_req_drop_idx means the violation is caused by the pick-up of req,
                # since the violation happens before the drop-off of req
                return False, np.inf, 4
            return False, np.inf, 0
        nid = tnid
    cost = compute_sche_cost(veh_params, sche, T, K)
    return True, cost, -1


# compute the schedule cost, used to update the costs in VT table (c_delay = c_wait + c_in-veh-delay)
def compute_sche_cost(veh_params, sche, T, K):
    [nid, t, n] = veh_params
    c_delay = 0.0
    c_wait = 0.0
    for (rid, pod, tnid, ept, ddl) in sche:
        dt = get_duration(nid, tnid)
        t += dt
        n += pod
        c_wait += (t + T - ept) if pod == 1 else 0
        c_delay += (t + T - ept) if pod == -1 else 0
        nid = tnid
        # assert n <= K and round(t + T - ept) >= 0
    cost = c_wait * COEF_WAIT + c_delay
    return cost

