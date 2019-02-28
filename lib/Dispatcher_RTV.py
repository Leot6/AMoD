"""
dispatch algorithms for the AMoD system
"""

import copy
import time
import requests
import numpy as np
from joblib import Parallel, delayed
from lib.Vehicle import *


def greedy_assign(model, osrm, vehicle_trip_edges, T):
    R_id_served = set()
    T_id_served = set()
    V_id_assigned = set()
    R_served = set()
    edges = sorted(vehicle_trip_edges, key=lambda e: (-len(e[1]), e[3]))
    print("    -start greedy assign with %d edges:" % len(edges))
    for (veh, trip, schedule, cost) in edges:
        veh_id = veh.id
        trip_id = tuple([r.id for r in trip])
        if trip_id in T_id_served:
            continue
        if veh_id in V_id_assigned:
            continue
        if np.any([r_id in R_id_served for r_id in trip_id]):
            continue
        model.vehs[veh_id].build_route(osrm, schedule, model.reqs, T)
        for rid in trip_id:
            R_id_served.add(rid)
            R_served.add(model.reqs[rid])
        T_id_served.add(trip_id)
        V_id_assigned.add(veh_id)

        print("     *trip %s is assigned to veh %d" % ([req.id for req in trip], veh.id))
    R_miss = set(model.queue) - R_served
    model.queue.clear()
    model.reqs_picking.update(R_served)
    model.rejs.extend(list(R_miss))


def build_rtv_graph(model, osrm, T):
    vehicle_trip_edges = []
    reqs_in_queue = model.queue
    print("  building RTV-graph...")

    # # parallel
    # trip_list_all = Parallel(n_jobs=-1)(delayed(single_vehicle_rtv_generation)(osrm, veh, reqs_in_queue, T)
    #                                     for veh in model.vehs)
    # for veh, (trip_list, schedule_list, cost_list) in zip(model.vehs, trip_list_all):
    #     for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
    #         for trip, schedule, cost in zip(trips, schedules, costs):
    #             vehicle_trip_edges.append([veh, trip, schedule, cost])

    # non-parallel
    for veh in model.vehs:
        trip_list, schedule_list, cost_list = single_vehicle_rtv_generation(osrm, veh, reqs_in_queue, T)
        for trips, schedules, costs in zip(trip_list, schedule_list, cost_list):
            for trip, schedule, cost in zip(trips, schedules, costs):
                vehicle_trip_edges.append([veh, trip, schedule, cost])

    # # debug code starts
    # for veh in model.vehs:
    #     trip_list, schedule_list, cost_list = single_vehicle_rtv_generation(osrm, veh, model.queue, T)
    #     l = len(trip_list)
    #     print("max trip size is", l)
    #     for i in range(l):
    #         l_1 = len(trip_list[i])
    #         print(" number of trip size", i+1, "is", l_1)
    #         for j in range(l_1):
    #             reqid = []
    #             for req in trip_list[i][j]:
    #                 reqid.append(req.id)
    #             legid = []
    #             for leg in schedule_list[i][j]:
    #                 legid.append([leg[0], leg[1]])
    #             print("  trip:", reqid, ", schedule:", legid, ", cost:", cost_list[i][j])
    # # debug code ends

    greedy_assign(model, osrm, vehicle_trip_edges, T)


