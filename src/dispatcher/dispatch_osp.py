"""
optimal batch assignment: computing the optimal schedule pool and then assign them together
"""

from src.dispatcher.ilp_assign import *
from itertools import permutations

FEASIBLE_TRIP_TABLE = [[[] for i in range(VEH_CAPACITY[0] + 4)] for j in range(FLEET_SIZE[0])]
PREV_FEASIBLE_TRIP_TABLE = [[]]


def assign_orders_through_osp(new_received_rids: list[int], reqs: list[Req], vehs: list[Veh], system_time_sec: int,
                              value_func: ValueFunction, is_reoptimization: bool = True):
    t = timer_start()
    # Some general settings.
    #        Always turned on. Only turned off to show that without re-optimization (re-assigning picking orders),
    #        multi-to-one match only outperforms a little than one-to-one match.
    enable_reoptimization = is_reoptimization
    #        A cutoff is set to avoid some potential bugs making the algorithm spends too much time on some dead loop.
    #        30 s is considered as a sufficient large value. If this cutoff time is set too small, it may happens that
    #        there are not enough feasible vehicle_trip_pairs found to support ensure_assigning_orders_that_are_picking.
    cutoff_time_for_a_size_k_trip_search_per_veh_sec = 0.1
    #        Orders that have been assigned vehicles are guaranteed to be served to ensure a good user experience.
    #        The objective of assignment could be further improved if this guarantee is abandoned.
    ensure_ilp_assigning_reqs_that_are_picking = True
    #        Fast_compute only computes combinations between the new requests and the previous ones, rather than
    #        between all known unpicked-up requests, to make the algorithm more efficient. But some bugs exist now
    #        and makes the results a little bit worse when enabling fast_compute.
    enable_fast_compute = False

    # 1. Get the list of considered orders, normally including all picking and pending orders.
    #    If re-assigning picking orders to different vehicles is not enabled, only new_received_orders are considered.
    considered_rids = []
    if enable_reoptimization:
        for req in reqs:
            if req.status == OrderStatus.PICKING or req.status == OrderStatus.PENDING:
                considered_rids.append(req.id)
    else:
        considered_rids = new_received_rids

    if DEBUG_PRINT:
        dispatch_method = "OSP" if enable_reoptimization else "OSP-NR"
        print(f"        -Assigning {len(considered_rids)} orders to vehicles through {dispatch_method}...")

    # 2. Compute all possible vehicle trip pairs, each indicating the orders in the trip can be served by the vehicle.
    if not enable_reoptimization:
        enable_fast_compute = False
    candidate_veh_trip_pairs = \
        compute_candidate_veh_trip_pairs(new_received_rids, considered_rids, reqs, vehs, system_time_sec,
                                         cutoff_time_for_a_size_k_trip_search_per_veh_sec,
                                         enable_reoptimization, enable_fast_compute)

    # 3. Score the candidate vehicle_trip_pairs.
    if not ENABLE_VALUE_FUNCTION:
        score_vt_pairs_with_num_of_orders_and_sche_cost(candidate_veh_trip_pairs, reqs, system_time_sec)
    else:
        score_vt_pairs_with_num_of_orders_and_value_of_post_decision_state(len(new_received_rids), vehs, reqs,
                                                                           candidate_veh_trip_pairs, value_func,
                                                                           system_time_sec, is_reoptimization)

    # 4. Compute the assignment policy, indicating which vehicle to pick which trip.
    selected_veh_trip_pair_indices = ilp_assignment(candidate_veh_trip_pairs, considered_rids, reqs, vehs,
                                                    ensure_ilp_assigning_reqs_that_are_picking)
    # selected_veh_trip_pair_indices = greedy_assignment(candidate_veh_trip_pairs)

    # 000. Convert and store the vehicles' states at current epoch and their post-decision states as an experience.
    if COLLECT_DATA and verify_the_current_epoch_is_in_the_main_study_horizon(system_time_sec):
        value_func.store_vehs_state_to_replay_buffer(len(new_received_rids), vehs,
                                                     candidate_veh_trip_pairs, selected_veh_trip_pair_indices,
                                                     system_time_sec, is_reoptimization)
    # if ENABLE_VALUE_FUNCTION and ONLINE_TRAINING:
    #     value_func.online_batch_learn(len(new_received_rids), vehs,
    #                                   candidate_veh_trip_pairs, selected_veh_trip_pair_indices,
    #                                   system_time_sec, is_reoptimization)

    # 5. Update the assigned vehicles' schedules and the considered orders' statuses.
    for rid in considered_rids:
        reqs[rid].status = OrderStatus.PENDING
    upd_schedule_for_vehicles_in_selected_vt_pairs(candidate_veh_trip_pairs, selected_veh_trip_pair_indices)

    # # 6. Update the schedule of vehicles, of which the assigned (picking) orders are reassigned to other vehicles.
    # #    (This is only needed when using GreedyAssignment.)
    # if enable_reoptimization:
    #     upd_sche_for_vehs_having_reqs_removed(vehs)

    if DEBUG_PRINT:
        num_of_assigned_reqs = 0
        for rid in considered_rids:
            if reqs[rid].status == OrderStatus.PICKING:
                num_of_assigned_reqs += 1
        print(f"            +Assigned orders: {num_of_assigned_reqs} ({timer_end(t)})")


