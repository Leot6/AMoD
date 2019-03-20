"""
dispatch algorithms for the AMoD system
"""

import copy
import time
from joblib import Parallel, delayed
from lib.Vehicle import *
from lib.Route import get_duration, get_duration_haversine


def greedy_assign(model, vehicle_trip_edges, T):
    print('    -start greedy assign with %d edges:' % len(vehicle_trip_edges))
    edges = sorted(vehicle_trip_edges, key=lambda e: (-len(e[1]), e[3]))
    R_id_assigned = set()
    T_id_assigned = set()
    V_id_assigned = set()
    V_id_assigned_list = []
    schedule_assigned = []

    # # debug code starts
    # for (veh, trip, schedule, cost) in edges:
    #     print('veh %d, trip %s, cost %.02f' % (veh.id, [r.id for r in trip], cost))
    # # debug code ends

    for (veh, trip, schedule, cost) in edges:
        veh_id = veh.id
        trip_id = tuple([r.id for r in trip])
        if trip_id in T_id_assigned:
            continue
        if veh_id in V_id_assigned:
            continue
        if np.any([r_id in R_id_assigned for r_id in trip_id]):
            continue
        for rid in trip_id:
            R_id_assigned.add(rid)
        T_id_assigned.add(trip_id)
        V_id_assigned.add(veh_id)
        V_id_assigned_list.append(veh_id)
        schedule_assigned.append(schedule)
        print('     *trip %s is assigned to veh %d' % ([req.id for req in trip], veh_id))

    # return R_id_assigned, V_id_assigned_list, schedule_assigned
    R_assigned = set()
    for req_id in R_id_assigned:
        R_assigned.add(model.reqs[req_id])
    model.reqs_picking.update(R_assigned)
    R_unassigned = set(model.queue) - R_assigned
    model.reqs_unassigned.update(R_unassigned)
    model.queue.clear()
    for veh_id, schedule in zip(V_id_assigned_list, schedule_assigned):
        model.vehs[veh_id].build_route(schedule, model.reqs, T)


def ILP_assign():
    with mosek.Env() as env:
        with env.Task(0, 0) as task:
            c = 1  # cost


def build_rtv_graph(vehs, reqs_pool, T):
    print('  building RTV-graph...')
    vehicle_trip_edges = []

    # # parallel
    # trip_list_all = Parallel(n_jobs=-1)(delayed(feasible_trips_search)(veh, reqs_in_queue, T)
    #                                     for veh in model.vehs)
    # for veh, (trip_list, schedule_list, cost_list) in zip(model.vehs, trip_list_all):
    #     for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
    #         for trip, schedule, cost in zip(trips, schedules, costs):
    #             vehicle_trip_edges.append([veh, trip, schedule, cost])

    # non-parallel
    for veh in vehs:
        trip_list, schedule_list, cost_list = feasible_trips_search(veh, reqs_pool, T)
        for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
            for trip, schedule, cost in zip(trips, schedules, costs):
                vehicle_trip_edges.append([veh, trip, schedule, cost])
        # print('veh %d is finished' % veh.id)

    # # debug code starts
    # for veh in model.vehs:
    #     trip_list, schedule_list, cost_list = feasible_trips_search(veh, model.queue, T)
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

    return vehicle_trip_edges


