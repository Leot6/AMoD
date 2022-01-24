"""
compute all feasible schedules for a given vehicle v and a trip T.
"""
import copy

from src.simulator.request import Req
from src.simulator.vehicle import Veh
from src.simulator.route_functions import *
from src.value_function.value_function import ValueFunction


# (schedules of trip T of size k are computed based on schedules of its subtrip of size k-1)
def compute_schedule(veh_params: [int, float, int], sub_sches: list[list[(int, int, int, float)]],
                     req_params: [int, int, int, float, float],
                     system_time_sec: int) -> (list, float, list[list[(int, int, int, float)]]):
    # veh_params = [veh.nid, veh.t_to_nid, veh.load]
    # req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
    feasible_sches = []
    best_sche = None
    min_cost = np.inf
    viol = None
    for sub_sche in sub_sches:
        l = len(sub_sche)
        # insert the req's pick-up point
        for i in range(l + 1):
            # insert the req's drop-off point
            for j in range(i + 1, l + 2):
                new_sche, new_sche_cost, viol = insert_req_into_sche(veh_params, sub_sche, req_params,
                                                                     i, j, system_time_sec)
                if new_sche:
                    if new_sche_cost < min_cost:
                        best_sche = new_sche
                        min_cost = new_sche_cost
                        feasible_sches.insert(0, new_sche)
                    else:
                        feasible_sches.append(new_sche)
                # # always return the first found feasible schedule (will speed up the computation)
                # if DISPATCHER == 'SBA' and best_sche:
                #     assert len(feasible_sches) == 1
                #     return best_sche, min_cost, feasible_sches
                if viol > 0:
                    break
            if viol == 3:
                break
    return best_sche, min_cost, feasible_sches


# Try to insert "req" into veh's "sub_sche", return the new_sche if it is feasible, else return "new_sche = None".
def insert_req_into_sche(veh_params: [int, float, int], sub_sche: list[(int, int, int, float)],
                         req_params: [int, int, int, float, float], idx_p: int, idx_d: int,
                         system_time_sec: int) -> (list, float, int):
    [rid, r_onid, r_dnid, r_Clp, r_Cld] = req_params
    new_sche = None
    new_sche_cost = np.inf

    sub_sche.insert(idx_p, (rid, 1, r_onid, r_Clp))
    sub_sche.insert(idx_d, (rid, -1, r_dnid, r_Cld))
    flag, c, viol = test_constraints_get_cost(veh_params, sub_sche, rid, idx_p, idx_d, system_time_sec)

    if flag:
        new_sche = copy.copy(sub_sche)
        new_sche_cost = c
    sub_sche.pop(idx_d)
    sub_sche.pop(idx_p)
    return new_sche, new_sche_cost, viol


# Test if a schedule can satisfy all constraints, return the cost (if yes) or the type of violation (if no).
# The returned cost is the sche time, which is the same as the output of the following function "compute_sche_cost".
def test_constraints_get_cost(veh_params: [int, float, int], sche: list[(int, int, int, float)],
                              new_rid: int, idx_p: int, idx_d: int, system_time_sec: int) -> (bool, float, int):
    [nid, accumulated_time_sec, n] = veh_params
    # test the capacity constraint during the whole schedule
    for (rid, pod, tnid, ddl) in sche:
        n += pod
        if n > VEH_CAPACITY[0]:
            return False, np.inf, 1  # over capacity

    # test the pick-up and drop-off time constraint for each passenger on board
    for idx, (rid, pod, tnid, ddl) in enumerate(sche):
        accumulated_time_sec += get_duration_from_origin_to_dest(nid, tnid)

        variance = 0
        # if IS_STOCHASTIC_SCHEDULE:
        #     variance += get_variance_from_origin_to_dest(nid, tnid)

        if idx >= idx_p and system_time_sec + accumulated_time_sec + 1 * variance > ddl:
            if rid == new_rid:
                # pod == -1 means a new pick-up insertion is needed, since later drop-off brings longer travel time
                # pod == 1 means no more feasible schedules is available, since later pick-up brings longer wait time
                return False, np.inf, 2 if pod == -1 else 3
            if idx < idx_d:
                # idx<=new_req_drop_idx means the violation is caused by the pick-up of req,
                # since the violation happens before the drop-off of req
                return False, np.inf, 4
            return False, np.inf, 0
        nid = tnid
    return True, accumulated_time_sec, -1


def compute_sche_cost(veh: Veh, sche: list[(int, int, int, float)]) -> float:
    nid = veh.nid
    accumulated_time_sec = veh.t_to_nid
    for (rid, pod, tnid, ddl) in sche:
        accumulated_time_sec += get_duration_from_origin_to_dest(nid, tnid)
        nid = tnid
    return accumulated_time_sec


