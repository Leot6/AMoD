"""
compute all feasible schedules for given vehicle v and trip T.
"""

import copy
import time
import numpy as np
from lib.Configure import COEF_WAIT, COEF_INVEH, IS_STOCHASTIC_CONSIDERED
from lib.Route import get_duration, get_path_from_SPtable, k_shortest_paths_nx, get_edge_dur, get_edge_std


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh, trip, _trip, _schedules):
    best_schedule = None
    min_cost = np.inf
    feasible_schedules = []
    ealist_pick_up_point = 0
    ealist_drop_off_point = 0
    viol = None

    req = tuple(set(trip) - set(_trip))[0]
    assert len(trip) - len(_trip) == 1

    for schedule in _schedules:
        # # check if the req has same origin-destination as any other req in the schedule
        # p = set()
        # d = set()
        # for (rid, pod, tnid, ddl) in schedule:
        #     if pod == 1 and req.onid == tnid:
        #         p.add(rid)
        #         # print(' # check if the req has same origin as any other req in the schedule')
        #     if pod == -1 and req.dnid == tnid:
        #         d.add(rid)
        #         # print(' # check if the req has same destination as any other req in the schedule')
        # same_req = p & d
        # if len(same_req) > 0:
        #     print(' # check if the req has same origin-destination as any other req in the schedule')
        #     i = 0
        #     i_p = 0
        #     i_d = 0
        #     for (rid, pod, tnid, ddl) in schedule:
        #         i += 1
        #         if pod == 1 and rid in same_req:
        #             if req.Clp <= ddl:
        #                 i_p = i-1
        #             else:
        #                 i_p = i
        #         if pod == -1 and rid in same_req:
        #             if req.Cld <= ddl:
        #                 i_d = i
        #             else:
        #                 i_d = i+1
        #     schedule.insert(i_p, (req.id, 1, req.onid, req.Clp))
        #     schedule.insert(i_d, (req.id, -1, req.dnid, req.Cld))
        #     flag, c, viol = test_constraints_get_cost(schedule, veh, req, i_d)
        #     if flag:
        #         feasible_schedules.append(copy.deepcopy(schedule))
        #         best_schedule = copy.deepcopy(schedule)
        #         min_cost = c
        #     schedule.pop(i_d)
        #     schedule.pop(i_p)
        #     return best_schedule, min_cost, feasible_schedules

        # # debug
        # if {r.id for r in trip} == {56, 505}:
        #     print()
        #     print('veh', veh.id)
        #     print('_sche', [(rid, pod) for (rid, pod, tnid, ddl) in schedule])

        l = len(schedule)
        # if the direct pick-up of req is longer than the time constrain of a req already in the schedule,
        # then it cannot be picked-up before that req. (seems not work as expected)
        dt = get_duration(veh.nid, req.onid) + veh.t_to_nid
        for i in reversed(range(l)):
            if veh.T + dt > schedule[i][3]:
                ealist_pick_up_point = i + 1
                break
        # if the shortest travel time of req is longer than the time constrain of a leg in the schedule,
        # it cannot be dropped-off before that leg.
        for i in reversed(range(l)):
            if veh.T + req.Ts > schedule[i][3]:
                ealist_drop_off_point = i + 2
                break

        # insert the req's pick-up point
        for i in range(l + 1):
            if i < ealist_pick_up_point:
                continue
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                viol = 0
                if j < ealist_drop_off_point:
                    continue
                schedule.insert(i, (req.id, 1, req.onid, req.Clp, None))
                schedule.insert(j, (req.id, -1, req.dnid, req.Cld, None))
                flag, c, viol = test_constraints_get_cost(veh, trip, schedule, req, j)  # j: req's drop-off point index
                if flag:
                    feasible_schedules.append(copy.deepcopy(schedule))
                    if c < min_cost:
                        best_schedule = copy.deepcopy(schedule)
                        min_cost = c
                schedule.pop(j)
                schedule.pop(i)
                if viol > 0:
                    break
            if viol == 3:
                break

    return best_schedule, min_cost, feasible_schedules


# test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no)
def test_constraints_get_cost(veh, trip, schedule, newly_insert_req, new_req_drop_idx):
    t = veh.t_to_nid
    n = veh.n
    T = veh.T
    K = veh.K
    nid = veh.nid
    insert_req_id = newly_insert_req.id

    # test the capacity constraint during the whole schedule
    for (rid, pod, tnid, ddl, pf_path) in schedule:
        n += pod
        if n > K:
            return False, None, 1  # over capacity

    # test the pick-up and drop-off time constraint for each passenger on board
    idx = -1
    for (rid, pod, tnid, ddl, pf_path) in schedule:
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

            # # solution 2
            # if ddl + 50 > T + t + 1.5 * standard_deviation > ddl:
            #     KSP = k_shortest_paths_nx(nid, tnid, 10, 'dur')
            #     best_mean = np.inf
            #     best_thre = np.inf
            #     for path in KSP:
            #         mean = 0
            #         variance = 0.0
            #         for i in range(len(path) - 1):
            #             u = path[i]
            #             v = path[i + 1]
            #             mean += get_edge_dur(u, v)
            #             variance += get_edge_std(u, v)
            #         standard_deviation = np.sqrt(variance)
            #         mean = round(mean, 2)
            #         thre = round(mean + 1.5 * standard_deviation, 2)
            #         if thre < best_thre:
            #             best_thre = thre
            #             best_mean = mean
            #     standard_deviation = (best_thre - best_mean) / 1.5
            #     t = t - dt + best_mean
        else:
            standard_deviation = 0

        if T + t + 2.5 * standard_deviation > ddl:
            if rid == insert_req_id:
                # pod == -1 means a new pick-up insertion is needed, since later drop-off brings longer travel time
                # pod == 1 means no more feasible schedules is available, since later pick-up brings longer wait time
                return False, None, 2 if pod == -1 else 3
            if idx < new_req_drop_idx:
                # idx<=new_req_drop_idx means the violation is caused by the pick-up of req,
                # since the violation happens before the drop-off of req
                return False, None, 4
            return False, None, 0
        nid = tnid

    cost = compute_schedule_cost(veh, trip, schedule)
    return True, cost, -1


# compute the schedule cost, used to update the costs in VT table
def compute_schedule_cost(veh, trip, schedule):
    c_delay = 0.0
    c_wait = 0.0
    # c_inveh = 0.0
    t = veh.t_to_nid
    n = veh.n
    T = veh.T
    nid = veh.nid
    reqs_in_schedule = list(trip) + list(veh.onboard_reqs)
    for (rid, pod, tnid, ddl, pf_path) in schedule:
        dt = get_duration(nid, tnid)
        t += dt
        # c_inveh += n * dt * COEF_INVEH
        n += pod
        assert n <= veh.K
        c_wait += t * COEF_WAIT if pod == 1 else 0
        if pod == -1:
            for req in reqs_in_schedule:
                if rid == req.id:
                    if T + t - (req.Tr + req.Ts) > 0:
                        c_delay += round(T + t - (req.Tr + req.Ts))
                    break
        nid = tnid
    cost = c_delay
    # cost = c_wait + c_delay
    # cost = c_wait
    return cost

