"""
compute all feasible veh-trip combinations for the vehicle fleet and requests in queue
"""

import copy
import time
from tqdm import tqdm
from joblib import Parallel, delayed

from lib.Configure import RIDESHARING_SIZE, CUTOFF_RTV
from lib.ScheduleFinder import compute_schedule
from lib.Route import get_duration


# build VT table for each veh, respectively
def build_vt_table(vehs, reqs_pool, T):
    veh_trip_edges = []

    # # parallel
    # trip_list_all = Parallel(n_jobs=-1)(delayed(feasible_trips_search)(veh, reqs_pool, T)
    #                                     for veh in vehs)
    #
    # for veh, (trip_list, schedule_list, cost_list) in zip(vehs, trip_list_all):
    #     for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
    #         for trip, schedule, cost in zip(trips, schedules, costs):
    #             veh_trip_edges.append([veh, trip, schedule, cost])

    # non-parallel
    for veh in tqdm(vehs, desc='VT Table'):
        trip_list, schedule_list, cost_list = feasible_trips_search(veh, reqs_pool, T)
        for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
            for trip, schedule, cost in zip(trips, schedules, costs):
                veh_trip_edges.append((veh, trip, schedule, cost))
        # print('veh %d is finished' % veh.id)

    # # debug code starts
    # for veh in model.vehs:
    #     trip_list, schedule_list, cost_list = feasible_trips_search(veh, reqs_pool, T)
    #     l = len(trip_list)
    #     print('max trip size is', l)
    #     for i in range(l):
    #         l_1 = len(trip_list[i])
    #         print(' number of trip size', i+1, 'is', l_1)
    #         for j in range(l_1):
    #             reqid = []
    #             for req in trip_list[i][j]:
    #                 reqid.append(req.id)
    #             legid = []
    #             for leg in schedule_list[i][j]:
    #                 legid.append([leg[0], leg[1]])
    #             print('  trip:', reqid, ', schedule:', legid, ', cost:', cost_list[i][j])
    # # debug code ends

    # # debug code starts
    # for (veh, trip, schedule, cost) in veh_trip_edges:
    #     print('veh %d, trip %s, cost %.02f' % (veh.id, [r.id for r in trip], cost))
    # # debug code ends

    return veh_trip_edges


# search all feasible trips for a single vehicle, incrementally from the trip size of one
# a time consuming step
def feasible_trips_search(veh, reqs, T):
    start_time = time.time()
    trip_list = [[]]  # all feasible trips of size 1, (2, 3...)
    schedule_list = [[]]  # best schedules for trips of size 1, (2, 3...)
    cost_list = [[]]  # min cost for trips of size 1, (2, 3...)
    schedules_k = []  # all feasible schedules for trips of size k

    # debug code
    time1 = time.time()

    # trips of size 1
    _schedule = []
    if not veh.idle:
        for leg in veh.route:
            _schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.tnid, leg.ddl))
    for req in reqs:
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

                # if veh.id == 3 or veh.id == 4:
                #     print('veh', veh.id, ': size 1 add', req.id, 'schedules_num', len(schedules))

    # print('veh', veh.id, ', trip size:', 1, ', num of trips:', len(trip_list[0]),
    #       ', running time:', round((time.time() - time1), 2))

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE + 1):

        # debug code
        time2 = time.time()

        trip_list.append([])  # feasible trips of size k
        schedule_list.append([])  # best schedules for trips of size k
        cost_list.append([])  # min cost for trips of size k
        schedules_k_1 = copy.deepcopy(schedules_k)  # all feasible schedules for trips of size k-1
        schedules_k.clear()  # all feasible schedules for trips of size k

        # # debug code starts
        # # different reqs with same origin-destination will bring many duplicate schedules
        # sch_num = []
        # for s in schedules_k_1:
        #     sch_num.append(len(s))
        #     if len(s) >= 4:
        #         scc = []
        #         for sub_s in s:
        #             reqid = []
        #             for (rid, pod, tlng, tlat, ddl) in sub_s:
        #                 reqid.append([rid, pod])
        #             print('schedule:', reqid)
        #         for (rid, pod, tlng, tlat, ddl) in s[0]:
        #                 scc.append([rid, pod, tlng, tlat, ddl])
        #         print('schedule num:', len(s), ', is', scc)
        # print('veh:', veh.id, ', trip size:', k-1, ', schedules:', sch_num)
        # # debug code ends

        # debug code
        n1 = 0
        n2 = 0
        n3 = 0

        l = len(trip_list[k - 2])  # number of trips of size k-1
        for i in range(l - 1):
            trip1 = trip_list[k - 2][i]  # a trip of size k-1
            for j in range(i + 1, l):
                trip2 = trip_list[k - 2][j]  # another trip of size k-1
                trip_k = tuple(sorted(set(trip1).union(set(trip2)), key=lambda r: r.id))

                # debug code
                n1 += 1

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

                # debug code
                n2 += 1

                best_schedule, min_cost, schedules = compute_schedule(veh, trip_k, _trip, _schedules)
                if best_schedule:
                    trip_list[k - 1].append(trip_k)
                    schedule_list[k-1].append(best_schedule)
                    cost_list[k-1].append(min_cost)
                    schedules_k.append(schedules)

                    # # debug code starts
                    # print('veh', veh.id, ': size', k, 'add', [req.id for req in trip_k],
                    #       'schedules_num', len(schedules))
                    # # debug code ends

                    # debug code
                    n3 += 1

                if time.time() - start_time > CUTOFF_RTV:
                    # # debug code starts
                    # print('   number of trip size', k - 1, 'is', len(trip_list[k - 2]))
                    # print('   number of trip size', k, 'in test1 is', n1)
                    # print('   number of trip size', k, 'in test2 is', n2)
                    # print('   number of trip size', k, 'pass test is', n3)
                    # # debug code ends
                    # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k - 1]), '(time out)')
                    return trip_list, schedule_list, cost_list
        # # debug code starts
        # print('   number of trip size', k-1, 'is', l)
        # print('   number of trip size', k, 'in test1 is', n1)
        # print('   number of trip size', k, 'in test2 is', n2)
        # print('   number of trip size', k, 'pass test is', n3)
        # # debug code ends
        # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k-1]),
        #       ', running time:', round((time.time() - time2), 2))

        if len(trip_list[k-1]) == 0:
            trip_list.pop()
            schedule_list.pop()
            cost_list.pop()
            break

    return trip_list, schedule_list, cost_list