def upd_schedule_for_vehicles_in_selected_vt_pairs(candidate_veh_trip_pairs: list,
                                                   selected_veh_trip_pair_indices: list[int]):
    t = timer_start()

    for idx in selected_veh_trip_pair_indices:
        [veh, trip, sche, cost, score] = candidate_veh_trip_pairs[idx]
        for req in trip:
            req.status = OrderStatus.PICKING
        veh.build_route(sche)
        veh.sche_has_been_updated_at_current_epoch = True

    if DEBUG_PRINT:
        print(f"                *Executing assignment with {len(selected_veh_trip_pair_indices)} pairs... "
              f"({timer_end(t)})")


def compute_sche_delay(veh: Veh, sche: list[(int, int, int, float)], reqs: list[Req], system_time_sec: int) -> float:
    nid = veh.nid
    accumulated_time_sec = veh.t_to_nid
    delay_sec = 0.0
    wait_sec = 0.0
    for (rid, pod, tnid, ddl) in sche:
        accumulated_time_sec += get_duration_from_origin_to_dest(nid, tnid)
        wait_sec += (system_time_sec + accumulated_time_sec - reqs[rid].Tr) if pod == 1 else 0
        delay_sec += (system_time_sec + accumulated_time_sec - reqs[rid].Tr - reqs[rid].Ts) if pod == -1 else 0
        nid = tnid
    total_delay = wait_sec * 1.0 + delay_sec
    return delay_sec


def score_vt_pairs_with_num_of_orders_and_sche_cost(veh_trip_pairs: list, reqs: list[Req], system_time_sec: int):
    # 1. Get the coefficients for NumOfOrders and ScheduleCost.
    max_sche_cost = 1
    for vt_pair in veh_trip_pairs:
        [veh, trip, sche, cost, score] = vt_pair
        vt_pair[3] = compute_sche_delay(veh, sche, reqs, system_time_sec)
        if vt_pair[3] > max_sche_cost:
            max_sche_cost = vt_pair[3]
    max_sche_cost = int(max_sche_cost)
    num_length = 0
    while max_sche_cost:
        max_sche_cost //= 10
        num_length += 1
    reward_for_serving_a_req = pow(10, num_length)

    # # 2. Score the vt_pairs with NumOfOrders and ScheduleCost.
    # # (The objective is to maximize the number of assigned orders and minimize the schedule cost (travel delay).)
    # for vt_pair in veh_trip_pairs:
    #     vt_pair[4] = reward_for_serving_a_req * len(vt_pair[1]) - vt_pair[3]

    for vt_pair in veh_trip_pairs:
        vt_pair[4] = len(vt_pair[1])


# ("is_reoptimization" only influences the calculation of rewards in "compute_post_decision_state".)
def score_vt_pairs_with_num_of_orders_and_value_of_post_decision_state(num_of_new_reqs: int,
                                                                       vehs: list[Veh],
                                                                       reqs: list[Req],
                                                                       veh_trip_pairs: list,
                                                                       value_func: ValueFunction,
                                                                       system_time_sec: int,
                                                                       is_reoptimization: bool = False):
    expected_vt_scores = value_func.compute_expected_values_for_veh_trip_pairs(num_of_new_reqs, vehs,
                                                                               copy.deepcopy(veh_trip_pairs),
                                                                               system_time_sec, is_reoptimization)
    for idx, vt_pair in enumerate(veh_trip_pairs):
        vt_pair[4] = expected_vt_scores[idx]

    # # 1. Get the coefficients for NumOfOrders and ScheduleCost.
    # max_sche_cost = 1
    # for vt_pair in veh_trip_pairs:
    #     [veh, trip, sche, cost, score] = vt_pair
    #     vt_pair[3] = compute_sche_delay(veh, sche, reqs, system_time_sec)
    #     if vt_pair[3] > max_sche_cost:
    #         max_sche_cost = vt_pair[3]
    # max_sche_cost = int(max_sche_cost)
    # num_length = 0
    # while max_sche_cost:
    #     max_sche_cost //= 10
    #     num_length += 1
    # reward_for_serving_a_req = pow(10, num_length)
    #
    # if ONLINE_TRAINING:
    #     # 2. Score the vt_pairs with NumOfOrders and ScheduleCost.
    #     for idx, vt_pair in enumerate(veh_trip_pairs):
    #         vt_pair[4] = reward_for_serving_a_req * expected_vt_scores[idx] - vt_pair[3]
    # else:
    #     # 2. Score the vt_pairs with NumOfOrders and ScheduleCost.
    #     for idx, vt_pair in enumerate(veh_trip_pairs):
    #         vt_pair[4] = expected_vt_scores[idx]

