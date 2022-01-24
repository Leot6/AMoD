from src.simulator.vehicle import Veh
from src.simulator.route_functions import *


class Experience(object):
    def __init__(self,
                 normalized_system_time_at_current_state: float,
                 vehs_visiting_node_ids_at_current_state: list[list[int]],
                 vehs_normalized_remaining_delays_at_current_state: list[list[float]],
                 vehs_num_of_visiting_nodes_at_current_state: list[int],
                 vehs_normalized_num_of_nearby_vehs_at_current_state: list[float],
                 normalized_num_of_new_reqs_at_current_state: float,
                 normalized_system_time_at_next_state: float,
                 vehs_visiting_node_ids_at_next_state: list[list[int]],
                 vehs_normalized_remaining_delays_at_next_state: list[list[float]],
                 vehs_num_of_visiting_nodes_at_next_state: list[int],
                 vehs_reward_for_transition_from_current_to_next_state: list[int],
                 assumed_vehs_normalized_num_of_nearby_vehs_at_next_state: list[float]):
        """
        Example of an experience (number_of_vehicles = 3, vehicle_capacity = 1, number_of_epochs = 100):
        -------
        normalized_system_time_at_current_state = 0.25
        vehs_visiting_node_ids_at_current_state =  [[1, 2, 3],
                                                    [4, 5, 0],
                                                    [7, 0, 0]]
        vehs_normalized_remaining_delays_at_current_state = [[1, 0.2, 0.3],
                                                             [1, 0.1, -1],
                                                             [1, -1, -1]]
        vehs_num_of_visiting_nodes_at_current_state = [3, 2, 1]

        vehs_normalized_num_of_nearby_vehs_at_current_state = [0.33, 0.67, 0.67]
        normalized_num_of_new_reqs_at_current_state = 2/3 = 0.67

        normalized_system_time_at_next_state = 0.26
        vehs_visiting_node_ids_at_next_state =  [[2, 3, 0],
                                                 [5, 9, 10],
                                                 [8, 11, 12]]
        vehs_normalized_remaining_delays_at_next_state = [[1, 0.3, -1],
                                                             [1, 0.2, 0.6],
                                                             [1, 0.1, 0.5]]
        vehs_num_of_visiting_nodes_at_next_state = [2, 3, 3]

        vehs_reward_for_transition_from_current_to_next_state = [0, 1, 1]

        vehs_normalized_num_of_nearby_vehs_at_current_state = [0.33, 0.33, 0.33]

        """

        # Deterministic knowledge about now.
        self.normalized_system_time_at_current_state = normalized_system_time_at_current_state
        self.vehs_visiting_node_ids_at_current_state = vehs_visiting_node_ids_at_current_state
        self.vehs_normalized_remaining_delays_at_current_state = vehs_normalized_remaining_delays_at_current_state
        self.vehs_num_of_visiting_nodes_at_current_state = vehs_num_of_visiting_nodes_at_current_state

        # Exogenous information about now. (Stochastic knowledge, which cannot be known at the previous state.)
        self.vehs_normalized_num_of_nearby_vehs_at_current_state = vehs_normalized_num_of_nearby_vehs_at_current_state
        self.normalized_num_of_new_reqs_at_current_state = normalized_num_of_new_reqs_at_current_state

        # Deterministic knowledge about the future. (They are derived from the current state and the action.)
        self.normalized_system_time_at_next_state = normalized_system_time_at_next_state
        self.vehs_visiting_node_ids_at_next_state = vehs_visiting_node_ids_at_next_state
        self.vehs_normalized_remaining_delays_at_next_state = vehs_normalized_remaining_delays_at_next_state
        self.vehs_num_of_visiting_nodes_at_next_state = vehs_num_of_visiting_nodes_at_next_state

        # Reward (obtained from the environment) for the transition from the current state to the next state.
        self.vehs_reward_for_transition_from_current_to_next_state = \
            vehs_reward_for_transition_from_current_to_next_state

        # Exogenous information about the future (We approximate them using the current known information,
        # under the assumption that, at a macro level, these do not change significantly in a single epoch.).
        self.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state = \
            assumed_vehs_normalized_num_of_nearby_vehs_at_next_state
        self.assumed_normalized_num_of_new_reqs_at_next_state = normalized_num_of_new_reqs_at_current_state

        # print(f"\n\n[DEBUG] normalized_system_time_at_current_state "
        #       f"{normalized_system_time_at_current_state}")
        # print(f"[DEBUG] vehs_visiting_node_ids_at_current_state "
        #       f"{vehs_visiting_node_ids_at_current_state[0]}")
        # print(f"[DEBUG] vehs_normalized_remaining_delays_at_current_state "
        #       f"{[round(e, 3) for e in vehs_normalized_remaining_delays_at_current_state[0]]}")
        # print(f"[DEBUG] vehs_num_of_visiting_nodes_at_current_state "
        #       f"{vehs_num_of_visiting_nodes_at_current_state[0]}")
        #
        # print(f"[DEBUG] vehs_normalized_num_of_nearby_vehs_at_current_state "
        #       f"{vehs_normalized_num_of_nearby_vehs_at_current_state[0]}")
        # print(f"[DEBUG] normalized_num_of_new_reqs_at_current_state "
        #       f"{normalized_num_of_new_reqs_at_current_state}")
        #
        # print(f"[DEBUG] normalized_system_time_at_next_state "
        #       f"{normalized_system_time_at_next_state}")
        # print(f"[DEBUG] vehs_visiting_node_ids_at_next_state "
        #       f"{vehs_visiting_node_ids_at_next_state[0]}")
        # print(f"[DEBUG] vehs_normalized_remaining_delays_at_next_state "
        #       f"{[round(e, 3) for e in vehs_normalized_remaining_delays_at_next_state[0]]}")
        # print(f"[DEBUG] vehs_num_of_visiting_nodes_at_next_state "
        #       f"{vehs_num_of_visiting_nodes_at_next_state[0]}")
        #
        # print(f"[DEBUG] vehs_reward_for_transition_from_current_to_next_state "
        #       f"{vehs_reward_for_transition_from_current_to_next_state[0]}")


