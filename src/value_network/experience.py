
from src.dispatcher.scheduling import *


class Experience(object):
    def __init__(self,
                 system_time_scaled: float,
                 num_of_new_orders: int,
                 vehicles_info: list[list[int]],
                 vehicles_current_schedule_pos: list[list[int]],
                 vehicles_current_schedule_delay: list[list[int]],
                 vehicles_candidate_schedules_info_updated_to_next_epoch: list[list[int]],
                 vehicles_candidate_schedules_pos_updated_to_next_epoch: list[list[int]],
                 vehicles_candidate_schedules_delay_updated_to_next_epoch: list[list[int]]):
        """
        Example of experience (number_of_vehicles = 3, vehicle_capacity = 1, max_pickup_wait_time_ms=50):
        (The schedule_pos here contains the vehicle's pos, which is different from the schedule used in types.)

        system_time_scaled = 0.5
        num_of_new_orders = 200
        vehicles_info = [[0, 1, 9, 3],
                         [1, 4, 12, 2],
                         [2, 7, 15, 1]]
        vehicles_current_schedule_pos = [[1, 2, 3],
                                        [4, 5, 0],
                                        [7, 0, 0]]
        vehicles_current_schedule_delay = [[100, 20, 30],
                                           [100, 10, -1],
                                           [100, -1, -2]]
        vehicles_candidate_schedules_info_updated_to_next_epoch = [[0, 2],
                                                                   [1, 3],
                                                                   [1, 2],
                                                                   [2, 2]]
        vehicles_candidate_schedules_pos_updated_to_next_epoch = [[1, 5, 0],
                                                                  [4, 3, 8],
                                                                  [4, 6, 0],
                                                                  [7, 2, 0]]
        vehicles_candidate_schedules_delay_updated_to_next_epoch = [[100, 30, -1],
                                                                    [100, 20, 10],
                                                                    [100, 10, -1],
                                                                    [100, 40, -1]]
        """

        self.system_time_scaled = system_time_scaled
        self.num_of_new_orders = num_of_new_orders

        #   vehicles_info = [[vehicle_id, vehicle_pos, num_of_nearby_vehicles, current_schedule_length]]
        self.vehicles_info = vehicles_info
        #   current_schedules_pos = [[vehicle_pos, schedule_pos_1, schedule_pos_2, ...]]
        self.vehicles_current_schedule_pos = vehicles_current_schedule_pos
        #   current_schedules_delay = [[vehicle_pos_delay, schedule_pos_1_delay, ...]]
        self.vehicles_current_schedule_delay = vehicles_current_schedule_delay

        #   candidate_schedules_info = [[vehicle_id, vehicle_candidate_schedule_length]]
        self.vehicles_candidate_schedules_info_updated_to_next_epoch = \
            vehicles_candidate_schedules_info_updated_to_next_epoch
        #   candidate_schedules_pos = [[vehicle_pos_updated_to_next_epoch, schedule_pos_1, schedule_pos_2, ...]]
        self.vehicles_candidate_schedules_pos_updated_to_next_epoch = \
            vehicles_candidate_schedules_pos_updated_to_next_epoch
        #   candidate_schedules_delay = [[vehicle_pos_delay_updated_to_next_epoch, schedule_pos_1_delay, ...]]
        self.vehicles_candidate_schedules_delay_updated_to_next_epoch = \
            vehicles_candidate_schedules_delay_updated_to_next_epoch


