"""
compute all feasible schedules of each veh-trip combinations between the vehicle fleet and requests in pool
(queue + picking + unassigned)
"""

import copy
import time
import numpy as np
from tqdm import tqdm

from lib.Configure import RIDESHARING_SIZE, DISPATCHER, CUTOFF_VT
from lib.A0_ScheduleFinder import compute_schedule, test_constraints_get_cost, compute_sche_cost
from lib.S_Route import get_duration


# build VT table for each veh, respectively
def build_vt_table(vehs, reqs_new, reqs_prev, T, K, mean_n_s_c, n_t_c):
    rid_prev = {req.id for req in reqs_prev}

    veh_trip_edges = []
    for veh in vehs:
    # for veh in tqdm(vehs, desc=DISPATCHER + ' Table'):
        feasible_shared_trips_search(veh, reqs_new, rid_prev, T, K, mean_n_s_c, n_t_c)
        for VTtable_k in veh.VTtable:
            for (trip, best_sche, cost, feasible_sches) in VTtable_k:
                veh_trip_edges.append((veh, trip, best_sche, cost))
    return veh_trip_edges


# search all feasible trips for a single vehicle, incrementally from the trip size of one
# a time consuming step
def feasible_shared_trips_search(veh, reqs_new, rid_prev, T, K, mean_n_s_c, n_t_c):
    veh_params = [veh.nid, veh.t_to_nid, veh.n]
    # trips of size 1
    # add old trips (size 1)
    if DISPATCHER == 'OSP-RO':
        veh.VTtable[0] = upd_prev_sches(veh, rid_prev, k=1)
    else:
        veh.VTtable[0].clear()
    n_prev_trips_k = len(veh.VTtable[0])  # number of old trips of size 1

    # add new trips (size 1)
    sub_sches, rid_enroute = restore_basic_sub_sches(veh)

    for req in reqs_new:
    # for req in tqdm(reqs_new, desc='size 1 trip'):
        # filter out the req which can not be served even when the veh is idle
        if get_duration(veh.nid, req.onid) + veh.t_to_nid + T > req.Clp:
            continue
        trip = tuple([req])  # trip is defined as tuple
        req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
        best_sche, min_cost, feasible_sches, n_s_c = compute_schedule(veh_params, sub_sches, req_params, T, K)
        if best_sche:
            veh.VTtable[0].append((trip, best_sche, min_cost, feasible_sches))
            # debug code
            assert {r.id for r in trip} == {rid for (rid, pod, tnid, ept, ddl) in best_sche} - rid_enroute
            assert {r.id for r in trip} <= {r.id for r in reqs_new}

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE + 1):
        start_time = time.time()

        # add old trips
        if DISPATCHER == 'OSP-RO':
            veh.VTtable[k - 1] = upd_prev_sches(veh, rid_prev, k)
        else:
            veh.VTtable[k - 1].clear()
        n_prev_trips_k_1 = n_prev_trips_k  # number of old trips of size k-1
        n_prev_trips_k = len(veh.VTtable[k - 1])  # number of old trips of size k

        # add new trips
        n_all_trips_k_1 = len(veh.VTtable[k - 2])  # number of all trips of size k-1
        n_new_trips_k_1 = n_all_trips_k_1 - n_prev_trips_k_1  # number of new trips of size k-1

        for i in range(1, n_new_trips_k_1 + 1):
        # for i in tqdm(range(1, n_new_trips_k_1 + 1), desc='size '+str(k)+' trip'):
            trip1 = veh.VTtable[k - 2][-i][0]  # a trip of size k-1
            for j in range(i + 1, n_all_trips_k_1 + 1):
                trip2 = veh.VTtable[k - 2][-j][0]  # another trip of size k-1 (different from trip1)
                trip_k = tuple(sorted(set(trip1).union(set(trip2)), key=lambda r: r.id))
                if k > 2:
                    # check trip size is k
                    if len(trip_k) != k:
                        continue
                    # check trip is already computed
                    all_found_trip_k = [vt[0] for vt in veh.VTtable[k - 1]]
                    if trip_k in all_found_trip_k:
                        continue
                    # check all subtrips are feasible
                    subtrips_check = True
                    for req in trip_k:
                        one_subtrip_of_trip_k = tuple(sorted((set(trip_k) - set([req])), key=lambda r: r.id))
                        all_found_trip_k_1 = [vt[0] for vt in veh.VTtable[k - 2]]
                        if one_subtrip_of_trip_k not in all_found_trip_k_1:
                            subtrips_check = False
                            break
                    if not subtrips_check:
                        continue

                sub_S1 = veh.VTtable[k - 2][-i][3]
                req1 = tuple(set(trip_k) - set(trip1))[0]
                req1_params = [req1.id, req1.onid, req1.dnid, req1.Tr, req1.Ts, req1.Clp, req1.Cld]
                best_sche1, min_cost1, feasible_S1, n_s_c = compute_schedule(veh_params, sub_S1, req1_params, T, K)

                # count the number of feasible schedules algorithm considers
                mean_n_s_c[k-2] = round((mean_n_s_c[k-2] * n_t_c[k-2] + n_s_c) / (n_t_c[k-2] + 1), 2)
                n_t_c[k - 2] += 1

                print('mean counting schedules', mean_n_s_c)
                print('count trips', n_t_c)

                # sub_S2 = veh.VTtable[k - 2][-j][3]
                # req2 = tuple(set(trip_k) - set(trip2))[0]
                # req2_params = [req2.id, req2.onid, req2.dnid, req2.Tr, req2.Ts, req2.Clp, req2.Cld]
                # best_sche2, min_cost2, feasible_S2 = compute_schedule(veh_params, sub_S2, req2_params, T, K)
                #
                # if len(feasible_S1) >= len(feasible_S2):
                #     best_sche = best_sche1
                #     min_cost = min_cost1
                #     feasible_sches = feasible_S1
                # else:
                #     best_sche = best_sche2
                #     min_cost = min_cost2
                #     feasible_sches = feasible_S2

                best_sche = best_sche1
                min_cost = min_cost1
                feasible_sches = feasible_S1

                if best_sche:
                    veh.VTtable[k - 1].append((trip_k, best_sche, min_cost, feasible_sches))
                    # debug code
                    T_id = {r.id for r in trip_k}
                    R_id_in_sche = {rid for (rid, pod, tnid, ept, ddl) in best_sche} - rid_enroute
                    assert T_id == R_id_in_sche
                    assert {req.id for req in trip_k} <= {req.id for req in set(reqs_new)}.union(rid_prev)

                # threshold cutoff
                current_time = time.time()
                if current_time - start_time > CUTOFF_VT:
                    # print('veh', veh.id, 'cutoff size', k, 'trip, second search')
                    break

            # threshold cutoff
            current_time = time.time()
            if current_time - start_time > CUTOFF_VT * 6:
                # print('veh', veh.id, 'cutoff size', k, 'trip, first search')
                break

        if len(veh.VTtable[k - 1]) == 0:
            for k1 in range(k, RIDESHARING_SIZE):
                veh.VTtable[k1].clear()
            break


