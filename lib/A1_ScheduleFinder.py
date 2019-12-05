"""
compute all feasible schedules for given vehicle v and trip T.
"""

import copy
import time
import numpy as np
from lib.Configure import COEF_WAIT, COEF_INVEH, IS_STOCHASTIC_CONSIDERED
from lib.S_Route import get_duration, get_path_from_SPtable, k_shortest_paths_nx, get_edge_mean_dur, get_edge_std


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh, trip, _trip, _schedules):
    # test
    aa = time.time()

    feasible_schedules = []
    best_schedule = None
    min_cost = np.inf
    ealist_pick_up_point = 0
    ealist_drop_off_point = 0
    viol = None

    req = tuple(set(trip) - set(_trip))[0]
    assert len(trip) - len(_trip) == 1

    # check if the req has same origin/destination as any other req in the schedule
    same_pick = set()
    same_drop = set()
    for (rid, pod, tnid, ddl, pf_path) in _schedules[0]:
        if req.onid == tnid:
            same_pick.add(rid)
        if req.dnid == tnid:
            same_drop.add(rid)

    for schedule in _schedules:
        l = len(schedule)
        # if the direct pick-up of req is longer than the time constraint of any req already in the schedule,
        # then it cannot be picked-up before that req. (seems not saving time as expected)
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

        # new added code starts
        # for repeat computation caused by same pick/drop node
        # (seems no effect, and will reduce the service rate a little, around 0.1%)
        idx_same_pick = -1
        idx_same_drop = -1
        # get the index of same origin/destination in the schedule
        if len(same_pick) > 0 or len(same_drop) > 0:
            for idx, (rid, pod, tnid, ddl, pf_path) in zip(range(len(schedule)), schedule):
                if req.onid == tnid:
                    idx_same_pick = idx if req.Clp <= ddl else idx + 1
                    if pod == -1:
                        idx_same_pick = idx + 1
                elif req.dnid == tnid:
                    idx_same_drop = idx + 1 if req.Cld <= ddl else idx + 2
                    if pod == 1:
                        idx_same_drop = idx + 1
                        break

        # # same origin and destination
        # if idx_same_pick != -1 and idx_same_drop != -1:
        #     idx_p = idx_same_pick
        #     idx_d = idx_same_drop
        #     best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, idx_p, idx_d,
        #                                                            best_schedule, min_cost, feasible_schedules)
        #     continue
        # # same origin only
        # if idx_same_pick != -1 and idx_same_drop == -1:
        #     idx_p = idx_same_pick
        #     # insert the req's drop-off point
        #     for idx_d in range(idx_p + 1, l + 2):
        #         if idx_d < ealist_drop_off_point:
        #             continue
        #         best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, idx_p, idx_d,
        #                                                                best_schedule, min_cost, feasible_schedules)
        #         if viol > 0:
        #             break
        #     continue
        # # same destination only
        # if idx_same_pick == -1 and idx_same_drop != -1:
        #     idx_d = idx_same_drop
        #     # insert the req's pick-up point
        #     for idx_p in range(idx_d):
        #         if idx_p < ealist_pick_up_point:
        #             continue
        #         best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, idx_p, idx_d,
        #                                                                best_schedule, min_cost, feasible_schedules)
        #         if viol == 3:
        #             break
        #     continue
        # # none is same
        # if idx_same_pick == -1 and idx_same_drop == -1:
        #     # insert the req's pick-up point
        #     for i in range(l + 1):
        #         if i < ealist_pick_up_point:
        #             continue
        #         # insert the req's drop-off point
        #         for j in range(i + 1, l + 2):
        #             if j < ealist_drop_off_point:
        #                 continue
        #             best_schedule, min_cost, viol = insert_req_to_schedule(veh, trip, schedule, req, i, j,
        #                                                                   best_schedule, min_cost, feasible_schedules)
        #             if viol > 0:
        #                 break
        #         if viol == 3:
        #             break
        #     continue
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

    # debug code starts
    ctt = time.time() - aa

    if ctt > 2:
        print()
        print()
        print('veh', veh.id, ', trip', [r.id for r in trip], ', trip size', len(trip), ', time:', ctt)
        print('num of subsche:', len(_schedules))
        # for sche in _schedules:
        #     print('sub-schedule', [(leg[0], leg[1], leg[2], leg[3]) for leg in sche])
        if best_schedule:
            print('best_schedule', ' sche len:', len(best_schedule), ', num of sche:', len(feasible_schedules), ', min_cost:', min_cost)
        # if len(feasible_schedules) > len(_schedules):
        #     for sche in feasible_schedules:
        #         print('new-schedule', [(leg[0], leg[1], leg[2], leg[3]) for leg in sche])
    # debug code ends

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

