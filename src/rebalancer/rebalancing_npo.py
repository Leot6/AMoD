"""
rebalancing algorithm for the AMoD system
"""

from src.dispatcher.ilp_assign import *


def reposition_idle_vehicles_to_nearest_pending_orders(reqs: list[Req], vehs: list[Veh], system_time_sec: int,
                                                       num_of_new_reqs: int, value_func: ValueFunction):
    t = timer_start()

    # 1. Get a list of the unassigned orders.
    pending_rids = []
    for req in reqs:
        if req.status == OrderStatus.PENDING:
            pending_rids.append(req.id)

    if DEBUG_PRINT:
        num_of_idle_vehs = 0
        for veh in vehs:
            if veh.status == VehicleStatus.IDLE:
                num_of_idle_vehs += 1
        print(f"        -Repositioning {num_of_idle_vehs} idle vehicles to "
              f"{len(pending_rids)} locations through NPO...")

    # 2. Compute all rebalancing candidates.
    rebl_veh_req_pairs = []
    for rid in pending_rids:
        req = reqs[rid]
        for veh in vehs:
            if veh.status != VehicleStatus.IDLE:
                continue
            rebl_dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
            detour_sec = 240  # A hyper parameter and 240 is probably not the best option.
            #  A rebalancing vehicle is allowed to pick up new orders
            #  if it can still visit the reposition waypoint with a small detour.
            rebl_sche = [(-1, 0, req.onid, system_time_sec + rebl_dt + detour_sec)]
            rebl_veh_req_pairs.append([veh, [req], rebl_sche, rebl_dt, -rebl_dt])

    # # 000. Score the rebalancing task using value functions.
    # if len(rebl_veh_req_pairs) > 1:
    #     expected_values = value_func.compute_expected_values_for_veh_trip_pairs(num_of_new_reqs, vehs,
    #                                                                             rebl_veh_req_pairs, system_time_sec)
    #     for idx, vr_pair in enumerate(rebl_veh_req_pairs):
    #         vr_pair[4] = expected_values[idx]

    # 3. Select suitable rebalancing candidates. Greedily from the one with the shortest travel time.
    rebl_veh_req_pairs.sort(key=lambda e: -e[4])
    selected_vids = []
    selected_rids = []
    for [veh, [req], sche, cost, score] in rebl_veh_req_pairs:
        # Check if the vehicle has been selected to do a rebalancing task.
        if veh.id in selected_vids:
            continue
        # Check if the visiting point in the current rebalancing task has been visited.
        if req.id in selected_rids:
            continue
        selected_vids.append(veh.id)
        selected_rids.append(req.id)

        # 4. Push the rebalancing task to the assigned vehicle.
        veh.build_route(sche)

    if DEBUG_PRINT:
        print(f"            +Rebalancing vehicles: {len(selected_vids)} ({timer_end(t)})")

