"""
definition of routes for the AMoD system
"""

import math
import copy
import numpy as np
import networkx as nx
from collections import deque
from itertools import islice
from lib.S_Configure import NOD_NET, NOD_LOC, NOD_TTT, NOD_SPT

G = copy.deepcopy(NOD_NET)
COEF_TRAVEL = 1.0


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
        ddl: latest arriving time
        t: total duration
        d: total distance
        steps: a list of steps
        pf_path: preferred path rather than the shortest path
    """

    def __init__(self, rid, pod, tnid, ddl, t=0.0, d=0.0, steps=[], pf_path=None):
        self.rid = rid
        self.pod = pod
        self.tnid = tnid
        self.ddl = ddl
        self.t = t
        self.d = d
        self.steps = deque(steps)
        self.pf_path = pf_path

    def __str__(self):
        return 'leg: distance = %.1f, duration = %.1f, number of steps = %d' % (self.d, self.t, len(self.steps))


class ScheTask(object):  # not used, cause using class will consume more time than just using tuple
    """
    ScheTask is a class for tasks in a schedule,
    where a schedule is a sequence of pick up and drop off tasks in a route
    Attributes:
        rid: request id (if rebalancing then -1)
        pod: pickup (+1) or dropoff (-1), rebalancing (0)
        tnid: target (end of task) node id in network
        ddl: latest arriving time
        pf_path: preferred path rather than the shortest path
    """

    def __init__(self, rid, pod, tnid, ddl, pf_path=None):
        self.rid = rid
        self.pod = pod
        self.tnid = tnid
        self.ddl = ddl
        self.pf_path = pf_path


# get the duration of the best route from origin to destination
def get_duration(onid, dnid):
    duration = NOD_TTT[onid - 1, dnid - 1] * COEF_TRAVEL
    if duration != -1:
        return duration
    else:
        None


# get the best route from origin to destination
def get_routing(onid, dnid, pf_path=None):
    if pf_path:
        path = pf_path
    else:
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


# get the duration of a path
def get_dur_from_path(path):
    dur = 0
    for node_idx in range(len(path) - 1):
        u = path[node_idx]
        v = path[node_idx + 1]
        dur += get_edge_real_dur(u, v)
    return dur


# update the traffic on road network
def upd_traffic_on_network(h=0):
    # sample from normal distribution
    for u, v in G.edges():
        dur = get_edge_mean_dur(u, v)
        std = get_edge_std(u, v)
        if dur is not np.inf:
            sample = np.random.normal(dur, std)
            while sample < 0:
                sample = np.random.normal(dur, std)
            G.edges[u, v]['dur'] = sample
    # # update on hours
    # for e, u, v in EDG_NOD:
    #     dur = EDG_TTH[e-1, h]
    #     G.edges[u, v]['dur'] = dur


# get the duration based on haversine formula
def get_haversine_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


# return the mean travel time of edge (u, v)
def get_edge_mean_dur(u, v):
    return NOD_NET.get_edge_data(u, v, default={'dur': None})['dur'] * COEF_TRAVEL


# return the mean travel time of edge (u, v)
def get_edge_real_dur(u, v):
    return G.get_edge_data(u, v, default={'dur': None})['dur'] * COEF_TRAVEL


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


# returns the k-shortest paths from source to target in a weighted graph G
def k_shortest_paths(G, source, target, k=1, weight='dur'):
    # Determine the shortest path from the source to the target
    duration, path = nx.bidirectional_dijkstra(G, source, target, weight=weight)
    A = [tuple([duration, path])]  # k_shortest_paths
    B = []
    # G_copy = G.copy()  # computational time might be long

    for i in range(1, k):
        i_path = A[-1][1]  # k-1 shortest path
        #  The spur node ranges from the first node to the next to last node in the previous k-shortest path
        for j in range(len(i_path) - 1):
            # Spur node is retrieved from the previous k-shortest path, k − 1.
            spur_node = i_path[j]
            root_path = i_path[:j + 1]

            root_path_duration = 0
            for u_i in range(len(root_path) - 1):
                u = root_path[u_i]
                v = root_path[u_i + 1]
                root_path_duration += get_edge_real_dur(u, v)

            # print('root_path', root_path)
            # print('root_path_duration', root_path_duration)

            edges_removed = []
            for path_k in A:
                curr_path = path_k[1]
                # Remove the links that are part of the previous shortest paths which share the same root path
                if len(curr_path) > j and root_path == curr_path[:j + 1]:
                    u = curr_path[j]
                    v = curr_path[j + 1]
                    if G.has_edge(u, v):
                        G.remove_edge(u, v)
                        edges_removed.append((u, v,get_edge_real_dur(u, v)))
                        # print('u, v, edge_duration (remove)', u, v, edge_duration)

            # remove rootPathNode (except spurNode) from Graph
            for n in range(len(root_path) - 1):
                u = root_path[n]
                # print('node', u)
                # out-edges
                nodes = copy.deepcopy(G[u])
                for v in nodes:
                    G.remove_edge(u, v)
                    edges_removed.append((u, v, get_edge_real_dur(u, v)))
                    # print('u, v, edge_duration (remove)', u, v, edge_duration)
                # if G.is_directed():
                #     # in-edges
                #     for u, v, edge_duration in G.in_edges_iter(node, data=True):
                #         print('u, v, edge_duration (in)', u, v, edge_duration)
                #         G.remove_edge(u, v)
                #         edges_removed.append((u, v, edge_duration))

            try:
                # Calculate the spur path from the spur node to the target
                spur_path_duration, spur_path = nx.bidirectional_dijkstra(G, spur_node, target, weight='dur')
                # Entire path is made up of the root path and spur path
                total_path = root_path[:-1] + spur_path
                total_path_duration = root_path_duration + spur_path_duration
                potential_k = tuple([total_path_duration, total_path])
                # Add the potential k-shortest path to the heap
                if potential_k not in B:
                    B.append(potential_k)
                    # print('potential_k', potential_k)
            except nx.NetworkXNoPath:
                # print('NetworkXNoPath')
                pass

            # Add back the edges and nodes that were removed from the graph
            for u, v, edge_duration in edges_removed:
                G.add_edge(u, v, weight=edge_duration)
                # print('u, v, edge_duration (add)', u, v, edge_duration)

        if len(B):
            B.sort(key=lambda e: e[0])
            A.append(B[0])
            B.pop(0)
        else:
            break
    A.sort(key=lambda p: p[0])
    return A


def k_shortest_paths_nx(source, target, k, weight='dur'):
    return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))






