"""

"""

import time
from tqdm import tqdm

from lib.simulator.config import FLEET_SIZE, RIDESHARING_SIZE
from lib.routing.routing_server import get_duration_from_origin_to_dest
from lib.dispatcher.rtv.rtv_schedule import compute_schedule

# feasible trips (trip, best_schedule, min_cost, feasible_schedules)
RTV_GRAPH = None
CUTOFF_RTV = 0.2
RTV_SIZE = 1200
RV_SIZE = 30 if CUTOFF_RTV == 0.2 else RTV_SIZE

# avg_num_of_sche_searched: # the number of possible schedules algorithm considers when finding the optimal schedule
# num_of_trips: # the number of different size trips algorithm considers
num_of_trip_searched = [0] * RIDESHARING_SIZE
avg_num_of_sche_searched = [0] * RIDESHARING_SIZE
show_counting = False


# build rtv graph for each veh, respectively
def search_feasible_trips(vehs, reqs_pool, T):
    clear_up_rtv_graph()

    reqs_pool.sort(key=lambda r: r.id)
    num_rids_remain = len(reqs_pool) - RTV_SIZE
    if num_rids_remain > 0:
        rids_remain = [req.id for req in reqs_pool[:num_rids_remain]]
        reqs_pool_rtv = reqs_pool[num_rids_remain:]
    else:
        rids_remain = []
        reqs_pool_rtv = reqs_pool

    # trips of size 1
    build_rv_graph(vehs, reqs_pool_rtv, rids_remain, T)
    # trips of size k (k >= 2)
    build_rtv_graph(vehs, reqs_pool_rtv, rids_remain, T)

    veh_trip_edges = []
    clear_veh_candidate_sches(vehs)
    for veh in vehs:
        for veh_rtv_k in RTV_GRAPH[veh.id]:
            for (trip, best_sche, cost) in veh_rtv_k:
                veh_trip_edges.append((veh, trip, best_sche, cost))
                # veh.candidate_sches.append(best_sche)
                veh.candidate_sches_rtv.append(best_sche)
    return veh_trip_edges


def build_rv_graph(vehs, reqs_pool, rids_remain, T):
    # for req in tqdm(reqs_pool, desc=f'RV graph ({RTV_SIZE}/{len(reqs_pool + rids_remain)} reqs)', leave=False):
    for req in reqs_pool:
        trip = tuple([req])
        rv_links = []
        # for veh in tqdm(vehs, desc=f'req {req.id} (size 1)', leave=False):
        for veh in vehs:
            if get_duration_from_origin_to_dest(veh.nid, req.onid) + veh.t_to_nid + T > req.Clp:
                continue
            veh_params = [veh.nid, veh.t_to_nid, veh.n]
            sub_sche = restore_basic_sub_sche(veh, rids_remain)
            best_sche, cost, num_of_sche_searched = compute_schedule(veh_params, sub_sche, trip, T)
            # print(f'sche: {best_sche}/{best_sche2}, cost: {cost}/{cost2}, n_s_c: {n_s_c}/{n_s_c2}')
            if best_sche:
                rv_links.append((veh.id, tuple([req]), best_sche, cost))
                # debug code
                assert {req.id} == \
                       {rid for (rid, pod, tnid, ept, ddl) in best_sche} - set(veh.onboard_rids + rids_remain)
                assert {req.id} <= {r.id for r in reqs_pool}
        rv_links = sorted(rv_links, key=lambda l: l[3])
        for (vid, trip, best_sche, cost) in rv_links[:RV_SIZE]:
            RTV_GRAPH[vid][0].append((trip, best_sche, cost))