# Store all vehicles' states info and rewards for offline learning.
# ("is_reoptimization" only influences the calculation of rewards in "compute_post_decision_state".)
def store_vehs_current_state_and_post_decision_state_as_an_experience(num_of_new_reqs: int,
                                                                      vehs: list[Veh],
                                                                      candidate_veh_trip_pairs: list,
                                                                      selected_veh_trip_pair_indices: list[int],
                                                                      system_time_sec: int,
                                                                      is_reoptimization: bool = False) -> Experience:
    t = timer_start()
    if DEBUG_PRINT:
        print("                *Storing vehicles' states and post-decision states...", end=" ")

    # 1. Add each vehicle's current state.
    #    1.1. Deterministic knowledge about now.
    normalized_system_time_at_current_state = \
        (system_time_sec - WARMUP_DURATION_MIN * 60) / (SIMULATION_DURATION_MIN * 60)
    vehs_visiting_node_ids_at_current_state = [[] for i in range(len(vehs))]
    vehs_normalized_remaining_delays_at_current_state = [[] for i in range(len(vehs))]
    vehs_num_of_visiting_nodes_at_current_state = [1 for i in range(len(vehs))]
    for veh in vehs:
        [vehs_visiting_node_ids_at_current_state[veh.id], vehs_normalized_remaining_delays_at_current_state[veh.id],
         vehs_num_of_visiting_nodes_at_current_state[veh.id]] = compute_current_sche_state_of_a_veh(veh.nid,
                                                                                                    veh.t_to_nid,
                                                                                                    veh.sche,
                                                                                                    system_time_sec)
    #    1.2. Exogenous information about now.
    vehs_normalized_num_of_nearby_vehs_at_current_state = \
        compute_normalized_num_of_nearby_vehs_for_all_vehs_with_given_node_ids([veh.nid for veh in vehs])
    normalized_num_of_new_reqs_at_current_state = num_of_new_reqs / FLEET_SIZE[0]

    # 2. Add each vehicle's post-decision state and its reward for transition from the current to the next state.
    selected_veh_trip_pairs = [None] * len(vehs)
    assert len(vehs) == len(selected_veh_trip_pairs)
    for i, j in enumerate(selected_veh_trip_pair_indices):
        selected_veh_trip_pairs[i] = candidate_veh_trip_pairs[j]
    selected_veh_trip_pairs.sort(key=lambda e: e[0].id)
    [normalized_system_time_at_next_state, vehs_visiting_node_ids_at_next_state,
     vehs_normalized_remaining_delays_at_next_state, vehs_num_of_visiting_nodes_at_next_state,
     vehs_reward_for_transition_from_current_to_next_state,
     assumed_vehs_normalized_num_of_nearby_vehs_at_next_state] = \
        compute_post_decision_state_for_vt_pairs(selected_veh_trip_pairs, vehs, system_time_sec, is_reoptimization)

    new_experience = Experience(normalized_system_time_at_current_state,
                                vehs_visiting_node_ids_at_current_state,
                                vehs_normalized_remaining_delays_at_current_state,
                                vehs_num_of_visiting_nodes_at_current_state,
                                vehs_normalized_num_of_nearby_vehs_at_current_state,
                                normalized_num_of_new_reqs_at_current_state,
                                normalized_system_time_at_next_state,
                                vehs_visiting_node_ids_at_next_state,
                                vehs_normalized_remaining_delays_at_next_state,
                                vehs_num_of_visiting_nodes_at_next_state,
                                vehs_reward_for_transition_from_current_to_next_state,
                                assumed_vehs_normalized_num_of_nearby_vehs_at_next_state)

    if DEBUG_PRINT:
        print(f"({timer_end(t)})")
    return new_experience


