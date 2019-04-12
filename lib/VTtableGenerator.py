"""
compute all feasible veh-trip combinations for the vehicle fleet and requests
"""

import copy
import time
import numpy as np
from tqdm import tqdm
from joblib import Parallel, delayed

from lib.Configure import RIDESHARING_SIZE, CUTOFF_RTV
from lib.Route import get_duration
from lib.ScheduleFinder import compute_schedule, test_constraints_get_cost


# build VT table for each veh, respectively
def build_vt_table(vehs, reqs_new, reqs_old, T):
    print('    -building VT-table...')
    veh_trip_edges = []

    # non-parallel
    for veh in tqdm(vehs, desc='VT Table'):
        trip_list, schedule_list, cost_list = feasible_trips_search(veh, reqs_new, reqs_old, T)
        for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
            for trip, schedule, cost in zip(trips, schedules, costs):
                veh_trip_edges.append([veh, trip, schedule, cost])
        # print('veh %d is finished' % veh.id)

    return veh_trip_edges


# search all feasible trips for a single vehicle, incrementally from the trip size of one
# a time consuming step
def feasible_trips_search(veh, reqs_new, reqs_old, T):
    start_time = time.time()

    rid_old = {req.id for req in reqs_old}

    trip_list = [[]]  # all feasible trips of size 1, (2, 3...)
    schedule_list = [[]]  # best schedules for trips of size 1, (2, 3...)
    cost_list = [[]]  # min cost for trips of size 1, (2, 3...)
    schedules_k = []  # all feasible schedules for trips of size k
    l_old_trips_k = 0  # number of old trips of size k

    # trips of size 1
    # add old trips
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
            if leg.rid in veh.rid_onboard:
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

                # print('veh', veh.id, ': size 1 add', req.id, 'schedules_num', len(schedules))
    # print('veh', veh.id, ', trip size:', 1, ', num of trips:', len(trip_list[0]),
    #       ', running time:', round((time.time() - time1), 2))

    veh.VTtable[0] = [(trips, schedules) for trips, schedules in zip(trip_list[0], schedules_k)]

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE+1):

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

                best_schedule, min_cost, schedules = compute_schedule(veh, trip_k, _trip, _schedules)
                if best_schedule:
                    trip_list[k-1].append(trip_k)
                    schedule_list[k-1].append(best_schedule)
                    cost_list[k-1].append(min_cost)
                    schedules_k.append(schedules)
                    # print('veh', veh.id, ': size', k, 'add', [req.id for req in trip_k], 'schedules_num', len(schedules))

                if time.time() - start_time > CUTOFF_RTV:
                    # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k - 1]), '(time out)')
                    return trip_list, schedule_list, cost_list

        veh.VTtable[k-1] = [(trips, schedules) for trips, schedules in zip(trip_list[k-1], schedules_k)]

        if len(trip_list[k-1]) == 0:
            trip_list.pop()
            schedule_list.pop()
            cost_list.pop()
            for k1 in range(k, RIDESHARING_SIZE+1):
                veh.VTtable[k1] = []
            break

    return trip_list, schedule_list, cost_list


