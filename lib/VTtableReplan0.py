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
    reqs_pool = reqs_old + reqs_new

    trip_list = [[]]  # all feasible trips of size 1, (2, 3...)
    schedule_list = [[]]  # best schedules for trips of size 1, (2, 3...)
    cost_list = [[]]  # min cost for trips of size 1, (2, 3...)
    schedules_k = []  # all feasible schedules for trips of size k

    # debug code
    time1 = time.time()

    # trips of size 1
    # add new trips
    _schedule = []
    if not veh.idle:
        for leg in veh.route:
            if leg.rid in veh.onboard_rid:
                _schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.tnid, leg.ddl))
    for req in reqs_pool:
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
                assert {req.id for req in trip} < {req.id for req in reqs_pool}

                # if veh.id == 3 or veh.id == 4:
                #     print('veh', veh.id, ': size 1 add', req.id, 'schedules_num', len(schedules))

    # print('veh', veh.id, ', trip size:', 1, ', num of trips:', len(trip_list[0]),
    #       ', running time:', round((time.time() - time1), 2))

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE+1):

        # debug code
        time2 = time.time()

        trip_list.append([])  # feasible trips of size k
        schedule_list.append([])  # best schedules for trips of size k
        cost_list.append([])  # min cost for trips of size k
        schedules_k_1 = copy.deepcopy(schedules_k)  # all feasible schedules for trips of size k-1
        schedules_k.clear()  # all feasible schedules for trips of size k

        # add new trips

        l = len(trip_list[k - 2])  # number of trips of size k-1
        for i in range(l - 1):
            trip1 = trip_list[k - 2][i]  # a trip of size k-1
            for j in range(i + 1, l):
                trip2 = trip_list[k - 2][j]  # another trip of size k-1
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
                if len(schedules_k_1[i]) <= len(schedules_k_1[j]):
                    _trip = trip1  # subtrip of trip_k
                    _schedules = schedules_k_1[i]  # all feasible schedules for trip1 of size k-1
                else:
                    _trip = trip2
                    _schedules = schedules_k_1[j]

                # # debug code starts
                # print('veh', veh.id, ': size', k, 'test', [req.id for req in trip_k])
                # # debug code ends

                best_schedule, min_cost, schedules = compute_schedule(veh, trip_k, _trip, _schedules)
                if best_schedule:
                    trip_list[k-1].append(trip_k)
                    schedule_list[k-1].append(best_schedule)
                    cost_list[k-1].append(min_cost)
                    schedules_k.append(schedules)

                    # debug code
                    assert {req.id for req in trip_k} < {req.id for req in reqs_pool}

                    # # debug code starts
                    # print('veh', veh.id, ': size', k, 'add', [req.id for req in trip_k],
                    #       'schedules_num', len(schedules))
                    # # debug code ends

                # if time.time() - start_time > CUTOFF_RTV:
                #     # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k - 1]), '(time out)')
                #     return trip_list, schedule_list, cost_list

        # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k - 1]),
        #       ', running time:', round((time.time() - time2), 2))

        if len(trip_list[k-1]) == 0:
            trip_list.pop()
            schedule_list.pop()
            cost_list.pop()
            break

    return trip_list, schedule_list, cost_list

