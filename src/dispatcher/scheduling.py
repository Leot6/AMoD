"""
compute all feasible schedules for a given vehicle v and a trip T.
"""

import numpy as np
import scipy.stats as st
from src.simulator.request import Req
from src.simulator.vehicle import Veh
from src.simulator.router_func import *


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh_params, sub_sches, req_params, T):
    # veh_params = [veh.nid, veh.t_to_nid, veh.load]
    # req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
    feasible_sches = []
    best_sche = None
    min_cost = np.inf
    viol = None
    for sub_sche in sub_sches:
        l = len(sub_sche)
        # insert the req's pick-up point
        for i in range(l + 1):
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                new_sche, new_sche_cost, viol = insert_req_to_sche(veh_params, sub_sche, req_params, i, j, T)
                if new_sche:
                    if new_sche_cost < min_cost:
                        best_sche = new_sche
                        min_cost = new_sche_cost
                        feasible_sches.insert(0, new_sche)
                    else:
                        feasible_sches.append(new_sche)
                # always return the first found feasible schedule (will speed up the computation)
                # if best_sche:
                if DISPATCHER != 'OSP' and best_sche:
                    assert len(feasible_sches) == 1
                    return best_sche, min_cost, feasible_sches
                if viol > 0:
                    break
            if viol == 3:
                break
    return best_sche, min_cost, feasible_sches


def insert_req_to_sche(veh_params, sub_sche, req_params, idx_p, idx_d, T):
    [rid, r_onid, r_dnid, r_Clp, r_Cld] = req_params
    new_sche = None
    new_sche_cost = np.inf

    sub_sche.insert(idx_p, (rid, 1, r_onid, r_Clp))
    sub_sche.insert(idx_d, (rid, -1, r_dnid, r_Cld))
    flag, c, viol = test_constraints_get_cost(veh_params, sub_sche, rid, idx_p, idx_d, T)

    if flag:
        new_sche = copy.copy(sub_sche)
        new_sche_cost = c
    sub_sche.pop(idx_d)
    sub_sche.pop(idx_p)
    return new_sche, new_sche_cost, viol


# test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no).
# The returned cost is the sche time, which is the same as the output of the following function "compute_sche_time".
def test_constraints_get_cost(veh_params, sche, new_rid, idx_p, idx_d, T):
    [nid, dt, n] = veh_params
    # test the capacity constraint during the whole schedule
    for (rid, pod, tnid, ddl) in sche:
        n += pod
        if n > VEH_CAPACITY:
            return False, np.inf, 1  # over capacity

    # test the pick-up and drop-off time constraint for each passenger on board
    for idx, (rid, pod, tnid, ddl) in enumerate(sche):
        dt += get_duration_from_origin_to_dest(nid, tnid)

        variance = 0
        # if IS_STOCHASTIC_SCHEDULE:
        #     variance += get_variance_from_origin_to_dest(nid, tnid)

        if idx >= idx_p and T + dt + 1 * variance > ddl:
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
    return True, dt, -1


def compute_sche_cost(veh, sche):
    nid = veh.nid
    t = veh.t_to_nid
    for (rid, pod, tnid, ddl) in sche:
        t += get_duration_from_origin_to_dest(nid, tnid)
        nid = tnid
    return t


def upd_schedule_for_vehicles_in_selected_vt_pairs(veh_trip_pairs: list, selected_veh_trip_pair_indices: list[int]):
    t = timer_start()

    for idx in selected_veh_trip_pair_indices:
        [veh, trip, sche, cost, score] = veh_trip_pairs[idx]
        for req in trip:
            req.status = OrderStatus.PICKING
        veh.build_route(sche)
        veh.sche_has_been_updated_at_current_epoch = True

    if DEBUG_PRINT:
        print(f"                *Executing assignment with {len(selected_veh_trip_pair_indices)} pairs... "
              f"({timer_end(t)})")


def compute_sche_delay(veh, sche, reqs):
    """c_delay = c_wait + c_in-veh-delay
    """
    T = veh.T
    nid = veh.nid
    t = veh.t_to_nid
    delay_sec = 0.0
    wait_sec = 0.0
    for (rid, pod, tnid, ddl) in sche:
        dt = get_duration_from_origin_to_dest(nid, tnid)
        t += dt
        wait_sec += (t + T - reqs[rid].Tr) if pod == 1 else 0
        delay_sec += (t + T - reqs[rid].Tr - reqs[rid].Ts) if pod == -1 else 0
        nid = tnid
    total_delay = wait_sec * 1.0 + delay_sec
    return delay_sec


def score_vt_pairs_with_num_of_orders_and_schedule_cost(veh_trip_pairs: list, reqs: list[Req]):
    # 1. Get the coefficients for NumOfOrders and ScheduleCost.
    max_sche_cost = 1
    for vt_pair in veh_trip_pairs:
        [veh, trip, sche, cost, score] = vt_pair
        vt_pair[3] = compute_sche_delay(veh, sche, reqs)
        if vt_pair[3] > max_sche_cost:
            max_sche_cost = vt_pair[3]
    max_sche_cost = int(max_sche_cost)
    num_length = 0
    while max_sche_cost:
        max_sche_cost //= 10
        num_length += 1
    reward_for_serving_a_req = pow(10, num_length)

    # 2. Score the vt_pairs with NumOfOrders and ScheduleCost.
    for vt_pair in veh_trip_pairs:
        vt_pair[4] = reward_for_serving_a_req * len(vt_pair[1]) - vt_pair[3]
