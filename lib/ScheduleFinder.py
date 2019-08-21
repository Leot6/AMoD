"""
compute all feasible schedules for given vehicle v and trip T.
"""

import copy
import time
import numpy as np
from lib.Configure import COEF_WAIT, COEF_INVEH, IS_STOCHASTIC_CONSIDERED
from lib.Route import get_duration, get_path_from_SPtable, k_shortest_paths_nx, get_edge_mean_dur, get_edge_std


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh, trip, _trip, _schedules):
    feasible_schedules = []
    best_schedule = None
    min_cost = np.inf
    ealist_pick_up_point = 0
    ealist_drop_off_point = 0
    viol = None

    req = tuple(set(trip) - set(_trip))[0]
    assert len(trip) - len(_trip) == 1

    # check if the req has same origin-destination as any other req in the schedule
    same_pick = set()
    same_drop = set()
    # for (rid, pod, tnid, ddl, pf_path) in _schedules[0]:
    #     if pod == 1 and req.onid == tnid:
    #         same_pick.add(rid)
    #     if pod == -1 and req.dnid == tnid:
    #         same_drop.add(rid)

    for schedule in _schedules:
        # if len(same_req) > 0:
        # if len(p) > 0 or len(d) > 0:
        #     i_p = 0
        #     i_d = 0
        #     for idx, (rid, pod, tnid, ddl, pf_path) in zip(range(len(schedule)), schedule):
        #         if rid in same_req and pod == 1:
        #         # if rid in p and pod == 1:
        #             if req.Clp <= ddl:
        #                 i_p = idx
        #             else:
        #                 i_p = idx + 1
        #         if rid in same_req and pod == -1:
        #         # if rid in d and pod == -1:
        #             if req.Cld <= ddl:
        #                 i_d = idx + 1
        #             else:
        #                 i_d = idx + 2
        #
        #     # print()
        #     # print(' # check same OD in the sche, veh %d, req %d, subtrip %s, num of sches %d'
        #     #       % (veh.id, req.id, [req.id for req in _trip], len(_schedules)))
        #     # print('insert req %d, onid & dnind %s, Tr %d, ddl %s'
        #     #       % (req.id, [req.onid, req.dnid], req.Tr, [req.Clp, req.Cld]))
        #     # print('                 origin geo %s' % [req.olng, req.olat])
        #     # print('                 destin geo %s' % [req.dlng, req.dlat])
        #     # print('SubSche rid %s' % [rid for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print('SubSche pod %s' % [pod for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print('SubSche nid %s' % [tnid for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print('SubSche ddl %s' % [ddl for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print(' - same OD found %s' % same_req)
        #     # print(' - same pn found %s' % p)
        #     # print(' - same dn found %s' % d)
        #     # for req1 in _trip:
        #     #     if req1.id in same_req:
        #     #         print('    same req %d, onid & dnind %s, Tr %d, ddl %s'
        #     #               % (req1.id, [req1.onid, req1.dnid], req1.Tr, [req1.Clp, req1.Cld]))
        #     #         print('                 origin geo %s' % [req1.olng, req1.olat])
        #     #         print('                 destin geo %s' % [req1.dlng, req1.dlat])
        #     # print(' - insertion point %s' % [i_p, i_d])
        #
        #     schedule.insert(i_p, (req.id, 1, req.onid, req.Clp, None))
        #     schedule.insert(i_d, (req.id, -1, req.dnid, req.Cld, None))
        #
        #     # print(' - insertion sche %s' % [rid for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print(' - insertion sche %s' % [pod for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print(' - insertion sche %s' % [tnid for (rid, pod, tnid, ddl, pf_path) in schedule])
        #     # print(' - insertion sche %s' % [ddl for (rid, pod, tnid, ddl, pf_path) in schedule])
        #
        #     flag, c, viol = test_constraints_get_cost(veh, trip, schedule, req, i_p, i_d)
        #     if flag:
        #         feasible_schedules.append(copy.deepcopy(schedule))
        #         if c < min_cost:
        #             best_schedule = copy.deepcopy(schedule)
        #             min_cost = c
        #     schedule.pop(i_d)
        #     schedule.pop(i_p)
        #     continue

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
            if veh.T + dt + req.Ts > schedule[i][3]:
                ealist_drop_off_point = i + 2
                break

        # # new added code starts
        # # for repeat computation caused by same pick/drop node
        # (seems no effect, and will reduce the service rate a little, around 0.1%)
        # idx_same_pick = -1
        # idx_same_drop = -1
        # if len(same_pick) > 0 or len(same_drop) > 0:
        #     for idx, (rid, pod, tnid, ddl, pf_path) in zip(range(len(schedule)), schedule):
        #         if rid in same_pick and pod == 1:
        #             if req.Clp <= ddl:
        #                 idx_same_pick = idx
        #             else:
        #                 idx_same_pick = idx + 1
        #         if rid in same_drop and pod == -1:
        #             if req.Cld <= ddl:
        #                 idx_same_drop = idx + 1
        #             else:
        #                 idx_same_drop = idx + 2
        # if idx_same_pick != -1 and idx_same_drop != -1:
        #     idx_p = idx_same_pick
        #     idx_d = idx_same_drop
        #     best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, idx_p, idx_d,
        #                                                            best_schedule, min_cost, feasible_schedules)
        #     break
        # if idx_same_pick != -1 and idx_same_drop == -1:
        #     idx_p = idx_same_pick
        #     for idx_d in range(idx_p + 1, l + 2):
        #         if idx_d < ealist_drop_off_point:
        #             continue
        #         best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, idx_p, idx_d,
        #                                                                best_schedule, min_cost, feasible_schedules)
        #         if viol > 0:
        #             break
        #     break
        # if idx_same_pick == -1 and idx_same_drop != -1:
        #     idx_d = idx_same_drop
        #     for idx_p in range(idx_d):
        #         if idx_p < ealist_pick_up_point:
        #             continue
        #         best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, idx_p, idx_d,
        #                                                                best_schedule, min_cost, feasible_schedules)
        #         if viol == 3:
        #             break
        #     break
        # # new added code ends

        # insert the req's pick-up point
        for i in range(l + 1):
            if i < ealist_pick_up_point:
                continue
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                if j < ealist_drop_off_point:
                    continue
                best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, i, j,
                                                                       best_schedule, min_cost, feasible_schedules)
                if viol > 0:
                    break
            if viol == 3:
                break
    return best_schedule, min_cost, feasible_schedules


def insert_req_to_schedule(veh, trip, _schedule, req, idx_p, idx_d, best_sche, min_cost, feasible_schedules):
    new_best_schedule = best_sche
    new_min_cost = min_cost
    _schedule.insert(idx_p, (req.id, 1, req.onid, req.Clp, None))
    _schedule.insert(idx_d, (req.id, -1, req.dnid, req.Cld, None))
    flag, c, viol = test_constraints_get_cost(veh, trip, _schedule, req, idx_p, idx_d)
    if flag:
        feasible_schedules.append(copy.deepcopy(_schedule))
        if c < min_cost:
            new_best_schedule = copy.deepcopy(_schedule)
            new_min_cost = c
    _schedule.pop(idx_d)
    _schedule.pop(idx_p)
    return new_best_schedule, new_min_cost, viol


# test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no)
def test_constraints_get_cost(veh, trip, schedule, newly_insert_req, new_req_pick_idx, new_req_drop_idx):
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
            #             mean += get_edge_mean_dur(u, v)
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

        if idx >= new_req_pick_idx and T + t + 2.5 * standard_deviation > ddl:
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
    # cost = c_delay
    cost = c_wait + c_delay
    # cost = c_wait
    return cost

