"""
route planning functions
"""

from src.utility.utility_functions import *

t = timer_start()
with open(PATH_TO_NETWORK_NODES, "rb") as f:
    network_nodes = pickle.load(f)
with open(PATH_TO_VEHICLE_STATIONS, "rb") as f:
    vehicle_stations = pickle.load(f)
with open(PATH_TO_SHORTEST_PATH_TABLE, "rb") as f:
    shortest_path_table = pickle.load(f)
with open(PATH_TO_MEAN_TRAVEL_TIME_TABLE, "rb") as f:
    mean_travel_time_table = pickle.load(f)
with open(PATH_TO_TRAVEL_DISTANCE_TABLE, "rb") as f:
    travel_distance_table = pickle.load(f)
print(f"[INFO] Route functions are ready. ({timer_end(t)})")


# get the mean duration of the best route from origin to destination
def get_duration_from_origin_to_dest(onid: int, dnid: int) -> float:
    duration = mean_travel_time_table[onid - 1][dnid - 1]
    assert duration != -1
    return duration


# get the distance of the best route from origin to destination
def get_distance_from_origin_to_dest(onid: int, dnid: int) -> float:
    distance = travel_distance_table[onid - 1][dnid - 1]
    assert distance != -1
    return distance


# get the best route from origin to destination
def build_route_from_origin_to_dest(onid: int, dnid: int) -> (float, float, list[tuple]):
    # 1. recover the best path from origin to destination from the path table
    path = [dnid]
    pre_node = shortest_path_table[onid - 1][dnid - 1]
    while pre_node > 0:
        path.append(pre_node)
        pre_node = shortest_path_table[onid - 1][pre_node - 1]
    path.reverse()

    # 2. get the route information from origin to destination
    duration = 0.0
    distance = 0.0
    steps = []
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        t = mean_travel_time_table[u - 1][v - 1]
        d = travel_distance_table[u - 1][v - 1]
        u_geo = get_node_geo(u)
        v_geo = get_node_geo(v)
        steps.append((t, d, [u, v], [u_geo, v_geo]))
        duration += t
        distance += d
    tnid = path[-1]
    tnid_geo = get_node_geo(tnid)
    steps.append((0.0, 0.0, [tnid, tnid], [tnid_geo, tnid_geo]))

    # check the accuracy of routing.
    deviation_due_to_data_structure = 0.005
    assert (abs(duration - mean_travel_time_table[onid - 1][dnid - 1])
            <= deviation_due_to_data_structure)
    assert (abs(distance - travel_distance_table[onid - 1][dnid - 1])
            <= deviation_due_to_data_structure)

    return duration, distance, steps


# return the geo of node [lng, lat]
def get_node_geo(nid: int) -> [float, float]:
    pos = network_nodes[nid - 1]
    return [pos.lng, pos.lat]


def get_num_of_vehicle_stations() -> int:
    return len(vehicle_stations)


def get_vehicle_station_id(station_index: int) -> int:
    return vehicle_stations[station_index].node_id