def compute_candidate_veh_trip_pairs(new_received_rids: list[int], considered_rids: list[int],
                                     reqs: list[Req], vehs: list[Veh], system_time_sec: int,
                                     cutoff_time_for_a_size_k_trip_search_per_veh_sec: int,
                                     enable_reoptimization: bool, enable_fast_compute: bool) \
        -> list[[Veh, list[Req], list[(int, int, int, float)], float, float]]:
    t = timer_start()
    if DEBUG_PRINT:
        print("                *Computing feasible vehicle trip pairs...", end=" ")

    initialize_feasible_trip_table(enable_fast_compute)

    # Each veh_req_pair = [veh, trip, sche, cost, score]
    candidate_veh_trip_pairs = []
    for veh in vehs:
        basic_candidate_vt_pair = \
            build_feasible_trip_table_for_one_veh(new_received_rids, considered_rids, reqs, veh, system_time_sec,
                                                  cutoff_time_for_a_size_k_trip_search_per_veh_sec,
                                                  enable_reoptimization, enable_fast_compute)
        # 1. Add the basic schedule of the vehicle, which denotes the "empty assign" option in ILP.
        candidate_veh_trip_pairs.append(basic_candidate_vt_pair)
        # 2. Add all searched candidate vehicle-trip pairs.
        for feasible_trips_size_k in FEASIBLE_TRIP_TABLE[veh.id]:
            for [trip, best_sche, cost, feasible_sches] in feasible_trips_size_k:
                candidate_veh_trip_pairs.append([veh, trip, best_sche, cost, 0.0])

        # 3. Add the current working schedule to double satisfy ensure_ilp_assigning_orders_that_are_picking.
        if enable_reoptimization:
            trip = []
            for rid in veh.picking_rids:
                trip.append(reqs[rid])
            trip.sort(key=lambda r: r.id)
            candidate_veh_trip_pairs.append([veh, trip, copy.copy(veh.sche), compute_sche_cost(veh, veh.sche), 0.0])

    if DEBUG_PRINT:
        print(f"({timer_end(t)})")
    return candidate_veh_trip_pairs


