"""
compute all feasible veh-trip combinations for the vehicle fleet and requests in pool (queue + picking)
"""

import copy
import time
import numpy as np
from tqdm import tqdm
from joblib import Parallel, delayed

from lib.Configure import RIDESHARING_SIZE, CUTOFF_RTV
from lib.Route import get_duration
from lib.ScheduleFinder import compute_schedule, test_constraints_get_cost, compute_schedule_cost


# build VT table for each veh(replan), respectively
def build_vt_table_replan(vehs, reqs_new, reqs_old, T):
    veh_trip_edges = []

    # non-parallel
    for veh in tqdm(vehs, desc='VT Table (replan)'):
        trip_list, schedule_list, cost_list = feasible_trips_search(veh, reqs_new, reqs_old, T)
        for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
            for trip, schedule, cost in zip(trips, schedules, costs):
                veh_trip_edges.append((veh, trip, schedule, cost))
        # print('veh %d is finished' % veh.id)

    return veh_trip_edges


# search all feasible trips for a single vehicle, incrementally from the trip size of one
# a time consuming step
def feasible_trips_search(veh, reqs_new, reqs_old, T):
    start_time = time.time()

    trip_list = [[]]  # all feasible trips of size 1, (2, 3...)
    schedule_list = [[]]  # best schedules for trips of size 1, (2, 3...)
    cost_list = [[]]  # min cost for trips of size 1, (2, 3...)
    schedules_k = []  # all feasible schedules for trips of size k
    l_old_trips_k = 0  # number of old trips of size k

    # debug code
    time1 = time.time()

    # trips of size 1
    # add old trips
    rid_old = {req.id for req in reqs_old}
    old_trip_list, old_schedule_list, old_cost_list, old_schedules_k = get_old_trips(veh, rid_old, k=1)
    trip_list[0].extend(old_trip_list)
    schedule_list[0].extend(old_schedule_list)
    cost_list[0].extend(old_cost_list)
    schedules_k.extend(old_schedules_k)
    l_old_trips_k = len(trip_list[0])

    # add new trips
    _schedule = []
    if not veh.idle:
        for leg in veh.route:
            if leg.rid in veh.onboard_rid:
                _schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.tnid, leg.ddl))
    for req in reqs_new:
        # filter the req which can not be served even when the veh is idle
        dt = get_duration(veh.lng, veh.lat, req.olng, req.olat, veh.nid, req.onid)
        if dt is None:  # no available route is found
            continue
        if dt + T <= req.Clp:
            trip = tuple([req])  # trip is defined as tuple
            best_schedule, min_cost, schedules = compute_schedule(veh, trip, [], [_schedule])
            if best_schedule:
                trip_list[0].append(trip)
                schedule_list[0].append(best_schedule)
                cost_list[0].append(min_cost)
                schedules_k.append(schedules)

                # debug code
                assert {req.id for req in trip} < {req.id for req in reqs_new}

                # if veh.id == 3 or veh.id == 4:
                #     print('veh', veh.id, ': size 1 add', req.id, 'schedules_num', len(schedules))

    # print('veh', veh.id, ', trip size:', 1, ', num of trips:', len(trip_list[0]),
    #       ', running time:', round((time.time() - time1), 2))

    veh.VTtable[0] = [(trip, schedules) for trip, schedules in zip(trip_list[0], schedules_k)]

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE+1):

        # debug code
        time2 = time.time()

        trip_list.append([])  # feasible trips of size k
        schedule_list.append([])  # best schedules for trips of size k
        cost_list.append([])  # min cost for trips of size k
        schedules_k_1 = copy.deepcopy(schedules_k)  # all feasible schedules for trips of size k-1
        schedules_k.clear()  # all feasible schedules for trips of size k
        l_old_trips_k_1 = l_old_trips_k  # number of old trips of size k-1
        l_old_trips_k = 0  # number of old trips of size k

        # add old trips
        old_trip_list, old_schedule_list, old_cost_list, old_schedules_k = get_old_trips(veh, rid_old, k)
        trip_list[k-1].extend(old_trip_list)
        schedule_list[k-1].extend(old_schedule_list)
        cost_list[k-1].extend(old_cost_list)
        schedules_k.extend(old_schedules_k)
        l_old_trips_k = len(trip_list[k-1])

        # add new trips
        l = len(trip_list[k-2])  # number of trips of size k-1
        l_new_trips_k_1 = l - l_old_trips_k_1  # number of new trips of size k-1
        for i in range(1, l_new_trips_k_1+1):
            trip1 = trip_list[k-2][-i]  # a new trip of size k-1
            for j in range(i+1, l+1):
                trip2 = trip_list[k-2][-j]  # another trip of size k-1
                trip_k = tuple(sorted(set(trip1).union(set(trip2)), key=lambda r: r.id))
                if k > 2:
                    # check trip size is k
                    if len(trip_k) != k:
                        continue
                    # check trip is already computed
                    if trip_k in trip_list[k - 1]:
                        continue
                    # check all subtrips are feasible
                    subtrips_check = True
                    for req in trip_k:
                        if tuple(sorted((set(trip_k) - set([req])), key=lambda r: r.id)) not in trip_list[k - 2]:
                            subtrips_check = False
                            break
                    if not subtrips_check:
                        continue
                if len(schedules_k_1[-i]) <= len(schedules_k_1[-j]):
                    _trip = trip1  # subtrip of trip_k
                    _schedules = schedules_k_1[-i]  # all feasible schedules for trip1 of size k-1
                else:
                    _trip = trip2
                    _schedules = schedules_k_1[-j]

                # # debug code starts
                # if veh.id == 3:
                #     print('veh', veh.id, ': size', k, 'test', [req.id for req in trip_k])
                # # debug code ends

                best_schedule, min_cost, schedules = compute_schedule(veh, trip_k, _trip, _schedules)
                if best_schedule:
                    trip_list[k-1].append(trip_k)
                    schedule_list[k-1].append(best_schedule)
                    cost_list[k-1].append(min_cost)
                    schedules_k.append(schedules)

                    # debug code
                    assert {req.id for req in trip_k} < {req.id for req in set(reqs_new).union(reqs_old)}

                    # # debug code starts
                    # print('veh', veh.id, ': size', k, 'add', [req.id for req in trip_k],
                    #       'schedules_num', len(schedules))
                    # # debug code ends

                # if time.time() - start_time > CUTOFF_RTV:
                #     # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k - 1]), '(time out)')
                #     return trip_list, schedule_list, cost_list

        veh.VTtable[k-1] = [(trip, schedules) for trip, schedules in zip(trip_list[k-1], schedules_k)]

        # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k - 1]),
        #       ', running time:', round((time.time() - time2), 2))

        if len(trip_list[k-1]) == 0:
            trip_list.pop()
            schedule_list.pop()
            cost_list.pop()
            for k1 in range(k, RIDESHARING_SIZE+1):
                veh.VTtable[k1] = []
            break

    return trip_list, schedule_list, cost_list