def get_old_trips(veh, rid_old, k):
    old_trip_list = []
    old_schedule_list = []
    old_cost_list = []
    old_schedules_k = []

    new_pick_rid = veh.new_pick_rid
    new_drop_rid = veh.new_drop_rid
    l_new_pick = len(veh.new_pick_rid)
    l_new_drop = len(veh.new_drop_rid)
    l_new_both = l_new_pick + l_new_drop
    k = k + l_new_pick

    if l_new_pick == 0 and l_new_drop == 0:
        for trip, schedules in veh.VTtable[k-1]:
            trip_id = {req.id for req in trip}
            if trip_id < rid_old:
                best_schedule = None
                min_cost = np.inf
                feasible_schedules = []
                for schedule in schedules:
                    flag, c, viol = test_constraints_get_cost(schedule, veh, trip[0], 0)
                    if flag:
                        feasible_schedules.append(copy.deepcopy(schedule))
                        if c < min_cost:
                            best_schedule = copy.deepcopy(schedule)
                            min_cost = c

                            # debug code starts
                            if sum([pod for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]) != -veh.n \
                                    or sum([leg.pod for leg in veh.route]) != -veh.n:
                            # if veh.id == 140:
                                schedule1 = [(leg.rid, leg.pod) for leg in veh.route]
                                schedule2 = [(rid, pod) for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]
                                print()
                                print('debug 1, veh', veh.id, ', passengers', veh.n)
                                print('route record', veh.route_record)
                                print('route to go', schedule1)
                                print('rid on board', veh.rid_onboard, ', new pick', veh.new_pick_rid, ', new drop',
                                      veh.new_drop_rid)
                                print('trip_id', trip_id)
                                print('schedule', schedule2)
                                sches = []
                                for sch in schedules:
                                    sches.append([(rid, pod) for (rid, pod, tlng, tlat, tnid, ddl) in sch])
                                print('schedules', sches)
                                print()
                            # debug code ends

                            # debug code starts
                            assert sum([leg.pod for leg in veh.route]) == -veh.n
                            assert sum([pod for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]) == -veh.n
                            # debug code ends

                if len(feasible_schedules) > 0:
                    old_trip_list.append(trip)
                    old_schedule_list.append(best_schedule)
                    old_cost_list.append(min_cost)
                    old_schedules_k.append(feasible_schedules)
                    # print('veh', veh.id, ': size', k, 're-add', [req.id for req in trip], 'schedules_num',
                    #       len(feasible_schedules))

    if l_new_pick == 0 and l_new_drop != 0:
        for trip, schedules in veh.VTtable[k-1]:
            trip_id = {req.id for req in trip}
            if trip_id < rid_old:
                best_schedule = None
                min_cost = np.inf
                feasible_schedules = []
                for schedule in schedules:
                    if {schedule[i][0] for i in range(l_new_drop)} == set(new_drop_rid):
                        assert sum([schedule[i][1] for i in range(l_new_drop)]) == -1 * l_new_drop
                        del schedule[0:l_new_drop]
                        flag, c, viol = test_constraints_get_cost(schedule, veh, trip[0], 0)
                        if flag:
                            feasible_schedules.append(copy.deepcopy(schedule))
                            if c < min_cost:
                                best_schedule = copy.deepcopy(schedule)
                                min_cost = c

                                # debug code starts
                                assert sum([leg.pod for leg in veh.route]) == -veh.n
                                assert sum([pod for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]) == -veh.n
                                # debug code ends

                if len(feasible_schedules) > 0:
                    old_trip_list.append(trip)
                    old_schedule_list.append(best_schedule)
                    old_cost_list.append(min_cost)
                    old_schedules_k.append(feasible_schedules)
                    # print('veh', veh.id, ': size', k, 're-add', [req.id for req in trip], 'schedules_num',
                    #       len(feasible_schedules))

    if l_new_pick != 0 and l_new_drop == 0:
        for trip, schedules in veh.VTtable[k-1]:
            trip_id = {req.id for req in trip}
            if set(new_pick_rid) < trip_id:
                best_schedule = None
                min_cost = np.inf
                feasible_schedules = []
                # remove req in trip
                trip1 = list(trip)
                for req in trip1:
                    if req.id in new_pick_rid:
                        trip1.remove(req)
                trip1 = tuple(trip1)
                for schedule in schedules:
                    if {schedule[i][0] for i in range(l_new_pick)} == set(new_pick_rid):
                        assert sum([schedule[i][1] for i in range(l_new_pick)]) == l_new_pick
                        del schedule[0:l_new_pick]
                        flag, c, viol = test_constraints_get_cost(schedule, veh, trip[0], 0)
                        if flag:
                            feasible_schedules.append(copy.deepcopy(schedule))
                            if c < min_cost:
                                best_schedule = copy.deepcopy(schedule)
                                min_cost = c

                                # debug code starts
                                # if sum([pod for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]) != -veh.n \
                                #         or sum([leg.pod for leg in veh.route]) != -veh.n:
                                if veh.id == 140:
                                    schedule1 = [(leg.rid, leg.pod) for leg in veh.route]
                                    schedule2 = [(rid, pod) for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]
                                    print()
                                    print('debug 4, veh', veh.id, ', passengers', veh.n)
                                    print('route record', veh.route_record)
                                    print('route to go', schedule1)
                                    print('rid on board', veh.rid_onboard, ', new pick', veh.new_pick_rid, ', new drop',
                                          veh.new_drop_rid)
                                    print('trip_id', trip_id, ', trip1', {req.id for req in trip1})
                                    print('schedule', schedule2)
                                    sches = []
                                    for sch in schedules:
                                        sches.append([(rid, pod) for (rid, pod, tlng, tlat, tnid, ddl) in sch])
                                    print('schedules', sches)
                                    print()
                                # debug code ends

                                # debug code starts
                                assert sum([leg.pod for leg in veh.route]) == -veh.n
                                assert sum([pod for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]) == -veh.n
                                # debug code ends

                if len(feasible_schedules) > 0:
                    old_trip_list.append(trip1)
                    old_schedule_list.append(best_schedule)
                    old_cost_list.append(min_cost)
                    old_schedules_k.append(feasible_schedules)
                    # print('veh', veh.id, ': size', k, 're-add', [req.id for req in trip], 'schedules_num',
                    #       len(feasible_schedules))

    if l_new_pick != 0 and l_new_drop != 0:
        for trip, schedules in veh.VTtable[k-1]:
            trip_id = {req.id for req in trip}
            if set(new_pick_rid) < trip_id:
                best_schedule = None
                min_cost = np.inf
                feasible_schedules = []
                # remove req in trip
                trip1 = list(trip)
                for req in trip1:
                    if req.id in new_pick_rid:
                        trip1.remove(req)
                trip1 = tuple(trip1)
                for schedule in schedules:
                    if {schedule[i][0] for i in range(l_new_both)} == set(new_pick_rid).union(set(new_drop_rid)):
                        assert sum([schedule[i][1] for i in range(l_new_both)]) == l_new_pick - 1 * l_new_drop
                        del schedule[0:l_new_both]
                        flag, c, viol = test_constraints_get_cost(schedule, veh, trip[0], 0)
                        if flag:
                            feasible_schedules.append(copy.deepcopy(schedule))
                            if c < min_cost:
                                best_schedule = copy.deepcopy(schedule)
                                min_cost = c

                                # debug code starts
                                assert sum([leg.pod for leg in veh.route]) == -veh.n
                                assert sum([pod for (rid, pod, tlng, tlat, tnid, ddl) in best_schedule]) == -veh.n
                                # debug code ends

                    if len(feasible_schedules) > 0:
                        old_trip_list.append(trip1)
                        old_schedule_list.append(best_schedule)
                        old_cost_list.append(min_cost)
                        old_schedules_k.append(feasible_schedules)
                        # print('veh', veh.id, ': size', k, 're-add', [req.id for req in trip], 'schedules_num',
                        #       len(feasible_schedules))

    return old_trip_list, old_schedule_list, old_cost_list, old_schedules_k