def restore_basic_sub_sches(veh):
    sub_sche = []
    rid_enroute = set()
    if not veh.idle:
        for leg in veh.route:
            if DISPATCHER == 'OSP-RO':
                if leg.rid in veh.onboard_rid:
                    sub_sche.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
                    rid_enroute.add(leg.rid)
            else:
                if leg.pod != 0:
                    sub_sche.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
                    rid_enroute.add(leg.rid)
    sub_sches = [sub_sche]

    # veh_params = [veh.nid, veh.t_to_nid, veh.n]
    # legs = []
    # rid_enroute = set()
    # if not veh.idle:
    #     for leg in veh.route:
    #         if DISPATCHER == 'OSP-RO':
    #             if leg.rid in veh.onboard_rid:
    #                 legs.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
    #                 rid_enroute.add(leg.rid)
    #         else:
    #             if leg.pod != 0:
    #                 legs.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
    #                 rid_enroute.add(leg.rid)
    # if not len(legs) == 0:
    #     sches_a = [[]]
    #     for (rid, pod, tnid, ept, ddl) in legs:
    #         sches_b = []
    #         for sche in sches_a:
    #             l = len(sche)
    #             for i in range(l + 1):
    #                 sche.insert(i, (rid, pod, tnid, ept, ddl))
    #                 flag, c, viol = test_constraints_get_cost(veh_params, sche, rid, 0, 0, veh.T, veh.K)
    #                 if flag:
    #                     sches_b.append(copy.deepcopy(sche))
    #                 sche.pop(i)
    #         sches_a = sches_b
    #     sub_sches = sches_a
    #     assert len(sub_sches[0]) == len(legs)
    # else:
    #     sub_sches = [[]]

    return sub_sches, rid_enroute