# search all feasible trips for a single vehicle, incrementally from the trip size of one
# a time consuming step
def feasible_trips_search(veh, reqs, T):
    CUTOFF = 30
    start_time = time.time()
    trip_list = [[]]  # all feasible trips of size 1, (2, 3...)
    schedule_list = [[]]  # best schedules for trips of size 1, (2, 3...)
    cost_list = [[]]  # min cost for trips of size 1, (2, 3...)
    schedules_k = []  # all feasible schedules for trips of size k

    # trips of size 1
    for req in reqs:
        # filter the req which can not be served even when the veh is idle
        dt_rough = get_duration_haversine(veh.lng, veh.lat, req.olng, req.olat)
        if dt_rough + T > req.Clp:
            continue
        dt = get_duration(veh.lng, veh.lat, req.olng, req.olat)
        if dt is None:  # no available route is found
            continue
        if dt + T <= req.Clp:
            trip = tuple([req])  # trip is defined as tuple
            _schedule = []
            if not veh.idle:
                for leg in veh.route:
                    _schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.ddl))
            best_schedule, min_cost, schedules = compute_schedule(veh, trip, [], [_schedule])
            if best_schedule:
                trip_list[0].append(trip)
                schedule_list[0].append(best_schedule)
                cost_list[0].append(min_cost)
                schedules_k.append(schedules)
                # print('size 1 add', req.id, 'schedules_num', len(schedules))
    # print('veh', veh.id, ', trip size:', 1, ', num of trips:', len(trip_list[0]))

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE + 1):
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

                # # debug code starts
                # reqid=[]
                # for req in trip_k:
                #     reqid.append(req.id)
                # print('veh', veh.id, 'test trip', reqid)
                # # debug code ends

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

                # debug code
                n2 += 1

                best_schedule, min_cost, schedules = compute_schedule(veh, trip_k, _trip, _schedules)
                if best_schedule:
                    trip_list[k - 1].append(trip_k)
                    schedule_list[k-1].append(best_schedule)
                    cost_list[k-1].append(min_cost)
                    schedules_k.append(schedules)

                    # debug code
                    n3 += 1

                    # # debug code starts
                    # reqid=[]
                    # for req in trip_k:
                    #     reqid.append(req.id)
                    # print('size', k, 'add', reqid, 'schedules_num', len(schedules))
                    # # debug code ends

                if time.time() - start_time > CUTOFF:
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
        # print('veh', veh.id, ', trip size:', k, ', num of trips:', len(trip_list[k-1]))
        if len(trip_list[k-1]) == 0:
            trip_list.pop()
            schedule_list.pop()
            cost_list.pop()
            break

    return trip_list, schedule_list, cost_list


# compute all feasible schedules of given vehicle v and trip T.
# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh, trip, _trip, _schedules):
    best_schedule = None
    min_cost = np.inf
    feasible_schedules = []
    ealist_pick_up_point = 0
    ealist_drop_off_point = 0
    viol = None

    if len(trip) == 1:
        req = trip[0]
    else:
        req = tuple(set(trip) - set(_trip))[0]

    for schedule in _schedules:
        # # check if the req has same origin-destination as any other req in the schedule
        # p = set()
        # d = set()
        # for (rid, pod, tlng, tlat, ddl) in schedule:
        #     if pod == 1 and req.olng == tlng and req.olat == tlat:
        #         p.add(rid)
        #     if pod == -1 and req.dlng == tlng and req.dlat == tlat:
        #         d.add(rid)
        # same_req = p & d
        # if len(same_req) > 0:
        #     print(' # check if the req has same origin-destination as any other req in the schedule')
        #     time.sleep(100)
        #     i = 0
        #     i_p = 0
        #     i_d = 0
        #     for (rid, pod, tlng, tlat, ddl) in schedule:
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
        #     schedule.insert(i_p, (req.id, 1, req.olng, req.olat, req.Clp))
        #     schedule.insert(i_d, (req.id, -1, req.dlng, req.dlat, req.Cld))
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
        dt = get_duration(veh.lng, veh.lat, req.olng, req.olat)
        for i in reversed(range(l)):
            if veh.T + dt > schedule[i][4]:
                ealist_pick_up_point = i + 1
                break
        # if the shortest travel time of req is longer than the time constrain of a leg in the schedule,
        # it cannot be dropped-off before that leg.
        for i in reversed(range(l)):
            if veh.T + req.Ts > schedule[i][4]:
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
                schedule.insert(i, (req.id, 1, req.olng, req.olat, req.Clp))
                schedule.insert(j, (req.id, -1, req.dlng, req.dlat, req.Cld))
                flag, c, viol = test_constraints_get_cost(schedule, veh, req, j)
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
def test_constraints_get_cost(schedule, veh, req, drop_point):
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
        dt = get_duration(lng, lat, tlng, tlat)
        if dt is None:
            return False, None, 1  # no route found between points
        t += dt
        if T + t > ddl:
            if rid == req.id:
                # pod == -1 means a new pick-up insertion is needed, since later drop-off brings longer travel time
                # pod == 1 means no more feasible schedules is available, since later pick-up brings longer wait time
                return False, None, 2 if pod == -1 else 3
            if k <= drop_point:
                # k<=drop_point means the violation is caused by the pick-up of req,
                # since the violation happens before the drop-off of req
                return False, None, 4
            return False, None, 0
        c += n * dt * COEF_INVEH
        n += pod
        assert n <= veh.K
        c += t * COEF_WAIT if pod == 1 else 0
        lng = tlng
        lat = tlat

    return True, c, -1

