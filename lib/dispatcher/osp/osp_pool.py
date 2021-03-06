"""
compute all feasible schedules of each veh-trip combinations between the vehicle fleet and requests in pool
(queue + picking + unassigned)
"""

import pickle
import copy
import time
import numpy as np
from tqdm import tqdm
from itertools import permutations

from lib.simulator.config import FLEET_SIZE, RIDESHARING_SIZE
from lib.routing.routing_server import get_duration_from_origin_to_dest
from lib.dispatcher.osp.osp_schedule import compute_schedule, test_constraints_get_cost, compute_sche_cost

from lib.analysis.animation_generator import anim_sche
from lib.dispatcher.rtv.rtv_schedule import compute_schedule as compute_sche_rtv


# feasible trips (trip, best_schedule, min_cost, feasible_schedules)
VT_TABLE = [[[] for i in range(RIDESHARING_SIZE)] for j in range(FLEET_SIZE)]
PREV_VT_TABLE = None
CUTOFF_VT = 20
# FAST_COMPUTE = True
FAST_COMPUTE = False

# avg_num_of_sche_searched: # the number of possible schedules algorithm considers when finding the optimal schedule
# num_of_trips: # the number of different size trips algorithm considers
avg_num_of_sche_searched = [0] * RIDESHARING_SIZE
num_of_trip_searched = [0] * RIDESHARING_SIZE
show_counting = False

num_of_new_reqs = []
num_of_all_reqs = []
num_of_counting = 0


# build VT table for each veh, respectively
def build_vt_table(vehs, reqs_new, reqs_prev, T):
    if FAST_COMPUTE:
        reqs_pool_vt = reqs_new
        rids_prev = {req.id for req in reqs_prev}
    else:
        reqs_pool_vt = reqs_prev + reqs_new
        rids_prev = set()
    clear_up_vt_table()
    veh_trip_edges = []

    clear_veh_candidate_sches(vehs)
    # for veh in vehs:
    for veh in tqdm(vehs, desc=f'OSP ({len(reqs_pool_vt)}/{len(reqs_new) + len(reqs_prev)} reqs)', leave=False):
        feasible_shared_trips_search(veh, reqs_pool_vt, rids_prev, T)
        for veh_vt_k in VT_TABLE[veh.id]:
            for (trip, best_sche, cost, feasible_sches) in veh_vt_k:
                veh_trip_edges.append((veh, trip, best_sche, cost))
                veh.candidate_sches.append(best_sche)

    # # debug
    # if 60 * (30 + 0) < T <= 60 * (30 + 30):
    #     global num_of_new_reqs
    #     global num_of_all_reqs
    #     num_of_new_reqs.append(len(reqs_new))
    #     num_of_all_reqs.append(len(reqs_new) + len(reqs_prev))
    #     print(f'reqs:{round(np.mean(num_of_new_reqs))}/{round(np.mean(num_of_all_reqs))}')
    #
    #     n_largest = 0
    #     vid_largest = 0
    #     for veh in vehs:
    #         veh_vt_1 = VT_TABLE[veh.id][0]
    #         n = len(veh_vt_1)
    #         if n > n_largest:
    #             n_largest = n
    #             vid_largest = veh.id
    #     vt_largest = VT_TABLE[vid_largest]
    #     vt_prev_largest = PREV_VT_TABLE[vid_largest]
    #     avg_num_of_old_trips = [0] * RIDESHARING_SIZE
    #     avg_num_of_new_trips = [0] * RIDESHARING_SIZE
    #     for i in range(0, RIDESHARING_SIZE):
    #         avg_num_of_old_trips[i] = len(upd_prev_sches(vehs[vid_largest], rids_prev, i+1, T))
    #         avg_num_of_new_trips[i] = len(vt_largest[i]) - avg_num_of_old_trips[i]
    #     print('avg_num_of_old_trips', avg_num_of_old_trips)
    #     print('avg_num_of_new_trips', avg_num_of_new_trips)
    # # debug

    return veh_trip_edges


