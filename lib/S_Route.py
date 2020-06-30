"""
definition of routes for the AMoD system
"""

import math
import copy
import numpy as np
import networkx as nx
from collections import deque
from itertools import islice
from lib.Configure import NOD_NET, NOD_LOC, NOD_TTT, NOD_SPT, IS_STOCHASTIC
from numba import jit

G = copy.deepcopy(NOD_NET)


class Step(object):
    """
    Step is a class for steps in a leg
    Attributes:
        t: duration
        d: distance
        nid: a list of nodes id
        geo: geometry, a list of coordinates
    """

    def __init__(self, t=0.0, d=0.0, nid=[], geo=[]):
        self.t = t
        self.d = d
        self.nid = nid
        self.geo = geo

    def __str__(self):
        return 'step: distance = %.1f, duration = %.1f' % (self.d, self.t)


class Leg(object):
    """
    Leg is a class for legs in the route
    A leg may consists of a series of steps
    Attributes:
        rid: request id (if rebalancing then -1)
        pod: pickup (+1) or dropoff (-1), rebalancing (0)
        tnid: target (end of leg) node id in network
        ept: earliest possible arrival time
        ddl: latest arriving time
        t: total duration
        d: total distance
        steps: a list of steps
    """

    def __init__(self, rid, pod, tnid, ept, ddl, t=0.0, d=0.0, steps=[]):
        self.rid = rid
        self.pod = pod
        self.tnid = tnid
        self.ept = ept
        self.ddl = ddl
        self.t = t
        self.d = d
        self.steps = deque(steps)

    def __str__(self):
        return 'leg: distance = %.1f, duration = %.1f, number of steps = %d' % (self.d, self.t, len(self.steps))


# get the duration of the best route from origin to destination
def get_duration(onid, dnid):
    duration = NOD_TTT[onid - 1, dnid - 1]
    if duration != -1:
        return duration
    else:
        None


# get the best route from origin to destination
def get_routing(onid, dnid):
    path = get_path_from_SPtable(onid, dnid)
    # length, path = nx.bidirectional_dijkstra(G, onid, dnid)
    duration, distance, steps = build_route_from_path(path)
    # print('SPT', path, duration, distance)
    return duration, distance, steps


# get the best path from origin to destination
def get_path_from_SPtable(onid, dnid):
    path = [dnid]
    pre_node = NOD_SPT[onid - 1, dnid - 1]
    while pre_node > 0:
        path.append(pre_node)
        pre_node = NOD_SPT[onid - 1, pre_node - 1]
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
        t = get_edge_real_dur(u, v)
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


# update the traffic on road network
def upd_traffic_on_network():
    # sample from normal distribution
    for u, v in G.edges():
        dur = get_edge_mean_dur(u, v)
        std = get_edge_std(u, v)
        if dur is not np.inf:
            sample = np.random.normal(dur, std)
            while sample < 0:
                sample = np.random.normal(dur, std)
            G.edges[u, v]['dur'] = round(sample, 2)


# get the duration based on haversine formula
def get_haversine_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


# return the mean travel time of edge (u, v)
def get_edge_mean_dur(u, v):
    return NOD_NET.get_edge_data(u, v, default={'dur': None})['dur']


# return the current travel time of edge (u, v)
def get_edge_real_dur(u, v):
    return G.get_edge_data(u, v, default={'dur': None})['dur']


# return the variance of travel time of edge (u, v)
def get_edge_var(u, v):
    return NOD_NET.get_edge_data(u, v, default={'var': None})['var']


# return the standard deviation of travel time of edge (u, v)
def get_edge_std(u, v):
    return NOD_NET.get_edge_data(u, v, default={'std': None})['std']


# return the distance of edge (u, v)
def get_edge_dist(u, v):
    return NOD_NET.get_edge_data(u, v, default={'dist': None})['dist']


# return the geo of node [lng, lat]
def get_node_geo(nid):
    return list(NOD_NET.nodes[nid]['pos'])


# find the nearest node to[lng, lat] in Manhattan network
def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in NOD_LOC:
        # d_ = get_haversine_distance(lng, lat, nlng, nlat)
        d_ = abs(lng-nlng) + abs(lat-nlat)
        if d_ < d:
            d = d_
            nearest_node_id = nid

    if nearest_node_id is None:
        print()
        print('nearest_node_id not found')
        print('coordination', lng, lat)
        print('d', d)
        print()
    return int(nearest_node_id)