# find out which trips from last interval can be still considered feasible size k trips in current interval
def upd_prev_sches(veh, rid_prev, k):
    veh_params = [veh.nid, veh.t_to_nid, veh.n]
    old_VTtable_k = []

    new_pick_rid = set(veh.new_pick_rid)
    new_drop_rid = set(veh.new_drop_rid)
    new_both_rid = new_pick_rid.union(new_drop_rid)
    n_new_pick = len(veh.new_pick_rid)
    n_new_drop = len(veh.new_drop_rid)
    n_new_both = n_new_pick + n_new_drop
    assert n_new_both == len(new_both_rid)
    k = k + n_new_pick
    if k > RIDESHARING_SIZE:
        return old_VTtable_k

    if n_new_pick == 0:
        trip_id_sub = set()
        trip_id_sup = rid_prev
    else:
        trip_id_sub = new_pick_rid
        trip_id_sup = rid_prev.union(new_pick_rid)
        assert len(trip_id_sup) - len(rid_prev) == n_new_pick

    veh_route = [(leg.rid, leg.pod) for leg in veh.route]

    # if veh.id == 42:
    #     assert n_new_both == 0
    #     print('veh_sample 42 route', veh_route)
    #     print('veh_sample 42 trip id range', [trip_id_sub, trip_id_sup])

    if len(veh_route) > 0 and veh_route[0] == (-2, 0):
        veh_route.remove(veh_route[0])

    # if veh.id == 42:
    #     assert n_new_both == 0
    #     print('veh_sample 42 route', veh_route)
    #     print('veh_sample 42 trip id range', [trip_id_sub, trip_id_sup])

    veh_rid_enroute = {leg.rid for leg in veh.route} - {-2}
    for (trip, best_sche, cost, all_sches) in veh.VTtable[k - 1]:
        trip_id = {req.id for req in trip}

        # if veh.id == 42:
        #     print(' trip_id', trip_id)
        #     print(' best sche', best_sche)

        if trip_id_sub < trip_id <= trip_id_sup:
            best_sche = None
            min_cost = np.inf
            feasible_sches = []
            if n_new_pick != 0:
                # remove picked req in trip
                trip_ = list(trip)
                for req in trip:
                    if req.id in new_pick_rid:
                        trip_.remove(req)
                trip_ = tuple(sorted(trip_, key=lambda r: r.id))
            else:
                trip_ = trip
            for sche in all_sches:
                if n_new_both != 0:
                    if {sche[i][0] for i in range(n_new_both)} != new_both_rid:
                        continue
                    else:
                        assert sum([sche[i][1] for i in range(n_new_both)]) == n_new_pick - 1 * n_new_drop
                        del sche[0:n_new_both]

                # codes to fix bugs that caused by non-static travel times (starts)
                # (the same schedule (which is feasible) might not be feasible after veh moves along that schedule,
                #     if travel times are not static) (also unshared trips can be ensured)
                trip_id_ = {req.id for req in trip_}
                trip_sche_ = [(rid, pod) for (rid, pod, tnid, ept, ddl) in sche]

                # if veh.id == 42:
                #     print(' trip_id_', trip_id_)
                #     print(' trip_sche_', trip_sche_)

                if trip_sche_ == veh_route:
                    flag = True
                    c = compute_sche_cost(veh_params, sche, veh.T, veh.K)
                elif trip_id_ < veh_rid_enroute:
                    veh_partial_route = []
                    for (rid, pod) in veh_route:
                        if rid in trip_id_.union(set(veh.onboard_rid)):
                            veh_partial_route.append((rid, pod))
                    if trip_sche_ == veh_partial_route:
                        flag = True
                        c = compute_sche_cost(veh_params, sche, veh.T, veh.K)
                    else:
                        new_req_pick_idx = 0
                        if sche[0][0] in veh.onboard_rid:
                            new_req_pick_idx = 1
                        flag, c, viol = test_constraints_get_cost(veh_params, sche, trip_[0].id, new_req_pick_idx, 0,
                                                                  veh.T, veh.K)
                else:
                    new_req_pick_idx = 0
                    if sche[0][0] in veh.onboard_rid:
                        new_req_pick_idx = 1
                    flag, c, viol = test_constraints_get_cost(veh_params, sche, trip_[0].id, new_req_pick_idx, 0, veh.T,
                                                              veh.K)
                # codes to fix bugs that caused by non-static travel times  (ends)

                if flag:
                    feasible_sches.append(copy.deepcopy(sche))
                    if c < min_cost:
                        best_sche = copy.deepcopy(sche)
                        min_cost = c
            if len(feasible_sches) > 0:
                old_VTtable_k.append((trip_, best_sche, min_cost, feasible_sches))
                T_id = {r.id for r in trip_}
                R_id_in_sche = set()
                for (rid, pod, tnid, ept, ddl) in best_sche:
                    if pod == 1:
                        R_id_in_sche.add(rid)
                assert T_id == R_id_in_sche
                assert {req.id for req in trip_} <= rid_prev

    # if veh.id == 42:
    #     print(' old_VTtable_k', k, old_VTtable_k)

    assert len([vt[0] for vt in old_VTtable_k]) == len(set([vt[0] for vt in old_VTtable_k]))
    return old_VTtable_k