# search all feasible trips for a single vehicle, incrementally from the trip size of one
# a time consuming step
def feasible_shared_trips_search(veh, reqs_new, rids_prev, T):
    veh_params = [veh.nid, veh.t_to_nid, veh.n]
    veh_vt = VT_TABLE[veh.id]

    if 60 * (30 + 0) < T <= 60 * (30 + 30):
        global num_of_counting
        num_of_counting += 1

    # trips of size 1
    if FAST_COMPUTE:
        veh_vt[0] = upd_prev_sches(veh, rids_prev, 1, T)
        n_prev_trips_k = len(veh_vt[0])  # number of old trips of size 1

    # add new trips (size 1)
    sub_sches = restore_basic_sub_sches(veh)
    for req in reqs_new:
    # for req in tqdm(reqs_new, desc=f'veh {veh.id} (size 1)', leave=False):
        # filter out the req which can not be served even when the veh is idle
        if get_duration_from_origin_to_dest(veh.nid, req.onid) + veh.t_to_nid + T > req.Clp:
            continue
        trip = tuple([req])  # trip is defined as tuple
        req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
        best_sche, min_cost, feasible_sches, num_of_sche_searched \
            = compute_schedule(veh_params, sub_sches, req_params, T)
        if best_sche:
            veh_vt[0].append((trip, best_sche, min_cost, feasible_sches))
            # debug code
            assert {r.id for r in trip} == {rid for (rid, pod, tnid, ept, ddl) in best_sche} - set(veh.onboard_rids)
            assert {r.id for r in trip} <= {r.id for r in reqs_new}

    # trips of size k (k >= 2)
    for k in range(2, RIDESHARING_SIZE + 1):
        start_time = time.time()
        if FAST_COMPUTE:
            n_prev_trips_k_1 = n_prev_trips_k  # number of old trips of size k-1
            n_all_trips_k_1 = len(veh_vt[k - 2])  # number of all trips of size k-1
            n_new_trips_k_1 = n_all_trips_k_1 - n_prev_trips_k_1  # number of new trips of size k-1
            veh_vt[k - 1] = upd_prev_sches(veh, rids_prev, k, T)
            n_prev_trips_k = len(veh_vt[k - 1])  # number of old trips of size k
        else:
            n_all_trips_k_1 = len(veh_vt[k - 2])
            n_new_trips_k_1 = n_all_trips_k_1

        for i in range(1, n_new_trips_k_1 + 1):
        # for i in tqdm(range(1, n_new_trips_k_1 + 1), f'veh {veh.id} (size {k})', leave=False):
            trip1 = veh_vt[k - 2][-i][0]  # a trip of size k-1
            for j in range(i + 1, n_all_trips_k_1 + 1):
                trip2 = veh_vt[k - 2][-j][0]  # another trip of size k-1 (different from trip1)
                trip_k = tuple(sorted(set(trip1).union(set(trip2)), key=lambda r: r.id))
                if k > 2:
                    # check trip size is k
                    if not len(trip_k) == k:
                        continue
                    # check trip is not already computed
                    all_found_trip_k = [vt[0] for vt in veh_vt[k - 1]]
                    if trip_k in all_found_trip_k:
                        continue
                    # check all subtrips are feasible
                    subtrips_check = True
                    for req in trip_k:
                        one_subtrip_of_trip_k = tuple(sorted((set(trip_k) - set([req])), key=lambda r: r.id))
                        all_found_trip_k_1 = [vt[0] for vt in veh_vt[k - 2]]
                        if one_subtrip_of_trip_k not in all_found_trip_k_1:
                            subtrips_check = False
                            break
                    if not subtrips_check:
                        continue

                sub_sches1 = veh_vt[k - 2][-i][3]
                req1 = tuple(set(trip_k) - set(trip1))[0]
                req2_params = [req1.id, req1.onid, req1.dnid, req1.Tr, req1.Ts, req1.Clp, req1.Cld]
                best_sche1, min_cost1, feasible_sches1, num_of_sche_searched1 \
                    = compute_schedule(veh_params, sub_sches1, req2_params, T)

                # sub_sches2 = veh_vt[k - 2][-j][3]
                # req2 = tuple(set(trip_k) - set(trip2))[0]
                # req2_params = [req2.id, req2.onid, req2.dnid, req2.Tr, req2.Ts, req2.Clp, req2.Cld]
                # best_sche2, min_cost2, feasible_sches2, num_of_sche_searched2 = compute_schedule(veh_params, sub_sches2,
                #                                                                              req2_params, T)
                # if best_sche1 and not min_cost2 == min_cost1:
                #     print(f'len(feasible_S): {len(feasible_sches1)}/{len(feasible_sches2)}, min_cost: {min_cost1} '
                #           f'/ {min_cost2}, num_s_c:{num_of_sche_searched1}/{num_of_sche_searched2}')
                #     print('best_sche1', best_sche1)
                #     print('best_sche2', best_sche2)

                best_sche = best_sche1
                min_cost = min_cost1
                feasible_sches = feasible_sches1
                num_of_sche_searched = num_of_sche_searched1

                # req_Ts = sorted([r.Ts for r in trip_k])[-2]
                #
                # if best_sche and k == 4 and len(set([r.onid for r in trip_k] + [r.dnid for r in trip_k])) == k * 2 \
                #         and 40 < num_of_sche_searched < 50 and req_Ts > 500 and len(veh.onboard_rids) <= 1:
                #     best_sche_rtv, min_cost_rtv, num_of_sche_searched_rtv, sches_searched_rtv\
                #         = compute_sche_rtv(veh_params, sub_sches[0], trip_k, T)
                #     if not best_sche_rtv:
                #         continue
                #     print(f'veh {veh.id}, on_board {veh.onboard_rids}, trip {[r.id for r in trip_k]}, '
                #           f'num of sches {num_of_sche_searched}/{num_of_sche_searched_rtv}')
                #     # assert best_sche == best_sche_rtv
                #     if num_of_sche_searched_rtv < 1300:
                #         a = anim_sche(copy.deepcopy(veh), trip_k, sches_searched, best_sche, 'osp')
                #         # b = anim_sche(copy.deepcopy(veh), trip_k, sches_searched_rtv, best_sche, 'rtv')
                #         data = [veh, trip_k, sches_searched, sches_searched_rtv, best_sche]
                #         with open(f'anime_sche_data_{veh.id}.pickle', 'wb') as f:
                #             pickle.dump(data, f)

                if show_counting:
                    # count the number of feasible schedules algorithm considers
                    k_c = k + len(veh.onboard_rids)
                    num_of_trip_searched[k_c - 2] += 1
                    avg_num_of_sche_searched[k_c - 2] += ((num_of_sche_searched - avg_num_of_sche_searched[k_c - 2])
                                                        / num_of_trip_searched[k_c - 2])
                    avg_num_of_sche_searched[k_c - 2] = round(avg_num_of_sche_searched[k_c - 2], 2)
                    print('mean counting schedules', avg_num_of_sche_searched)
                    print('count trips', num_of_trip_searched)

                if best_sche:
                    veh_vt[k - 1].append((trip_k, best_sche, min_cost, feasible_sches))
                    # debug code
                    rids_in_trip = {r.id for r in trip_k}
                    rids_in_sche = {rid for (rid, pod, tnid, ept, ddl) in best_sche} - set(veh.onboard_rids)
                    assert rids_in_trip == rids_in_sche
                    assert {req.id for req in trip_k} <= {req.id for req in set(reqs_new)}.union(rids_prev)

                # threshold cutoff
                current_time = time.time()
                if current_time - start_time > 0.1 * CUTOFF_VT / RIDESHARING_SIZE:
                    # print('veh', veh.id, 'cutoff size', k, 'trip, second search')
                    break

            # threshold cutoff
            current_time = time.time()
            if current_time - start_time > CUTOFF_VT / RIDESHARING_SIZE:
                # print('veh', veh.id, 'cutoff size', k, 'trip, first search')
                break

        if len(veh_vt[k - 1]) == 0:
            for k1 in range(k, RIDESHARING_SIZE):
                veh_vt[k1].clear()
            break