def build_feasible_trip_table_for_one_veh(new_received_rids: list[int], considered_rids: list[int],
                                          reqs: list[Req], veh: Veh, system_time_sec: int,
                                          cutoff_time_for_a_size_k_trip_search_per_veh_sec: int,
                                          enable_reoptimization: bool, enable_fast_compute: bool) \
        -> [Veh, list[Req], list[(int, int, int, float)], float, float]:

    # 0. Set the search list of requests and other parameters added for fast compute. (If fast_compute is enabled.)
    search_rids = considered_rids
    prev_rids_set = None
    n_prev_trips_of_size_k = 0
    if enable_fast_compute:
        prev_rids_set = set(considered_rids) - set(new_received_rids)
        search_rids = new_received_rids

    # 1. Get the basic schedules of the vehicle.
    basic_sches = compute_basic_sches_of_one_veh(veh, system_time_sec, enable_reoptimization)
    basic_candidate_vt_pair = [veh, [], basic_sches[0], compute_sche_cost(veh, basic_sches[0]), 0.0]

    # 2. Compute trips of size 1.
    #      Update previous trips. (If fast_compute is enabled.)
    if enable_fast_compute:
        upd_prev_feasible_trip_table_to_generate_size_k_trips_for_one_veh(prev_rids_set, veh, 1, T)
        n_prev_trips_of_size_k = len(FEASIBLE_TRIP_TABLE[veh.id][0])  # k = 1
    #      Add new trips.
    veh_params = [veh.nid, veh.t_to_nid, veh.load]
    for rid in search_rids:
        req = reqs[rid]
        req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
        if get_duration_from_origin_to_dest(veh.nid, req.onid) + veh.t_to_nid + system_time_sec > req.Clp:
            continue
        best_sche, cost, feasible_sches = compute_schedule(veh_params, basic_sches, req_params, system_time_sec)
        if best_sche:
            FEASIBLE_TRIP_TABLE[veh.id][0].append([[req], best_sche, cost, feasible_sches])

    # 3. Compute trips of size k (k >= 2).
    feasible_trips_of_size_k_minus_1 = FEASIBLE_TRIP_TABLE[veh.id][0]
    while len(feasible_trips_of_size_k_minus_1) != 0:
        search_start_time_datetime = get_time_stamp_datetime()
        n_all_trips_of_size_k_minus_1 = len(feasible_trips_of_size_k_minus_1)
        k = len(feasible_trips_of_size_k_minus_1[0][0]) + 1
        searched_trip_ids_of_size_k = []
        feasible_trip_ids_of_size_k_minus_1 = \
            [[r.id for r in trip_info[0]] for trip_info in feasible_trips_of_size_k_minus_1]
        #      Update previous trips. (If fast_compute is enabled.)
        if enable_fast_compute:
            n_prev_trips_of_size_k_minus_1 = n_prev_trips_of_size_k
            upd_prev_feasible_trip_table_to_generate_size_k_trips_for_one_veh(prev_rids_set, veh, k, system_time_sec)
            n_prev_trips_of_size_k = len(FEASIBLE_TRIP_TABLE[veh.id][k - 1])
        else:
            n_prev_trips_of_size_k_minus_1 = 0
        #       Add new trips
        for i in range(0, n_all_trips_of_size_k_minus_1 - 1):
            trip1 = feasible_trips_of_size_k_minus_1[i][0]
            for j in range(max(i + 1, n_prev_trips_of_size_k_minus_1), n_all_trips_of_size_k_minus_1):
                trip2 = feasible_trips_of_size_k_minus_1[j][0]
                new_trip_k = sorted(set(trip1).union(set(trip2)), key=lambda r: r.id)
                if k > 2:
                    new_trip_k_ids = [r.id for r in new_trip_k]
                    # Check if the new trip size is not k.
                    if len(new_trip_k_ids) != k:
                        continue
                    # Check if the trip has been already computed.
                    if new_trip_k_ids in searched_trip_ids_of_size_k:
                        continue
                    # Check if any sub-trip is not feasible.
                    flag_at_least_one_subtrip_is_not_feasible = False
                    for idx in range(k):
                        sub_trip_ids = copy.copy(new_trip_k_ids)
                        sub_trip_ids.pop(idx)
                        assert (len(sub_trip_ids) == k - 1)
                        if sub_trip_ids not in feasible_trip_ids_of_size_k_minus_1:
                            flag_at_least_one_subtrip_is_not_feasible = True
                            break
                    if flag_at_least_one_subtrip_is_not_feasible:
                        continue
                    searched_trip_ids_of_size_k.append(new_trip_k_ids)
                # The schedules of the new trip is computed as inserting an order into vehicle's schedules of serving
                # trip1. This inserted order is included in trip2 and not included in trip1.
                sub_sches = feasible_trips_of_size_k_minus_1[i][3]
                insertion_reqs = list(set(new_trip_k) - set(trip1))
                assert (len(insertion_reqs) == 1)
                insert_req = insertion_reqs[0]
                insert_req_params = [insert_req.id, insert_req.onid, insert_req.dnid, insert_req.Clp, insert_req.Cld]
                best_sche_k, cost, feasible_sches_k = compute_schedule(veh_params, sub_sches, insert_req_params,
                                                                       system_time_sec)
                if best_sche_k:
                    FEASIBLE_TRIP_TABLE[veh.id][k - 1].append([new_trip_k, best_sche_k, cost, feasible_sches_k])
                if get_runtime_sec_from_t_to_now(search_start_time_datetime) \
                        > cutoff_time_for_a_size_k_trip_search_per_veh_sec / 10:
                    break
            if get_runtime_sec_from_t_to_now(search_start_time_datetime) \
                    > cutoff_time_for_a_size_k_trip_search_per_veh_sec:
                break

        feasible_trips_of_size_k_minus_1 = FEASIBLE_TRIP_TABLE[veh.id][k - 1]

    return basic_candidate_vt_pair