def compute_current_sche_state_of_a_veh(veh_nid: int, veh_t_to_nid: float, sche: list[(int, int, int, float)],
                                        system_time_sec: int) -> [list[int], list[float], int]:
    extra_length_for_long_sche = 6
    # A 2-seat vehicle might serve 3 orders in one trip.
    # e.g. [veh_pos, pick_order_1, pick_order_2, drop_order_1, pick_order_3, drop_order_2, drop_order_3],
    visiting_node_ids = [0] * (1 + VEH_CAPACITY[0] * 2 + extra_length_for_long_sche)
    normalized_remaining_delays_at_visiting_nodes = [-1] * (1 + VEH_CAPACITY[0] * 2 + extra_length_for_long_sche)

    visiting_node_ids[0] = veh_nid
    normalized_remaining_delays_at_visiting_nodes[0] = 1
    num_of_visiting_nodes = 1 + len(sche)
    accumulated_time_sec = veh_t_to_nid

    if len(sche) + 1 > len(visiting_node_ids):
        print(f"[DEBUG-T] sche len {len(sche)}, sche {sche}")

    for idx, (rid, pod, tnid, ddl) in enumerate(sche):
        visiting_node_ids[idx + 1] = tnid
        accumulated_time_sec += get_duration_from_origin_to_dest(visiting_node_ids[idx], tnid)
        normalized_remaining_delays_at_visiting_nodes[idx + 1] = \
            (ddl - system_time_sec - accumulated_time_sec) / (MAX_PICKUP_WAIT_TIME_MIN[0] * 60 * 2)
        if not (normalized_remaining_delays_at_visiting_nodes[idx + 1]) >= 0:
            assert np.isclose(system_time_sec + accumulated_time_sec, ddl)
            normalized_remaining_delays_at_visiting_nodes[idx + 1] = 0

    return [visiting_node_ids, normalized_remaining_delays_at_visiting_nodes, num_of_visiting_nodes]


