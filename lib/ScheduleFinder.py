"""
compute all feasible schedules for given vehicle v and trip T.
"""

import copy
import time
import numpy as np
from lib.Configure import COEF_WAIT, COEF_INVEH
from lib.Route import get_duration, get_duration_from_osrm


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh, trip, _trip, _schedules):
    best_schedule = None
    min_cost = np.inf
    feasible_schedules = []
    ealist_pick_up_point = 0
    ealist_drop_off_point = 0
    viol = None

    req = tuple(set(trip) - set(_trip))[0]

    for schedule in _schedules:
        # # check if the req has same origin-destination as any other req in the schedule
        # p = set()
        # d = set()
        # for (rid, pod, tlng, tlat, tnid, ddl) in schedule:
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
        #     for (rid, pod, tlng, tlat, tnid, ddl) in schedule:
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
        #     schedule.insert(i_p, (req.id, 1, req.olng, req.olat, req.onid, req.Clp))
        #     schedule.insert(i_d, (req.id, -1, req.dlng, req.dlat, req.dnid, req.Cld))
        #     flag, c, viol = test_constraints_get_cost(schedule, veh, req, i_d)
        #     if flag:
        #         feasible_schedules.append(copy.deepcopy(schedule))
        #         best_schedule = copy.deepcopy(schedule)
        #         min_cost = c
        #     schedule.pop(i_d)
        #     schedule.pop(i_p)
        #     return best_schedule, min_cost, feasible_schedules

        l = len(schedule)
        # if the direct pick-up of req is longer than the time constrain of a req already in the schedule,
        # it cannot be picked-up before that req.
        dt = get_duration(veh.lng, veh.lat, req.olng, req.olat, veh.nid, req.onid)
        for i in reversed(range(l)):
            if veh.T + dt > schedule[i][5]:
                ealist_pick_up_point = i + 1
                break
        # if the shortest travel time of req is longer than the time constrain of a leg in the schedule,
        # it cannot be dropped-off before that leg.
        for i in reversed(range(l)):
            if veh.T + req.Ts > schedule[i][5]:
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
                schedule.insert(i, (req.id, 1, req.olng, req.olat, req.onid, req.Clp))
                schedule.insert(j, (req.id, -1, req.dlng, req.dlat, req.dnid, req.Cld))
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

    # # calibrate the min_cost to osrm result, instead using the travel time table
    # if best_schedule is not None:
    #     min_cost = compute_schedule_cost(best_schedule, veh)
    return best_schedule, min_cost, feasible_schedules


# test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no)
def test_constraints_get_cost(veh, trip, schedule, req, drop_point):
    c_delay = 0.0
    c_wait = 0.0
    c_inveh = 0.0
    t = 0.0
    n = veh.n
    T = veh.T
    K = veh.K
    lng = veh.lng
    lat = veh.lat
    nid = veh.nid
    req_id = req.id

    # test the capacity constraint during the whole schedule
    for (rid, pod, tlng, tlat, tnid, ddl) in schedule:
        n += pod
        if n > K:
            return False, None, 1  # over capacity
    n = veh.n

    # test the pick-up and drop-off time constraint for each passenger on board
    idx = 0
    for (rid, pod, tlng, tlat, tnid, ddl) in schedule:
        idx += 1
        dt = get_duration(lng, lat, tlng, tlat, nid, tnid)
        if dt is None:
            return False, None, 1  # no route found between points
        t += dt
        if T + t > ddl:
            if rid == req_id:
                # pod == -1 means a new pick-up insertion is needed, since later drop-off brings longer travel time
                # pod == 1 means no more feasible schedules is available, since later pick-up brings longer wait time
                return False, None, 2 if pod == -1 else 3
            if idx <= drop_point:
                # idx<=drop_point means the violation is caused by the pick-up of req,
                # since the violation happens before the drop-off of req
                return False, None, 4
            return False, None, 0
        c_inveh += n * dt * COEF_INVEH
        n += pod
        assert n <= veh.K
        c_wait += t * COEF_WAIT if pod == 1 else 0
        if pod == -1:
            for req in trip:
                if rid == req.id:
                    c_delay += round(T + t - (req.Tr + req.Tp + req.Ts_VT))
                    if round(T + t - (req.Tr + req.Tp + req.Ts_VT)) < 0:
                        c_delay += -round(T + t - (req.Tr + req.Tp + req.Ts_VT))
        lng = tlng
        lat = tlat
        nid = tnid

    return True, c_wait+c_delay, -1
    # return True, round(t*8/c_inveh), -1
    # return True, c_wait+c_inveh, -1
    # return True, c_wait, -1


# compute the schedule cost using osrm
def compute_schedule_cost(veh, trip, schedule):
    c_delay = 0.0
    c_wait = 0.0
    c_inveh = 0.0
    t = 0.0
    n = veh.n
    T = veh.T
    lng = veh.lng
    lat = veh.lat
    for (rid, pod, tlng, tlat, tnid, ddl) in schedule:
        dt = get_duration_from_osrm(lng, lat, tlng, tlat)
        t += dt
        c_inveh += n * dt * COEF_INVEH
        n += pod
        c_wait += t * COEF_WAIT if pod == 1 else 0
        if pod == -1:
            for req in trip:
                if rid == req.id:
                    c_delay += round(T + t - (req.Tr + req.Tp + req.Ts_VT))
                    if round(T + t - (req.Tr + req.Tp + req.Ts_VT)) < 0:
                        c_delay += -round(T + t - (req.Tr + req.Tp + req.Ts_VT))
        c_wait += t * COEF_WAIT if pod == 1 else 0
        lng = tlng
        lat = tlat
    return c_wait+c_delay