def convert_and_store_feasible_schedules_as_an_experience(feasible_vehicle_trip_pairs: list[SchedulingResult],
                                                          num_of_new_orders: int,
                                                          orders: list[Order],
                                                          vehicles: list[Vehicle],
                                                          system_time_ms: int,
                                                          router_func: Router,
                                                          cycle_ms: int) -> Experience:
    max_pickup_wait_time_ms = MAX_PICKUP_WAIT_TIME_MIN * 60 * 1000

    #   vehicles_info = [[vehicle_id, vehicle_pos, num_of_nearby_vehicles, current_schedule_length]]
    vehicles_info: list[list[int]] = []
    #   current_schedule_pos = [[vehicle_pos, schedule_pos_1, schedule_pos_2, ...]]
    vehicles_current_schedule_pos: list[list[int]] = []
    #   current_schedule_delay = [[vehicle_pos_delay, schedule_pos_1_delay, ...]]
    vehicles_current_schedule_delay: list[list[int]] = []

    for vehicle in vehicles:
        # 1. Add each vehicle's id, location node id, the number of its nearby vehicles
        # and the length of its complete schedule pos.
        num_of_nearby_vehicles = 0
        for vehicle_2 in vehicles:
            if router_func.get_route(vehicle.pos, vehicle_2.pos, RoutingType.TIME_ONLY).duration_ms \
                    < max_pickup_wait_time_ms \
                    or router_func.get_route(vehicle_2.pos, vehicle.pos, RoutingType.TIME_ONLY).duration_ms \
                    < max_pickup_wait_time_ms:
                num_of_nearby_vehicles += 1
        assert (len(vehicles_info) == vehicle.id)
        vehicles_info.append([vehicle.id, vehicle.pos.node_id, num_of_nearby_vehicles, len(vehicle.schedule) + 1])

        # 2. Add each vehicle's current schedule's locations and remaining delays.
        vehicle_current_schedule_pos, vehicle_current_schedule_remaining_delay = \
            convert_schedule_to_list_data_structure(vehicle_pos_node_id=vehicle.pos.node_id,
                                                    vehicle_capacity=vehicle.capacity,
                                                    schedule=vehicle.schedule,
                                                    schedule_start_idx=0,
                                                    orders=orders,
                                                    max_pickup_wait_time_ms=max_pickup_wait_time_ms,
                                                    accumulated_time_ms=0,
                                                    system_time_ms=system_time_ms)
        vehicles_current_schedule_pos.append(vehicle_current_schedule_pos)
        vehicles_current_schedule_delay.append(vehicle_current_schedule_remaining_delay)

    #   candidate_schedules_info = [[vehicle_id, vehicle_candidate_schedule_length]]
    vehicles_candidate_schedules_info_updated_to_next_epoch: list[list[int]] = []
    #   candidate_schedules_pos = [[vehicle_pos_updated_to_next_epoch, schedule_pos_1, schedule_pos_2, ...]]
    vehicles_candidate_schedules_pos_updated_to_next_epoch: list[list[int]] = []
    #   candidate_schedules_delay = [[vehicle_pos_updated_to_next_epoch, schedule_pos_1, schedule_pos_2, ...]]
    vehicles_candidate_schedules_delay_updated_to_next_epoch: list[list[int]] = []

    # 3. Add each vehicle's candidate schedules' locations and remaining delays, updated to next epoch.
    for vt_pair in feasible_vehicle_trip_pairs:
        vehicle_pos_node_id = vehicle.pos.node_id
        candidate_schedule_start_idx = 0
        candidate_schedule = vt_pair.feasible_schedules[vt_pair.best_schedule_idx]
        remaining_time = cycle_ms - vehicle.step_to_pos.duration_ms
        if remaining_time > 0:
            for wp in candidate_schedule:
                if wp.route.duration_ms <= remaining_time:
                    remaining_time -= wp.route.duration_ms
                    vehicle_pos_node_id = wp.pos.node_id
                    candidate_schedule_start_idx += 1
                else:
                    for step in wp.route:
                        if step.duration_ms <= remaining_time:
                            remaining_time -= step.duration_ms
                            vehicle_pos_node_id = step.poses[1].node_id
                        else:
                            vehicle_pos_node_id = step.poses[1].node_id
                            break
                    break
        vehicle_candidate_schedule_pos, vehicle_candidate_schedule_remaining_delay = \
            convert_schedule_to_list_data_structure(vehicle_pos_node_id=vehicle_pos_node_id,
                                                    vehicle_capacity=vehicle.capacity,
                                                    schedule=candidate_schedule,
                                                    schedule_start_idx=candidate_schedule_start_idx,
                                                    orders=orders,
                                                    max_pickup_wait_time_ms=max_pickup_wait_time_ms,
                                                    accumulated_time_ms=vehicle.step_to_pos.duration_ms,
                                                    system_time_ms=system_time_ms)
        vehicles_candidate_schedules_info_updated_to_next_epoch.append(
            [vehicle.id, len(vehicle.schedule) + 1 - candidate_schedule_start_idx])
        vehicles_candidate_schedules_pos_updated_to_next_epoch.append(vehicle_candidate_schedule_pos)
        vehicles_candidate_schedules_delay_updated_to_next_epoch.append(vehicle_candidate_schedule_remaining_delay)
    new_experience = Experience(system_time_ms, num_of_new_orders,
                                vehicles_info,
                                vehicles_current_schedule_pos,
                                vehicles_current_schedule_delay,
                                vehicles_candidate_schedules_info_updated_to_next_epoch,
                                vehicles_candidate_schedules_pos_updated_to_next_epoch,
                                vehicles_candidate_schedules_delay_updated_to_next_epoch)
    return new_experience


def convert_schedule_to_list_data_structure(vehicle_pos_node_id: int,
                                            vehicle_capacity: int,
                                            schedule: list[Waypoint],
                                            schedule_start_idx: int,
                                            orders: list[Order],
                                            max_pickup_wait_time_ms: int,
                                            accumulated_time_ms: int,
                                            system_time_ms: int) -> tuple[list[int], list[int]]:
    extra_length_for_long_schedule = 2
    # A 2-seat vehicle might serve 3 orders in one trip.
    # e.g. [vehicle_pos, pick_order_1, pick_order_2, drop_order_1, pick_order_3, drop_order_2, drop_order_3],
    vehicle_schedule_pos = [0] * (1 + vehicle_capacity * 2 + extra_length_for_long_schedule)
    vehicle_schedule_remaining_delay = [-1] * (vehicle_capacity * 2 + 1 + extra_length_for_long_schedule)

    vehicle_schedule_pos[0] = vehicle_pos_node_id
    vehicle_schedule_remaining_delay[0] = max_pickup_wait_time_ms * 2

    for idx, wp in enumerate(schedule):
        accumulated_time_ms += wp.route.duration_ms
        # schedule_start_idx is used for candidate_schedule only, updating the status of the schedule to next epoch.
        if idx < schedule_start_idx:
            continue
        vehicle_schedule_pos[idx + 1 - schedule_start_idx] = wp.pos.node_id
        if wp.op == WaypointOp.PICKUP:
            vehicle_schedule_remaining_delay[idx + 1 - schedule_start_idx] = \
                orders[wp.order_id].max_pickup_time_ms - (system_time_ms + accumulated_time_ms)
            assert (0 <= vehicle_schedule_remaining_delay[idx + 1 - schedule_start_idx] <= max_pickup_wait_time_ms)
        if wp.op == WaypointOp.DROPOFF:
            vehicle_schedule_remaining_delay[idx + 1 - schedule_start_idx] = \
                orders[wp.order_id].max_dropoff_time_ms - (system_time_ms + accumulated_time_ms)
            assert (0 <= vehicle_schedule_remaining_delay[idx + 1 - schedule_start_idx] <= max_pickup_wait_time_ms * 2)
    return vehicle_schedule_pos, vehicle_schedule_remaining_delay