# Compute the number of vehicles that will arrive in the MAX_PICKUP_DELAY area of each vehicle's current loc.
def compute_normalized_num_of_nearby_vehs_for_all_vehs_with_given_node_ids(vehs_nid: list[int]) -> list[float]:
    # Term "vehs_nid" is a list of vehicle's position node id, sorted by vehicle id (e.g., vehs_nid[0] is nid of veh 0).
    # The number of nearby vehicles is initialized as 1 to include the vehicle itself in the calculation.
    vehs_normalized_num_of_nearby_vehs = [1 for i in range(len(vehs_nid))]
    for i in range(len(vehs_nid)):
        veh1_nid = vehs_nid[i]
        for j in range(i + 1, len(vehs_nid)):
            veh2_nid = vehs_nid[j]
            if get_duration_from_origin_to_dest(veh1_nid, veh2_nid) < MAX_PICKUP_WAIT_TIME_MIN[0] * 60 \
                    or get_duration_from_origin_to_dest(veh2_nid, veh1_nid) < MAX_PICKUP_WAIT_TIME_MIN[0] * 60:
                vehs_normalized_num_of_nearby_vehs[i] += 1
                vehs_normalized_num_of_nearby_vehs[j] += 1
        vehs_normalized_num_of_nearby_vehs[i] = \
            vehs_normalized_num_of_nearby_vehs[i] / FLEET_SIZE[0]
    return vehs_normalized_num_of_nearby_vehs


# Compute the vehicle's post-decision state (and the reward) resulting from each vehicle-trip pair. That is
# what the vehicle's state will be at the next epoch if the dispatcher selects a vehicle-trip pair for assignment.
# ("is_reoptimization" only influences the calculation of rewards.)
def compute_post_decision_state_for_vt_pairs(veh_trip_pairs: list, vehs: list[Veh], system_time_sec: int,
                                             is_reoptimization: bool) -> [float, list[list[int]],
                                                                          list[list[float]], list[int],
                                                                          list[int], list[float]]:
    # Deterministic knowledge about the future. (They are derived from the current state and the action.)
    normalized_system_time_at_next_state = \
        (system_time_sec + CYCLE_S[0] - WARMUP_DURATION_MIN * 60) / (SIMULATION_DURATION_MIN * 60)
    vt_pairs_visiting_node_ids_at_next_state = [[] for i in range(len(veh_trip_pairs))]
    vt_pairs_normalized_remaining_delays_at_next_state = [[] for i in range(len(veh_trip_pairs))]
    vt_pairs_num_of_visiting_nodes_at_next_state = [1 for i in range(len(veh_trip_pairs))]
    # Reward (obtained from the environment) for the transition from the current state to the next state.
    vt_pairs_reward_for_transition_from_current_to_next_state = [0 for i in range(len(veh_trip_pairs))]
    # Exogenous information about the future (We approximate them using the current known information)
    assumed_vt_pairs_normalized_num_of_nearby_vehs_at_next_state = [1 for i in range(len(veh_trip_pairs))]

    # (We assume all vehicles follow their current schedules to calculate the num_of_nearby_vehs_at_next_state.)
    assumed_vehs_nid_at_next_state = \
        [update_veh_pos_and_sche_to_next_epoch(veh.nid, veh.t_to_nid, veh.sche)[0] for veh in vehs]
    assumed_vehs_normalized_num_of_nearby_vehs_at_next_state = \
        compute_normalized_num_of_nearby_vehs_for_all_vehs_with_given_node_ids(assumed_vehs_nid_at_next_state)

    for idx, [veh, trip, sche, cost, score] in enumerate(veh_trip_pairs):
        # (Deterministic knowledge)
        [vt_pairs_visiting_node_ids_at_next_state[idx], vt_pairs_normalized_remaining_delays_at_next_state[idx],
         vt_pairs_num_of_visiting_nodes_at_next_state[idx]] = compute_next_sche_state_of_a_veh(veh.nid,
                                                                                               veh.t_to_nid,
                                                                                               sche,
                                                                                               system_time_sec)
        # (Reward)
        if is_reoptimization:
            vt_pairs_reward_for_transition_from_current_to_next_state[idx] = len(trip) - len(veh.picking_rids)
        else:
            vt_pairs_reward_for_transition_from_current_to_next_state[idx] = len(trip)

        # (Exogenous information)
        assumed_vt_pairs_normalized_num_of_nearby_vehs_at_next_state[idx] = \
            assumed_vehs_normalized_num_of_nearby_vehs_at_next_state[veh.id]

    return [normalized_system_time_at_next_state, vt_pairs_visiting_node_ids_at_next_state,
            vt_pairs_normalized_remaining_delays_at_next_state, vt_pairs_num_of_visiting_nodes_at_next_state,
            vt_pairs_reward_for_transition_from_current_to_next_state,
            assumed_vt_pairs_normalized_num_of_nearby_vehs_at_next_state]