def restore_basic_sub_sches(veh):
    veh_params = [veh.nid, veh.t_to_nid, veh.n]
    sub_sches = []
    sub_sche = []
    if not veh.idle:
        for leg in veh.route:
            if leg.rid in veh.onboard_rids:
                sub_sche.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
    assert len(sub_sche) == veh.n
    sub_sches.append(sub_sche)
    possible_sub_sches = permutations(sub_sche)
    for sche in possible_sub_sches:
        sche = list(sche)
        if not sche == sub_sche:
            flag, c, viol = test_constraints_get_cost(veh_params, sche, 0, 0, 0, veh.T)
            if flag:
                sub_sches.append(sche)
    return sub_sches


def get_prev_assigned_edges(vehs, reqs, T):
    prev_assigned_edges = []
    for veh in vehs:
        if not veh.idle and 1 in {leg.pod for leg in veh.route}:
            trip = tuple([reqs[rid] for rid in sorted(veh.picking_rids)])
            sche = []
            for (rid, pod, tnid, ept, ddl) in veh.sche:
                if pod == 1 and not ddl == reqs[rid].Clp:
                    ddl = reqs[rid].Clp
                sche.append((rid, pod, tnid, ept, ddl))
            veh_params = [veh.nid, veh.t_to_nid, veh.n]
            cost = compute_sche_cost(veh_params, sche, T) * 1.08
            prev_assigned_edges.append((veh, trip, sche, cost))
    return prev_assigned_edges