# search all feasible ride-sharing trips for each vehicle, respectively, incrementally from the trip size of two
def build_rtv_graph(vehs, reqs_pool, rids_remain, T):
    # for veh in tqdm(vehs, desc=f'RTV graph ({RTV_SIZE}/{len(reqs_pool + rids_remain)} reqs)', leave=False):
    for veh in vehs:
        veh_params = [veh.nid, veh.t_to_nid, veh.n]
        veh_rtv = RTV_GRAPH[veh.id]
        start_time = time.time()
        for k in range(2, RIDESHARING_SIZE + 1):
            n_all_trips_k_1 = len(veh_rtv[k - 2])  # number of all trips of size k-1
            # for i in tqdm(range(0, n_all_trips_k_1), desc=f'veh {veh.id} (size {k})', leave=False):
            for i in range(0, n_all_trips_k_1):
                trip1 = veh_rtv[k - 2][i][0]  # a trip of size k-1
                for j in range(i + 1, n_all_trips_k_1):
                    trip2 = veh_rtv[k - 2][j][0]  # another trip of size k-1 (different from trip1)
                    trip_k = tuple(sorted(set(trip1).union(set(trip2)), key=lambda r: r.id))
                    if k > 2:
                        # check trip size is k
                        if len(trip_k) != k:
                            continue
                        # check trip is already computed
                        all_found_trip_k = [edge[0] for edge in veh_rtv[k - 1]]
                        if trip_k in all_found_trip_k:
                            continue
                        # check all subtrips are feasible
                        subtrips_check = True
                        for req in trip_k:
                            one_subtrip_of_trip_k = tuple(sorted((set(trip_k) - set([req])), key=lambda r: r.id))
                            all_found_trip_k_1 = [vt[0] for vt in veh_rtv[k - 2]]
                            if one_subtrip_of_trip_k not in all_found_trip_k_1:
                                subtrips_check = False
                                break
                        if not subtrips_check:
                            continue

                    sub_sche = restore_basic_sub_sche(veh, rids_remain)
                    best_sche, min_cost, num_of_sche_searched = compute_schedule(veh_params, sub_sche, trip_k, T)

                    if show_counting:
                        k_c = k + len(veh.onboard_rids)
                        # count the number of feasible schedules algorithm considers
                        num_of_trip_searched[k_c - 2] += 1
                        avg_num_of_sche_searched[k_c - 2] += ((num_of_sche_searched - avg_num_of_sche_searched[k_c - 2])
                                                            / num_of_trip_searched[k_c - 2])
                        avg_num_of_sche_searched[k_c - 2] = round(avg_num_of_sche_searched[k_c - 2], 2)
                        print('mean counting schedules', avg_num_of_sche_searched)
                        print('count trips', num_of_trip_searched)

                    if best_sche:
                        veh_rtv[k - 1].append((trip_k, best_sche, min_cost))
                        # debug code
                        rids_in_trip = {r.id for r in trip_k}
                        rids_in_sche = \
                            {rid for (rid, pod, tnid, ept, ddl) in best_sche} - set(veh.onboard_rids + rids_remain)
                        assert rids_in_trip == rids_in_sche
                        assert {req.id for req in trip_k} <= {req.id for req in reqs_pool}

                    # threshold cutoff
                    current_time = time.time()
                    if current_time - start_time > CUTOFF_RTV:
                        # print(f'time using 1 {current_time - start_time}, {i, j}')
                        # print('veh', veh.id, 'cutoff size', k, 'trip, second search')
                        break

                # threshold cutoff
                current_time = time.time()
                if current_time - start_time > CUTOFF_RTV:
                    # print(f'time using 2 {current_time - start_time}')
                    # print('veh', veh.id, 'cutoff size', k, 'trip, first search')
                    break

            if len(veh_rtv[k - 1]) == 0:
                break


def restore_basic_sub_sche(veh, rids_remain):
    sub_sche = []
    if not veh.idle:
        for leg in veh.route:
            if leg.rid in veh.onboard_rids or leg.rid in rids_remain:
                sub_sche.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
    return sub_sche


def clear_up_rtv_graph():
    global RTV_GRAPH
    RTV_GRAPH = [[[] for i in range(RIDESHARING_SIZE)] for j in range(FLEET_SIZE)]


def change_rtv_graph_param(cut_off, rtv_size, rv_size):
    global CUTOFF_RTV
    global RTV_SIZE
    global RV_SIZE
    CUTOFF_RTV = cut_off
    RTV_SIZE = rtv_size
    RV_SIZE = rv_size


def clear_veh_candidate_sches(vehs):
    for veh in vehs:
        # veh.candidate_sches.clear()
        veh.candidate_sches_rtv.clear()