def get_old_trips(veh, rid_old, k):

    # debug
    veh_id = 3
    # if veh.id == veh_id and len(veh.route) != 0:
    #     print('new start           veh', veh.id, ' has route, new pick:', veh.new_pick_rid, ', new drop:', veh.new_drop_rid)
    #     print([(leg.rid, leg.pod) for leg in veh.route], veh.onboard_rid)
    #     print('trip size', k)
    #     print('veh.VTtable[0]', len(veh.VTtable[0]))
    #     print('veh.VTtable[1]', len(veh.VTtable[1]))
    #     print('veh.VTtable[2]', len(veh.VTtable[2]))
    #     print('veh.VTtable[3]', len(veh.VTtable[3]))

    old_trip_list = []
    old_schedule_list = []
    old_cost_list = []
    old_schedules_k = []

    new_pick_rid = set(veh.new_pick_rid)
    new_drop_rid = set(veh.new_drop_rid)
    new_both_rid = new_pick_rid.union(new_drop_rid)
    l_new_pick = len(veh.new_pick_rid)
    l_new_drop = len(veh.new_drop_rid)
    l_new_both = l_new_pick + l_new_drop
    assert l_new_both == len(new_both_rid)
    k = k + l_new_pick

    if l_new_pick == 0:
        trip_id_sub = set()
        trip_id_sup = rid_old
    else:
        trip_id_sub = new_pick_rid
        trip_id_sup = rid_old.union(new_pick_rid)
        assert len(trip_id_sup) - len(rid_old) == l_new_pick

    veh_route = [(leg.rid, leg.pod) for leg in veh.route]
    veh_rid_enroute = {leg.rid for leg in veh.route}
    for trip, schedules in veh.VTtable[k - 1]:
        trip_id = {req.id for req in trip}

        # # debug
        # if veh.id == veh_id and len(veh.route) != 0:
        #     print('trip size', k, ', trip_id', trip_id, ', schedules', len(schedules))

        if trip_id_sub < trip_id < trip_id_sup:
            best_schedule = None
            min_cost = np.inf
            feasible_schedules = []
            if l_new_pick != 0:
                # remove picked req in trip
                trip_ = list(trip)
                for req in trip:
                    if req.id in new_pick_rid:
                        trip_.remove(req)
                trip_ = tuple(sorted(trip_, key=lambda r: r.id))
            else:
                trip_ = trip
            for schedule in schedules:

                # # debug
                # if veh.id == veh_id and len(veh.route) != 0:
                #     print('sche', [(rid, pod) for (rid, pod, tlng, tlat, tnid, ddl) in schedule])

                if l_new_both != 0:
                    if {schedule[i][0] for i in range(l_new_both)} != new_both_rid:
                        continue
                    else:
                        assert sum([schedule[i][1] for i in range(l_new_both)]) == l_new_pick - 1 * l_new_drop
                        del schedule[0:l_new_both]

                # # codes to fix bugs that caused by using travel time table (starts)
                # # (the same schedule (which is feasible) might not be feasible after veh moves along that schedule,
                # #     if travel times are computed from travel time table (which is not accurate))
                # trip_id_ = {req.id for req in trip_}
                # trip_sche_ = [(rid, pod) for (rid, pod, tlng, tlat, tnid, ddl) in schedule]
                # if trip_sche_ == veh_route:
                #     flag = True
                #     c = compute_schedule_cost(veh, trip_, schedule)
                #
                #     # # debug
                #     # if veh.id == veh_id:
                #     #     print('veh', veh.id, ' add route (same as route)')
                #
                # elif trip_id_ < veh_rid_enroute:
                #     veh_partial_route = []
                #     for (rid, pod) in veh_route:
                #         if rid in trip_id_.union(set(veh.onboard_rid)):
                #             veh_partial_route.append((rid, pod))
                #
                #     # # debug
                #     # if veh.id == veh_id:
                #     #     print('trip_sche_', trip_sche_)
                #     #     print('veh_partial_route', veh_partial_route)
                #
                #     if trip_sche_ == veh_partial_route:
                #         flag = True
                #         c = compute_schedule_cost(veh, trip_, schedule)
                #
                #         # # debug
                #         # if veh.id == veh_id:
                #         #     print('veh', veh.id, ' add route (partial route)')
                #
                #     else:
                #         flag, c, viol = test_constraints_get_cost(veh, trip_, schedule, trip_[0], 0)
                #
                #         # # debug
                #         # if veh.id == veh_id:
                #         #     print('veh', veh.id, ' go to test (partial route)')
                # else:
                #     flag, c, viol = test_constraints_get_cost(veh, trip_, schedule, trip_[0], 0)
                # # codes to fix bugs that caused by using travel time table (ends)

                flag, c, viol = test_constraints_get_cost(veh, trip_, schedule, trip_[0], 0)
                if flag:

                    # # debug
                    # if veh.id == veh_id:
                    #     print('veh', veh.id, ' add route, cost:', c)

                    feasible_schedules.append(copy.deepcopy(schedule))
                    if c < min_cost:
                        best_schedule = copy.deepcopy(schedule)
                        min_cost = c
            if len(feasible_schedules) > 0:
                old_trip_list.append(trip_)
                old_schedule_list.append(best_schedule)
                old_cost_list.append(min_cost)
                old_schedules_k.append(feasible_schedules)
                assert {req.id for req in trip_} < rid_old

    assert len(old_trip_list) == len(set(old_trip_list))

    # # debug
    # if veh.id == veh_id:
    #     print('old_trip_list', len(old_trip_list))

    return old_trip_list, old_schedule_list, old_cost_list, old_schedules_k
