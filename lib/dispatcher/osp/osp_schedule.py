"""
compute all feasible schedules for a given vehicle v and a trip T.
"""

import copy
import time
import numpy as np
import scipy.stats as st
from lib.simulator.config import VEH_CAPACITY, DISPATCHER, IS_STOCHASTIC_SCHEDULE
from lib.routing.routing_server import get_duration_from_origin_to_dest, get_variance_from_origin_to_dest, \
    get_distance_from_origin_to_dest

num_of_violation = []


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh_params, sub_sches, req_params, T):
    # veh_params = [veh.nid, veh.t_to_nid, veh.n]
    # req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
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
                # # if DISPATCHER != 'OSP' and best_sche:
                #     assert len(feasible_sches) == 1
                #     return best_sche, min_cost, feasible_sches, num_of_sche_searched
                if viol > 0:
                    break
            if viol == 3:
                break
    return best_sche, min_cost, feasible_sches, num_of_sche_searched


def insert_req_to_sche(veh_params, sub_sche, req_params, idx_p, idx_d, T):
    [rid, r_onid, r_dnid, r_Clp, r_Cld] = req_params
    new_sche = None
    new_sche_cost = np.inf

    flag = False
    if len(sub_sche) > 1 and sub_sche[0][0] == 11651:
        flag = True

    sub_sche.insert(idx_p, (rid, 1, r_onid, r_Clp))
    sub_sche.insert(idx_d, (rid, -1, r_dnid, r_Cld))
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
    for (rid, pod, tnid, ddl) in sche:
        n += pod
        if n > VEH_CAPACITY:
            return False, np.inf, 1  # over capacity

    # test the pick-up and drop-off time constraint for each passenger on board
    idx = -1
    for (rid, pod, tnid, ddl) in sche:
        idx += 1
        t += get_duration_from_origin_to_dest(nid, tnid)

        variance = 0
        # if IS_STOCHASTIC_SCHEDULE:
        #     variance += get_variance_from_origin_to_dest(nid, tnid)

        if idx >= idx_p and T + t + 1 * variance > ddl:
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
    return True, t, -1


def compute_sche_time(veh, sche):
    nid = veh.nid
    t = veh.t_to_nid
    for (rid, pod, tnid, ddl) in sche:
        t += get_duration_from_origin_to_dest(nid, tnid)
        nid = tnid
    return t


def compute_sche_delay(veh, sche, reqs_all):
    """c_delay = c_wait + c_in-veh-delay
    """
    T = veh.T
    nid = veh.nid
    t = veh.t_to_nid
    c_delay = 0.0
    c_wait = 0.0
    for (rid, pod, tnid, ddl) in sche:
        dt = get_duration_from_origin_to_dest(nid, tnid)
        t += dt
        c_wait += (t + T - reqs_all[rid].Tr) if pod == 1 else 0
        c_delay += (t + T - reqs_all[rid].Tr - reqs_all[rid].Ts) if pod == -1 else 0
        nid = tnid
    delay = c_wait * 1.0 + c_delay
    return delay


def compute_sche_reward(veh, sche, reqs_all):
    T = veh.T
    nid = veh.nid
    d = veh.d_to_nid
    income = 0.0
    t = veh.t_to_nid
    var = 0

    for (rid, pod, tnid, ddl) in sche:
        d += get_distance_from_origin_to_dest(nid, tnid)
        if IS_STOCHASTIC_SCHEDULE:
            t += get_duration_from_origin_to_dest(nid, tnid)
            var += get_variance_from_origin_to_dest(nid, tnid)
            mean = round(t, 2)
            std = round(var ** 0.5, 2)
            quantile = round(ddl - T, 2)
        if pod == -1:
            if IS_STOCHASTIC_SCHEDULE:
                cdf = round(st.norm(mean, std).cdf(quantile), 4) if std != 0 else 1.0
                # print('debug1', mean, std, quantile, cdf, reqs_all[rid].base_fee)
                if cdf < 1:
                    expected_shortfall = round(mean + std * st.norm.pdf(st.norm.ppf(cdf)) / (1 - cdf), 2)
                    extra_delay = round(expected_shortfall - quantile, 2)
                    assert extra_delay > 0
                    reqs_all[rid].update_price_est(extra_delay)
                    # print('debug2', mean, std, quantile, expected_shortfall, extra_delay, reqs_all[rid].price_est)
                else:
                    reqs_all[rid].price_est = reqs_all[rid].base_fee
                # print('debug3', mean, std, quantile, cdf, reqs_all[rid].price_est)
            income += reqs_all[rid].price_est
        nid = tnid
    outcome = round(d / 1000, 2)
    reward = income - outcome
    return reward


def compute_sche_reliability(veh, sche):
    T = veh.T
    nid = veh.nid
    average_arrival_reliability = 1.0
    t = veh.t_to_nid
    var = 0

    if IS_STOCHASTIC_SCHEDULE:
        total_cdf = 0
        num_of_reqs = 0
        for (rid, pod, tnid, ddl) in sche:
            t += get_duration_from_origin_to_dest(nid, tnid)
            var += get_variance_from_origin_to_dest(nid, tnid)
            mean = round(t, 2)
            std = round(var ** 0.5, 2)
            quantile = round(ddl - T, 2)
            if pod == -1:
                num_of_reqs += 1
                cdf = round(st.norm(mean, std).cdf(quantile), 4) if std != 0 else 1.0
                # if cdf < 0.95:
                #     print('debug', mean, std, quantile, cdf)
                total_cdf += cdf
            nid = tnid
        average_arrival_reliability = total_cdf / num_of_reqs
    return average_arrival_reliability, num_of_reqs