# build the rtv-graph for a single vehicle, incrementally from the trip size of one
# a time consuming step
def single_vehicle_rtv_generation(osrm, veh, reqs, T):
    CUTOFF = 30
    start_time = time.time()
    trip_list = [[]]  # all feasible trips of size 1, (2, 3...)
    schedule_list = [[]]  # best schedules for trips of size 1, (2, 3...)
    cost_list = [[]]  # min cost for trips of size 1, (2, 3...)
    schedules_k = []  # all feasible schedules for trips of size k

    # trips of size 1
    for req in reqs:
        # filter the req which can not be served even when the veh is idle
        if osrm.get_duration(veh.lng, veh.lat, req.olng, req.olat) + T <= req.Clp:
            trip = tuple([req])  # trip is defined as tuple
            _schedule = []
            if not veh.idle:
                for leg in veh.route:
                    _schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.ddl))
            best_schedule, min_cost, schedules = compute_schedule(osrm, veh, trip, [], [_schedule])
            if best_schedule:
                trip_list[0].append(trip)
                schedule_list[0].append(best_schedule)
                cost_list[0].append(min_cost)
                schedules_k.append(schedules)
                # print("size 1 add", req.id, "schedules_num", len(schedules))
    print("veh", veh.id, ", trip size:", 1, ", num of trips:", len(trip_list[0]))

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
        #             print("schedule:", reqid)
        #         for (rid, pod, tlng, tlat, ddl) in s[0]:
        #                 scc.append([rid, pod, tlng, tlat, ddl])
        #         print("schedule num:", len(s), ", is", scc)
        # print("veh:", veh.id, ", trip size:", k-1, ", schedules:", sch_num)
        # # debug code ends

        # debug code
        n1 = 0
        n2 = 0
        n3 = 0

        l = len(trip_list[k - 2])
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
                # print("veh", veh.id, "test trip", reqid)
                # # debug code ends

                subtrips_check = True
                if k > 2:
                    if len(trip_k) != k:
                        continue
                    if trip_k in trip_list[k - 1]:
                        continue
                    # check subtrips
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

                best_schedule, min_cost, schedules = compute_schedule(osrm, veh, trip_k, _trip, _schedules)
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
                    # print("size", k, "add", reqid, "schedules_num", len(schedules))
                    # # debug code ends

                if time.time() - start_time > CUTOFF:
                    # # debug code starts
                    # print("   number of trip size", k - 1, "is", len(trip_list[k - 2]))
                    # print("   number of trip size", k, "in test1 is", n1)
                    # print("   number of trip size", k, "in test2 is", n2)
                    # print("   number of trip size", k, "pass test is", n3)
                    # # debug code ends
                    print("veh", veh.id, ", trip size:", k, ", num of trips:", len(trip_list[k - 1]), "(time out)")
                    return trip_list, schedule_list, cost_list
        # # debug code starts
        # print("   number of trip size", k-1, "is", l)
        # print("   number of trip size", k, "in test1 is", n1)
        # print("   number of trip size", k, "in test2 is", n2)
        # print("   number of trip size", k, "pass test is", n3)
        # # debug code ends
        print("veh", veh.id, ", trip size:", k, ", num of trips:", len(trip_list[k-1]))
        if len(trip_list[k-1]) == 0:
            trip_list.pop()
            schedule_list.pop()
            cost_list.pop()
            break

    return trip_list, schedule_list, cost_list


# compute all feasible schedules of given vehicle v and trip T.
# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(osrm, veh, trip, _trip, _schedules):
    best_schedule = None
    min_cost = np.inf
    feasible_schedules = []
    ealist_drop_off_point = 0
    viol = None

    if len(trip) == 1:
        req = trip[0]
    else:
        req = tuple(set(trip) - set(_trip))[0]

    for schedule in _schedules:
        # check if the req has same origin-destination as any other req in the schedule
        p = set()
        d = set()
        for (rid, pod, tlng, tlat, ddl) in schedule:
            if pod == 1 and req.olng == tlng and req.olat == tlat:
                p.add(rid)
            if pod == -1 and req.dlng == tlng and req.dlat == tlat:
                d.add(rid)
        same_req = p & d
        if len(same_req) > 0:
            i = 0
            i_p = 0
            i_d = 0
            for (rid, pod, tlng, tlat, ddl) in schedule:
                i += 1
                if pod == 1 and rid in same_req:
                    if req.Clp <= ddl:
                        i_p = i-1
                    else:
                        i_p = i
                if pod == -1 and rid in same_req:
                    if req.Cld <= ddl:
                        i_d = i
                    else:
                        i_d = i+1
            schedule.insert(i_p, (req.id, 1, req.olng, req.olat, req.Clp))
            schedule.insert(i_d, (req.id, -1, req.dlng, req.dlat, req.Cld))
            flag, c, viol = test_constraints_get_cost(osrm, schedule, veh, req, i_d)
            if flag:
                feasible_schedules.append(copy.deepcopy(schedule))
                best_schedule = copy.deepcopy(schedule)
                min_cost = c
            schedule.pop(i_d)
            schedule.pop(i_p)
            return best_schedule, min_cost, feasible_schedules

        l = len(schedule)
        # if the shortest travel time of req is longer than the time constrain of a req already in the schedule,
        # it cannot be dropped-off before that req.
        for i in range(l):
            if veh.T + req.Ts > schedule[i][4]:
                ealist_drop_off_point = i + 2
                break

        # insert the req's pick-up point
        for i in range(l + 1):
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                viol = 0
                if j < ealist_drop_off_point:
                    continue
                schedule.insert(i, (req.id, 1, req.olng, req.olat, req.Clp))
                schedule.insert(j, (req.id, -1, req.dlng, req.dlat, req.Cld))
                flag, c, viol = test_constraints_get_cost(osrm, schedule, veh, req, j)
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
def test_constraints_get_cost(osrm, schedule, veh, req, drop_point):
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
        lng = tlng
        lat = tlat

    return True, c, -1


