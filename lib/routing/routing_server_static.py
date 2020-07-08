"""
route planning functions using deterministic travel times
"""

import pickle
import numpy as np
from lib.simulator.config import TRAVEL_TIME

with open(f'./data/NYC_NET_{TRAVEL_TIME}.pickle', 'rb') as f:
    NETWORK = pickle.load(f)
with open(f'./data/path-tables-gitignore/NYC_SPT_{TRAVEL_TIME}_0.pickle', 'rb') as f:
    PATH_TABLE = pickle.load(f)
with open(f'./data/path-tables-gitignore/NYC_TTT_{TRAVEL_TIME}_0.pickle', 'rb') as f:
    TIME_TABLE = pickle.load(f)


# get the duration of the best route from origin to destination
def get_duration_from_origin_to_dest(onid, dnid):
    duration = TIME_TABLE[onid - 1, dnid - 1]
    if duration != -1:
        return duration
    else:
        None


# get the best route from origin to destination
def build_route_from_origin_to_dest(onid, dnid):
    path = get_path_from_origin_to_dest(onid, dnid)
    duration, distance, steps = build_route_from_path(path)
    assert np.isclose(duration, TIME_TABLE[onid - 1, dnid - 1])
    return duration, distance, steps


# recover the best path from origin to destination from the path table
def get_path_from_origin_to_dest(onid, dnid):
    path = [dnid]
    pre_node = PATH_TABLE[onid - 1, dnid - 1]
    while pre_node > 0:
        path.append(pre_node)
        pre_node = PATH_TABLE[onid - 1, pre_node - 1]
    path.reverse()
    return path


# get the best route information from origin to destination
def build_route_from_path(path):
    duration = 0.0
    distance = 0.0
    steps = []
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        t = get_edge_dur(u, v)
        d = get_edge_dist(u, v)
        u_geo = get_node_geo(u)
        v_geo = get_node_geo(v)
        steps.append((t, d, [u, v], [u_geo, v_geo]))
        duration += t
        distance += d
    tnid = path[-1]
    tnid_geo = get_node_geo(tnid)
    steps.append((0.0, 0.0, [tnid, tnid], [tnid_geo, tnid_geo]))
    return duration, distance, steps


# return the mean travel time of edge (u, v)
def get_edge_dur(u, v):
    return NETWORK.get_edge_data(u, v, default={'dur': None})['dur']


# return the distance of edge (u, v)
def get_edge_dist(u, v):
    return NETWORK.get_edge_data(u, v, default={'dist': None})['dist']


# return the geo of node [lng, lat]
def get_node_geo(nid):
    return list(NETWORK.nodes[nid]['pos'])