# find out which trips from last interval can be still considered feasible size k trips in current interval
def upd_prev_sches(veh, rids_prev, k, T):
    veh_params = [veh.nid, veh.t_to_nid, veh.n]
    prev_veh_vt = PREV_VT_TABLE[veh.id]
    updated_prev_vt_k = []

    new_pick_rids = set(veh.new_picked_rids)
    new_drop_rids = set(veh.new_droped_rids)
    new_both_rids = new_pick_rids.union(new_drop_rids)
    n_new_pick = len(new_pick_rids)
    n_new_drop = len(new_drop_rids)
    n_new_both = n_new_pick + n_new_drop
    k = k + n_new_pick
    if k > RIDESHARING_SIZE or not prev_veh_vt[k-1]:
        return []

    if n_new_pick == 0:
        T_id_sub = set()
        T_id_sup = rids_prev
    else:
        T_id_sub = new_pick_rids
        T_id_sup = rids_prev.union(new_pick_rids)

    for (prev_trip, prev_best_sche, prev_cost, prev_all_sches) in prev_veh_vt[k - 1]:
        if not T_id_sub < {req.id for req in prev_trip} <= T_id_sup:
            continue
        best_sche = None
        min_cost = np.inf
        feasible_sches = []
        if not n_new_pick == 0:
            # remove picked req in trip
            trip = list(prev_trip)
            for req in prev_trip:
                if req.id in new_pick_rids:
                    trip.remove(req)
            trip = tuple(sorted(trip, key=lambda r: r.id))
        else:
            trip = prev_trip
        for sche in prev_all_sches:
            if not n_new_both == 0:
                if not {sche[i][0] for i in range(n_new_both)} == new_both_rids:
                    continue
                else:
                    assert sum([sche[i][1] for i in range(n_new_both)]) == n_new_pick - 1 * n_new_drop
                    del sche[0:n_new_both]
            flag, c, viol = test_constraints_get_cost(veh_params, sche, 0, 0, 0, T)
            if flag:
                feasible_sches.append(sche)
                if c < min_cost:
                    best_sche = copy.deepcopy(sche)
                    min_cost = c
        if best_sche:
            updated_prev_vt_k.append((trip, best_sche, min_cost, feasible_sches))
            T_id = {r.id for r in trip}
            rids_in_sche = {rid for (rid, pod, tnid, ept, ddl) in best_sche}
            assert T_id == rids_in_sche - set(veh.onboard_rids)
            assert T_id <= rids_prev

    assert len([vt[0] for vt in updated_prev_vt_k]) == len(set([vt[0] for vt in updated_prev_vt_k]))
    return updated_prev_vt_k


def clear_up_vt_table():
    global VT_TABLE, PREV_VT_TABLE
    if FAST_COMPUTE:
        PREV_VT_TABLE = VT_TABLE
    VT_TABLE = [[[] for i in range(RIDESHARING_SIZE)] for j in range(FLEET_SIZE)]


def clear_veh_candidate_sches(vehs):
    for veh in vehs:
        veh.candidate_sches.clear()
