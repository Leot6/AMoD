"""
compute the best schedule for a given vehicle v and a trip T.
"""

import copy
import numpy as np
from tqdm import tqdm
from itertools import permutations
from lib.dispatcher.osp.osp_schedule import insert_req_to_sche, test_constraints_get_cost


def compute_schedule(veh_params, sub_sche, trip, T):
    num_pass_onboard = len(sub_sche)
    onboard_rids = [rid for (rid, pod, tnid, ept, ddl) in sub_sche]
    exhaustive_search_size = 5  # >=4
    n = 0
    best_sche = None
    min_cost = np.inf

    num_of_schedule_searched = 0  # the number of possible schedules considered by the algorithm
    sches_searched = []

    if num_pass_onboard < exhaustive_search_size:
        basic_sche = copy.deepcopy(sub_sche)
        n = exhaustive_search_size - num_pass_onboard
        for req in trip[:n]:
            basic_sche.extend(
                [(req.id, 1, req.onid, req.Tr, req.Clp), (req.id, -1, req.dnid, req.Tr + req.Ts, req.Cld)])
        possible_sches = permutations(basic_sche)
        for sche in possible_sches:
            sche = list(sche)
            if not verify_sequencial_constraint(sche):
                continue
            if not sche[-1][0] == sche[-2][0]:
                num_of_schedule_searched += 1
                # sches_searched.append(sche)
            flag, cost, viol = test_constraints_get_cost(veh_params, sche, 0, 0, 0, T)
            if cost < min_cost:
                best_sche = sche
                min_cost = cost
        if not best_sche:
            return None, np.inf, num_of_schedule_searched
    else:
        best_sche = sub_sche

    for req in trip[n:]:
        req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
        sche = best_sche
        best_sche = None
        min_cost = np.inf
        l = len(sche)
        for i in range(l + 1):
            for j in range(i + 1, l + 2):
                new_sche, new_sche_cost, viol = insert_req_to_sche(veh_params, sche, req_params, i, j, T)
                if not i == l + 1:
                    num_of_schedule_searched += 1
                if new_sche_cost < min_cost:
                    best_sche = new_sche
                    min_cost = new_sche_cost
        if not best_sche:
            return None, np.inf, num_of_schedule_searched

    assert {r.id for r in trip} == {rid for (rid, pod, tnid, ept, ddl) in best_sche} - set(onboard_rids)
    assert len(best_sche) == 2 * len(trip) + num_pass_onboard
    return best_sche, min_cost, num_of_schedule_searched


def verify_sequencial_constraint(sche):
    onboard_rids = []
    for (rid, pod, tnid, ept, ddl) in sche:
        if pod == 1 and rid in onboard_rids:
            return False
        if len(onboard_rids) > 3 and rid == onboard_rids[-1]:
            return False
        onboard_rids.append(rid)
    return True


# def compute_schedule_fast(veh_params, sub_sche, trip, T):
#     best_sche = None
#     min_cost = np.inf
#
#     num_of_schedule_searched = 0  # the number of possible schedules considered by the algorithm
#
#     sub_sches2 = [(sub_sche, np.inf)]
#     for req in trip[:4]:
#         sub_sches1 = sub_sches2
#         sub_sches2 = []
#         req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
#         for (sche, cost) in sub_sches1:
#             l = len(sche)
#             for i in range(l + 1):
#                 for j in range(i + 1, l + 2):
#                     new_sche, new_sche_cost, viol = insert_req_to_sche(veh_params, sche, req_params, i, j, T)
#                     num_of_schedule_searched += 1
#                     if not new_sche_cost == np.inf:
#                         sub_sches2.append((new_sche, new_sche_cost))
#
#     if len(sub_sches2) == 0:
#         return None, np.inf, num_of_schedule_searched
#
#     sub_sches2.sort(key=lambda e: e[1])
#     best_sche = sub_sches2[0][0]
#     min_cost = sub_sches2[0][1]
#
#     for req in trip[4:]:
#         sche = best_sche
#         best_sche = None
#         min_cost = np.inf
#         req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
#         l = len(sche)
#         for i in range(l + 1):
#             for j in range(i + 1, l + 2):
#                 new_sche, new_sche_cost, viol = insert_req_to_sche(veh_params, sche, req_params, i, j, T)
#                 num_of_schedule_searched += 1
#                 if not new_sche_cost == np.inf:
#                     if new_sche_cost < min_cost:
#                         best_sche = new_sche
#                         min_cost = new_sche_cost
#     return best_sche, min_cost, num_of_schedule_searched

