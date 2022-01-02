"""
single request batch assignment, where requests cannot be combined in the same interval
"""

from src.dispatcher.ilp_assign import *


def assign_orders_through_sba(new_received_rids: list[int], reqs: list[Req], vehs: list[Veh], T: int):
    t = timer_start()
    if DEBUG_PRINT:
        print(f"        -Assigning {len(new_received_rids)} orders to vehicles through SBA...")

    # 1. Compute all possible veh-req pairs, each indicating that the request can be served by the vehicle.
    candidate_veh_req_pairs = compute_candidate_veh_req_pairs(new_received_rids, reqs, vehs, T)

    # 2. Score the candidate veh-req pairs.
    score_vt_pairs_with_num_of_orders_and_schedule_cost(candidate_veh_req_pairs, reqs)

    # 3. Compute the assignment policy, indicating which vehicle to pick which request.
    selected_veh_req_pair_indices = ilp_assignment(candidate_veh_req_pairs, new_received_rids, reqs, vehs)
    # selected_veh_req_pair_indices = greedy_assignment(feasible_veh_req_pairs)

    # 4. Update the assigned vehicles' schedules and the assigned requests' statuses.
    upd_schedule_for_vehicles_in_selected_vt_pairs(candidate_veh_req_pairs, selected_veh_req_pair_indices)

    if DEBUG_PRINT:
        num_of_assigned_reqs = 0
        for rid in new_received_rids:
            if reqs[rid].status == OrderStatus.PICKING:
                num_of_assigned_reqs += 1
        print(f"            +Assigned orders: {num_of_assigned_reqs} ({timer_end(t)})")


def compute_candidate_veh_req_pairs(new_received_rids: list[int], reqs: list[Req], vehs: list[Veh], T: int) \
        -> list[[Veh, list[Req], list[[int, int, int, float, float]], float]]:
    t = timer_start()
    if DEBUG_PRINT:
        print("                *Computing candidate vehicle order pairs...", end=" ")

    # Each veh_req_pair = [veh, trip, sche, cost, score]
    candidate_veh_req_pairs = []

    # 1. Compute the feasible veh-req pairs for new received requests.
    for rid in new_received_rids:
        req = reqs[rid]
        req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
        for veh in vehs:
            if get_duration_from_origin_to_dest(veh.nid, req.onid) + veh.t_to_nid + T > req.Clp:
                continue
            veh_params = [veh.nid, veh.t_to_nid, veh.load]
            sub_sche = veh.sche
            best_sche, cost, feasible_sches = compute_schedule(veh_params, [sub_sche], req_params, T)
            if best_sche:
                candidate_veh_req_pairs.append([veh, [req], best_sche, cost, 0.0])

    # candidate_veh_req_pairs = search_from_order(new_received_rids, reqs, vehs, T)

    # 2. Add the basic schedule of each vehicle, which denotes the "empty assign" option in ILP.
    for veh in vehs:
        candidate_veh_req_pairs.append([veh, [], copy.copy(veh.sche), compute_sche_cost(veh, veh.sche), 0.0])

    if DEBUG_PRINT:
        print(f"({timer_end(t)})")

    return candidate_veh_req_pairs