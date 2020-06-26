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
def upd_traffic_on_network(h=0):
    # sample from normal distribution
    for u, v in G.edges():
        dur = get_edge_mean_dur(u, v)
        std = get_edge_std(u, v)
        if dur is not np.inf:
            sample = np.random.normal(dur, std)
            while sample < 0:
                sample = np.random.normal(dur, std)
            G.edges[u, v]['dur'] = round(sample, 2)
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
    return NOD_NET.get_edge_data(u, v, default={'dur': None})['dur']


# return the mean travel time of edge (u, v)
def get_edge_real_dur(u, v):
    return G.get_edge_data(u, v, default={'dur': None})['dur']


# return the variance of travel time of edge (u, v)
def get_edge_var(u, v):
    return NOD_NET.get_edge_data(u, v, default={'var': None})['var']


# return the standard deviation of travel time of edge (u, v)
def get_edge_std(u, v):
    var = NOD_NET.get_edge_data(u, v, default={'var': None})['var']
    return np.sqrt(var)


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


# compute path that maximize the probability of arriving at a destination before a given time deadline
def stochastic_shortest_path(d, onid, dnid):
    """
    Attributes:
        d: deadline
        onid: origin node id
        dnid: destination node id
        m: mean
        v: variance
        l:left
        r:right
    """

    candidate_regions = []
    path_0, m_0, v_0 = get_lemada_optimal_path(0, onid, dnid)
    phi_0 = get_path_phi(d, m_0, v_0)
    path_inf, m_inf, v_inf = get_lemada_optimal_path(np.inf, onid, dnid)
    phi_inf = get_path_phi(d, m_inf, v_inf)

    if path_0 == path_inf:
        return path_0
    elif phi_0 > phi_inf:
        best_path = path_0
        phi_best = phi_0
    else:
        best_path = path_inf
        phi_best = phi_inf
    candidate_regions.append(((m_0, v_0), (m_inf, v_inf)))

    while len(candidate_regions) != 0:
        region = candidate_regions.pop()
        (m_l, v_l), (m_r, v_r) = region
        phi_probe = get_path_phi(d, m_l, v_r)
        if phi_probe < phi_best:
            continue
        lemada = - (m_l - m_r) / (v_l - v_r)
        path, m, v = get_lemada_optimal_path(lemada, onid, dnid)
        phi_path = get_path_phi(d, m, v)
        if (m == m_l and v == v_l) or (m == m_r and v == v_r):
            continue
        if phi_path > phi_best:
            best_path = path
            phi_best = phi_path
        phi_probe_l = get_path_phi(d, m_l, v)
        phi_probe_r = get_path_phi(d, m, v_r)
        if phi_probe_l > phi_best:
            candidate_regions.append(((m_l, v_l), (m, v)))
        if phi_probe_r > phi_best:
            candidate_regions.append(((m, v), (m_r, v_r)))
    return best_path


def get_lemada_optimal_path(lemada, onid, dnid):
    for u, v in G.edges():
        dur = get_edge_mean_dur(u, v)
        var = get_edge_var(u, v)
        if dur is np.inf:
            print('error: dur is np.inf !!!')
            quit()
        if lemada == np.inf:
            weight = var
        else:
            weight = dur + lemada * var
        G.edges[u, v]['dur'] = weight
    path = get_the_minimum_duration_path(G, onid, dnid)
    mean, var = get_path_mean_and_var(path)
    return path, mean, var


def get_the_minimum_duration_path(graph, source, target):
    path = nx.shortest_path(graph, source, target, weight='dur')
    return path


def get_path_mean_and_var(path):
    mean = 0.0
    var = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        mean += get_edge_mean_dur(u, v)
        var += get_edge_var(u, v)
    return round(mean, 2), round(var, 2)


def get_path_phi(d, m, v):
    return round((d-m)/(math.sqrt(v)), 4)




