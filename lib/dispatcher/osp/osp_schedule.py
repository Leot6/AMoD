"""
compute all feasible schedules for a given vehicle v and a trip T.
"""

import copy
import time
import numpy as np
from numba import jit, prange
from lib.simulator.config import VEH_CAPACITY, COEF_WAIT, DISPATCHER, IS_STOCHASTIC_CONSIDERED
from lib.routing.routing_server import get_duration_from_origin_to_dest


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh_params, sub_sches, req_params, T):
    # veh_params = [veh.nid, veh.t_to_nid, veh.n]
    # req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
    feasible_sches = []
    best_sche = None
    min_cost = np.inf
    viol = None
    num_of_sche_searched = 0  # the number of possible schedules considered by the algorithm
    sches_searched = []
    for sub_sche in sub_sches:
        l = len(sub_sche)
        # insert the req's pick-up point
        for i in range(l + 1):
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                new_sche, new_sche_cost, viol = insert_req_to_sche(veh_params, sub_sche, req_params, i, j, T)
                num_of_sche_searched += 1
                # sches_searched.append(t_sche)
                if new_sche:
                    if new_sche_cost < min_cost:
                        best_sche = new_sche
                        min_cost = new_sche_cost
                        feasible_sches.insert(0, new_sche)
                    else:
                        feasible_sches.append(new_sche)
                # always return the first found feasible schedule (will speed up the computation)
                # if best_sche:
                if not DISPATCHER == 'OSP' and best_sche:
                    assert len(feasible_sches) == 1
                    return best_sche, min_cost, feasible_sches, num_of_sche_searched
                if viol > 0:
                    break
            if viol == 3:
                break
    return best_sche, min_cost, feasible_sches, num_of_sche_searched


def insert_req_to_sche(veh_params, sub_sche, req_params, idx_p, idx_d, T):
    [rid, r_onid, r_dnid, r_Tr, r_Ts, r_Clp, r_Cld] = req_params
    new_sche = None
    new_sche_cost = np.inf
    sub_sche.insert(idx_p, (rid, 1, r_onid, r_Tr, r_Clp))
    sub_sche.insert(idx_d, (rid, -1, r_dnid, r_Tr + r_Ts, r_Cld))
    flag, c, viol = test_constraints_get_cost(veh_params, sub_sche, rid, idx_p, idx_d, T)

    # test_schedule = copy.deepcopy(sub_sche)

    if flag:
        new_sche = copy.deepcopy(sub_sche)
        new_sche_cost = c
    sub_sche.pop(idx_d)
    sub_sche.pop(idx_p)
    return new_sche, new_sche_cost, viol


# test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no)
def test_constraints_get_cost(veh_params, sche, new_rid, idx_p, idx_d, T):
    [nid, t, n] = veh_params
    # test the capacity constraint during the whole schedule
    for (rid, pod, tnid, ept, ddl) in sche:
        n += pod
        if n > VEH_CAPACITY:
            return False, np.inf, 1  # over capacity

    # test the pick-up and drop-off time constraint for each passenger on board
    idx = -1
    for (rid, pod, tnid, ept, ddl) in sche:
        idx += 1
        dt = get_duration_from_origin_to_dest(nid, tnid)
        t += dt
        if idx >= idx_p and T + t > ddl:
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
    cost = compute_sche_cost(veh_params, sche, T)
    return True, cost, -1


def compute_sche_cost(veh_params, sche, T):
    """Compute the cost of the schedule. c_delay = c_wait + c_in-veh-delay

        Args:
            veh_params: [nid_of_vehicle_location, t_to_nid, num_of_passenger_on_board]
            sche: schedule of the trip
            T: system time at current state

        Returns:
            cost
    """
    [nid, t, n] = veh_params
    c_delay = 0.0
    c_wait = 0.0
    for (rid, pod, tnid, ept, ddl) in sche:
        dt = get_duration_from_origin_to_dest(nid, tnid)
        t += dt
        n += pod
        c_wait += (t + T - ept) if pod == 1 else 0
        c_delay += (t + T - ept) if pod == -1 else 0
        nid = tnid
        # assert n <= K and round(t + T - ept) >= 0
    cost = c_wait * COEF_WAIT + c_delay
    return cost