# # creating a new function instead using OsrmEngine is trying to avoid bugs - Timeout when call url
# def osrm_get_duration(olng, olat, dlng, dlat):
#     ghost = '0.0.0.0'
#     gport = 5000
#     url = "http://{0}:{1}/route/v1/driving/{2},{3};{4},{5}?alternatives=false&steps=" \
#           "{6}&annotations={7}&geometries=geojson".format(
#             ghost, gport, olng, olat, dlng, dlat, "false", "false")
#     # call_url
#     count = 0
#     while count < 10:
#         try:
#             response = requests.get(url, timeout=1)
#             json_response = response.json()
#             code = json_response['code']
#             if code == 'Ok':
#                 return json_response['routes'][0]['duration']
#             else:
#                 print("Error: %s" % (json_response['message']))
#                 return None
#         except requests.exceptions.Timeout:
#             print("call_url time out")
#             print(url)
#             count += 1
#         except Exception as err:
#             print("Failed: %s" % (url))
#             return None



# an attempt to build RV-graph, but it seems not necessary
# class RV_Graph(object):
#    # build RV-graph
#    def build_rv(self, osrm, T):
#        self.rv.clear_graph()
#        for veh in self.vehs:
#            self.rv.add_node_v(veh)
#        for req in self.queue:
#            self.rv.add_node_r(req)
#        # build e(r,v)
#        print("building e(r,v)...")
#        viol = None
#        dc_ = None
#        for veh in self.vehs:
#            route = []
#            if not veh.idle:
#                for leg in veh.route:
#                    route.append((leg.rid, leg.pod, leg.tlng, leg.tlat))
#            else:
#                assert veh.c == 0
#            l = len(route)
#            c = veh.c
#            for req in self.queue:
#                if osrm.get_duration(veh.lng, veh.lat, req.olng, req.olat) + T > req.Clp:
#                    break
#                dc_ = np.inf
#                for i in range(l + 1):
#                    for j in range(i + 1, l + 2):
#                        route.insert(i, (req.id, 1, req.olng, req.olat))
#                        route.insert(j, (req.id, -1, req.dlng, req.dlat))
#                        flag, c_, viol = self.test_constraints_get_cost(osrm, route, veh, req, c + dc_)
#                        if flag:
#                            dc_ = c_ - c
#                        route.pop(j)
#                        route.pop(i)
#                        if viol > 0 or viol == -1:
#                            break
#                    if viol == 3 or viol == -1:
#                        break
#                if dc_ != np.inf:
#                    self.rv.add_edge_rv(req, veh, weight=dc_)
#        # build e(r,r)
#        print("building e(r,r)...")
#        l = len(self.queue)
#        for i in range(l - 1):
#            req1 = self.queue[i]
#            for j in range(i + 1, l):
#                req2 = self.queue[j]
#                flag = False
#                if req1.Tr + req1.Ts > req2.Clp or req2.Tr + req2.Ts > req1.Clp:
#                    break
#                o1_o2 = osrm.get_duration(req1.olng, req1.olat, req2.olng, req2.olat)
#                o2_d1 = osrm.get_duration(req2.olng, req2.olat, req1.dlng, req1.dlat)
#                d1_d2 = osrm.get_duration(req1.dlng, req1.dlat, req2.dlng, req2.dlat)
#                o2_d2 = osrm.get_duration(req2.olng, req2.olat, req2.dlng, req2.dlat)
#                d2_d1 = osrm.get_duration(req2.dlng, req2.dlat, req1.dlng, req1.dlat)
#                o2_o1 = osrm.get_duration(req2.olng, req2.olat, req1.olng, req1.olat)
#                o1_d2 = osrm.get_duration(req1.olng, req1.olat, req2.dlng, req2.dlat)
#                o1_d1 = osrm.get_duration(req1.olng, req1.olat, req1.dlng, req1.dlat)
#                # o1-o2-d1-d2
#                if req2.Cep <= req1.Tr + o1_o2 <= req2.Clp \
#                    and req1.Tr + o1_o2 + o2_d1 <= req1.Cld \
#                        and req1.Tr + o1_o2 + o2_d1 + d1_d2 <= req2.Cld:
#                    flag = True
#                # o1-o2-d2-d1
#                elif req2.Cep <= req1.Tr + o1_o2 <= req2.Clp \
#                    and req1.Tr + o1_o2 + o2_d2 <= req2.Cld \
#                        and req1.Tr + o1_o2 + o2_d2 + d2_d1 <= req1.Cld:
#                    flag = True
#                # o2-o1-d2-d1
#                elif req1.Cep <= req2.Tr + o2_o1 <= req1.Clp \
#                    and req2.Tr + o2_o1 + o1_d2 <= req2.Cld \
#                        and req2.Tr + o1_o2 + o1_d2 + d2_d1 <= req1.Cld:
#                    flag = True
#                # o2-o1-d1-d2
#                elif req1.Cep <= req2.Tr + o2_o1 <= req1.Clp \
#                    and req2.Tr + o2_o1 + o1_d1 <= req1.Cld \
#                        and req2.Tr + o2_o1 + o1_d1 + d1_d2 <= req2.Cld:
#                    flag = True
#                if flag:
#                    self.rv.add_edge_rr(req1, req2)

