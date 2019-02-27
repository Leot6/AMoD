"""
A first-in-first-out insertion fleet assignment algorithm for the AMoD system
"""

import copy
import time

from lib.Vehicle import *


# insertion heuristics
def insertion_heuristics(model, osrm, T):
    l = len(model.queue)
    for i in range(l):
        req = model.queue[i]
        if not insert_heuristics(model, osrm, req, T):
            model.rejs.append(req)
        else:
            model.reqs_picking.add(req)
            model.queue_[i].served = True
    model.queue.clear()


# insert a request using the insertion heuristics method
def insert_heuristics(model, osrm, req, T):
    CUTOFF = 0.5
    start_time = time.time()
    ealist_drop_off_point = 0
    dc_ = np.inf
    veh_ = None
    schedule_ = None
    viol = None
    for veh in model.vehs:
        # filter the veh which can not serve the req even it is idle
        if osrm.get_duration(veh.lng, veh.lat, req.olng, req.olat) + T <= req.Clp:
            schedule = []
            if not veh.idle:
                for leg in veh.route:
                    schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.ddl))
            else:
                assert veh.c == 0
            l = len(schedule)

            # if the shortest travel time of req is longer than the time constrain of a req already in the schedule,
            # it cannot be dropped-off before that req.
            for i in range(l):
                if veh.T + req.Ts > schedule[i][4]:
                    ealist_drop_off_point = i + 2
                    break

            c = veh.c
            # insert the req's pick-up point
            for i in range(l + 1):
                # insert the req's dropoff point
                for j in range(i + 1, l + 2):
                    schedule.insert(i, (req.id, 1, req.olng, req.olat, req.Clp))
                    schedule.insert(j, (req.id, -1, req.dlng, req.dlat, req.Cld))
                    flag, c_, viol = test_constraints_get_cost(osrm, schedule, veh, req, c + dc_, j)
                    if flag:
                        dc_ = c_ - c
                        veh_ = veh
                        schedule_ = copy.deepcopy(schedule)
                    schedule.pop(j)
                    schedule.pop(i)
                    if viol > 0:
                        break
                if viol == 3:
                    break
                if time.time() - start_time > CUTOFF:
                    return False
    if veh_ != None:
        veh_.build_route(osrm, schedule_, model.reqs, T)
        print("    Insertion Heuristics: req %d is assigned to veh %d" % (req.id, veh_.id))
        return True
    else:
        # print("    Insertion Heuristics: req %d is rejected!" % (req.id))
        return False


# test if a schedule can satisfy all constraints, and if yes, return the cost of the schedule
def test_constraints_get_cost(osrm, schedule, veh, req, C, drop_point):
    c = 0.0
    t = 0.0
    n = veh.n
    T = veh.T
    K = veh.K
    lng = veh.lng
    lat = veh.lat

    # test the capacity constraint during the whole schedule
    for (rid, pod, tlng, tlat, ddl) in schedule:
        n += pod
        if n > K:
            return False, None, 1  # over capacity
    n = veh.n

    # test the pick-up and drop-off time constraint for each passenger on board
    k = 0
    for (rid, pod, tlng, tlat, ddl) in schedule:
        k += 1
        dt = osrm.get_duration(lng, lat, tlng, tlat)
        t += dt
        if T + t > ddl:
            if rid == req.id:
                # pod == -1 means a new pick-up insertion is needed, for later drop-off brings longer travel time
                # pod == 1 means a new schedule is needed, for later pick-up brings longer wait time
                return False, None, 2 if pod == -1 else 3
            if k <= drop_point:
                # k<=drop_point means the violation is caused by the pick-up of req,
                # for the violation happens before the drop-off of req
                return False, None, 4
            return False, None, 0
        c += n * dt * COEF_INVEH
        n += pod
        assert n <= veh.K
        c += t * COEF_WAIT if pod == 1 else 0
        if c > C:
            return False, None, 0
        lng = tlng
        lat = tlat
    return True, c, -1