# find out which trips from the last interval can be considered feasible size k trips in the current interval
def upd_prev_feasible_trip_table_to_generate_size_k_trips_for_one_veh(prev_rids_set: set[int],
                                                                      veh: Veh, k: int, system_time_sec: int):
    new_pick_rids_set = set(veh.new_picked_rids)
    new_drop_rids_set = set(veh.new_dropped_rids)
    new_both_rids_set = new_pick_rids_set.union(new_drop_rids_set)
    n_new_pick = len(new_pick_rids_set)
    n_new_drop = len(new_drop_rids_set)
    n_new_both = n_new_pick + n_new_drop

    veh_params = [veh.nid, veh.t_to_nid, veh.load]
    k_prev_table = k + n_new_pick
    if not PREV_FEASIBLE_TRIP_TABLE[veh.id][k - 1]:
        return

    if n_new_pick == 0:
        trip_ids_sub_set = set()
        trip_ids_sup_set = prev_rids_set
    else:
        trip_ids_sub_set = new_pick_rids_set
        trip_ids_sup_set = prev_rids_set.union(new_pick_rids_set)

    for [prev_trip, prev_best_sche, prev_cost, prev_all_sches] in PREV_FEASIBLE_TRIP_TABLE[veh.id][k_prev_table - 1]:
        if not trip_ids_sub_set < {r.id for r in prev_trip} <= trip_ids_sup_set :
            continue
        best_sche_k = None
        min_cost_k = np.inf
        feasible_sches_k = []
        if n_new_pick != 0:
            # remove picked req in trip
            trip_k = copy.copy(prev_trip)
            for req in prev_trip:
                if req.id in new_pick_rids_set:
                    trip_k.remove(req)
        else:
            trip_k = prev_trip
        for sche in prev_all_sches:
            if n_new_both != 0:
                if {sche[i][0] for i in range(n_new_both)} != new_both_rids_set:
                    continue
                else:
                    assert sum([sche[i][1] for i in range(n_new_both)]) == n_new_pick - 1 * n_new_drop
                    del sche[0:n_new_both]
            flag, c, viol = test_constraints_get_cost(veh_params, sche, 0, 0, 0, system_time_sec)
            if flag:
                feasible_sches_k.append(sche)
                if c < min_cost_k:
                    best_sche_k = copy.copy(sche)
                    min_cost_k = c
        if best_sche_k:
            trip_k_ids_set = {r.id for r in trip_k}
            sche_rids_set = {rid for (rid, pod, tnid, ddl) in best_sche_k}
            assert (len(trip_k_ids_set) == k)
            assert (trip_k_ids_set == sche_rids_set - set(veh.onboard_rids) - {-1})
            FEASIBLE_TRIP_TABLE[veh.id][k - 1].append([trip_k, best_sche_k, min_cost_k, feasible_sches_k])


def initialize_feasible_trip_table(enable_fast_compute: bool):
    global FEASIBLE_TRIP_TABLE, PREV_FEASIBLE_TRIP_TABLE
    if enable_fast_compute:
        PREV_FEASIBLE_TRIP_TABLE = FEASIBLE_TRIP_TABLE
    FEASIBLE_TRIP_TABLE = [[[] for i in range(VEH_CAPACITY[0] + 4)] for j in range(FLEET_SIZE[0])]


def compute_basic_sches_of_one_veh(veh: Veh, system_time_sec: int,
                                   enable_reoptimization: bool) -> list[list[(int, int, int, float)]]:
    basic_sches = []

    # If the vehicle is rebalancing, just return its current full schedule to ensure its rebalancing task.
    # If the vehicle is idle, then the basic schedule is an empty schedule.
    if veh.status == VehicleStatus.REBALANCING or veh.status == VehicleStatus.IDLE or not enable_reoptimization:
        basic_sches.append(copy.copy(veh.sche))
        return basic_sches

    # If the vehicle is working, return the sub-schedule only including the drop-off tasks.
    veh_params = [veh.nid, veh.t_to_nid, veh.load]
    basic_sche = []
    for leg in veh.route:
        if leg.rid in veh.onboard_rids:
            basic_sche.append((leg.rid, leg.pod, leg.tnid, leg.ddl))
    assert (len(basic_sche) == veh.load)
    basic_sches.append(basic_sche)

    # Consider permutations of basic_schedule to make sure we search all possible schedules later.
    for sche in permutations(basic_sche):
        sche = list(sche)
        if sche != basic_sche:
            flag, c, viol = test_constraints_get_cost(veh_params, sche, 0, 0, 0, system_time_sec)
            if flag:
                basic_sches.append(sche)
    assert (len(basic_sches) > 0)
    return basic_sches


def upd_sche_for_vehs_having_reqs_removed(vehs: list[Veh]):
    t = timer_start()
    if DEBUG_PRINT:
        num_of_changed_vehs = 0
        for veh in vehs:
            if not veh.sche_has_been_updated_at_current_epoch and veh.status == VehicleStatus.WORKING \
                    and len(veh.sche) != veh.load:
                num_of_changed_vehs += 1
        print(f"                *Updating schedule for {num_of_changed_vehs} changed vehicles...", end=" ")

        for veh in vehs:
            if not veh.sche_has_been_updated_at_current_epoch and veh.status == VehicleStatus.WORKING \
                    and len(veh.sche) != veh.load:
                basic_sche = []
                for (rid, pod, tnid, ddl) in veh.sche:
                    if rid in veh.onboard_rids:
                        basic_sche.append((rid, pod, tnid, ddl))
                veh.build_route(basic_sche)
                veh.sche_has_been_updated_at_current_epoch = True

    if DEBUG_PRINT:
        print(f"({timer_end(t)})")