# Compute the next schedule state of a vehicle, by updating its position and assigned schedule to the next epoch.
def compute_next_sche_state_of_a_veh(veh_nid: int, veh_t_to_nid: float,
                                     assigned_sche: list[(int, int, int, float)],
                                     system_time_sec: int) -> [list[int], list[float], int]:

    updated_veh_nid, updated_veh_t_to_nid, updated_assigned_sche = \
        update_veh_pos_and_sche_to_next_epoch(veh_nid, veh_t_to_nid, assigned_sche)

    [visiting_node_ids_at_next_epoch, normalized_remaining_delays_at_next_epoch,
     num_of_visiting_nodes_at_next_epoch] = compute_current_sche_state_of_a_veh(updated_veh_nid,
                                                                                updated_veh_t_to_nid,
                                                                                updated_assigned_sche,
                                                                                system_time_sec + CYCLE_S[0])

    return [visiting_node_ids_at_next_epoch, normalized_remaining_delays_at_next_epoch,
            num_of_visiting_nodes_at_next_epoch]


# Compute the vehicle's location (and update the given schedule) at the next epoch,
# if the vehicle is following the given schedule.
def update_veh_pos_and_sche_to_next_epoch(veh_nid: int, veh_t_to_nid: float,
                                          sche: list[(int, int, int, float)]) -> (int, float, list):
    updated_veh_nid = veh_nid
    updated_veh_t_to_nid = 0.0
    sche_start_idx_at_next_epoch = 0
    dT = CYCLE_S[0] - veh_t_to_nid
    if dT <= 0:
        updated_veh_t_to_nid = -dT
    else:
        for (rid, pod, tnid, ddl) in sche:
            leg_duration_sec = get_duration_from_origin_to_dest(updated_veh_nid, tnid)
            if dT > leg_duration_sec:
                dT -= leg_duration_sec
                updated_veh_nid = tnid
                sche_start_idx_at_next_epoch += 1
            else:
                leg_duration_sec, leg_distance_m, leg_segments = build_route_from_origin_to_dest(updated_veh_nid, tnid)
                for [t, d, nid_pair, geo_pair] in leg_segments:
                    assert (updated_veh_nid == nid_pair[0])
                    updated_veh_nid = nid_pair[1]
                    dT -= t
                    if dT <= 0:
                        updated_veh_t_to_nid = -dT
                        break
                break
    updated_sche = sche[sche_start_idx_at_next_epoch:]

    return updated_veh_nid, updated_veh_t_to_nid, updated_sche


def process_exp(exp: Experience):
    x1 = exp.normalized_system_time_at_current_state
    x2 = []
    x3 = []
    x4 = []
    x5 = []
    x6 = exp.normalized_num_of_new_reqs_at_current_state

    x1_ = exp.normalized_system_time_at_next_state
    x2_ = []
    x3_ = []
    x4_ = []
    x7 = []
    x5_ = []

    for idx, reward in enumerate(exp.vehs_reward_for_transition_from_current_to_next_state):
        if reward != 0:
            x2.append(exp.vehs_visiting_node_ids_at_current_state[idx])
            x3.append(exp.vehs_normalized_remaining_delays_at_current_state[idx])
            x4.append(exp.vehs_num_of_visiting_nodes_at_current_state[idx])
            x5.append(exp.vehs_normalized_num_of_nearby_vehs_at_current_state[idx])
            x2_.append(exp.vehs_visiting_node_ids_at_next_state[idx])
            x3_.append(exp.vehs_normalized_remaining_delays_at_next_state[idx])
            x4_.append(exp.vehs_num_of_visiting_nodes_at_next_state[idx])
            x5_.append(exp.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state[idx])
            x7.append(reward)

    new_exp = Experience(x1, x2, x3, x4, x5, x6, x1_, x2_, x3_, x4_, x7, x5_)
    return new_exp
