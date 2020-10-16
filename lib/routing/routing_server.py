"""
route planning functions using stochastic travel times
"""

import os
import math
import copy
import pickle
import numpy as np
import scipy.stats as st
from lib.simulator.config import TRAVEL_TIME, IS_STOCHASTIC, IS_STOCHASTIC_CONSIDERED

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

with open(f'{root_path}/data/NYC_NET_{TRAVEL_TIME}.pickle', 'rb') as f:
    NETWORK = pickle.load(f)
if IS_STOCHASTIC:
    NETWORK_STOCHASTIC = copy.deepcopy(NETWORK)
    NUM_OF_LAMBDA = 21
else:
    NUM_OF_LAMBDA = 1
PATH_TABLE_LIST = [None] * NUM_OF_LAMBDA
TIME_TABLE_LIST = [None] * NUM_OF_LAMBDA
VAR_TABLE_LIST = [None] * NUM_OF_LAMBDA
for i in range(NUM_OF_LAMBDA):
    with open(f'{root_path}/data/path-tables-gitignore/NYC_SPT_{TRAVEL_TIME}_{str(i)}.pickle', 'rb') as f:
        PATH_TABLE_LIST[i] = pickle.load(f)
    with open(f'{root_path}/data/path-tables-gitignore/NYC_TTT_{TRAVEL_TIME}_{str(i)}.pickle', 'rb') as f:
        TIME_TABLE_LIST[i] = pickle.load(f)
    with open(f'{root_path}/data/path-tables-gitignore/NYC_TTV_{TRAVEL_TIME}_{str(i)}.pickle', 'rb') as f:
        VAR_TABLE_LIST[i] = pickle.load(f)

num_of_path = 0
num_of_stochastic_path = 0
avg_path_mean = 0
avg_path_var = 0
avg_path_mean_stochastic = 0
avg_path_var_stochastic = 0
avg_cdf = 0
avg_cdf_0 = 0
show_counting = False


# get the mean duration of the best route from origin to destination
def get_duration_from_origin_to_dest(onid, dnid):
    duration = TIME_TABLE_LIST[0][onid - 1, dnid - 1]
    if duration != -1:
        return duration
    else:
        None


# get the best route from origin to destination
def build_route_from_origin_to_dest(onid, dnid):
    path = get_path_from_origin_to_dest(onid, dnid)
    duration, distance, steps = build_route_from_path(path)
    return duration, distance, steps


# recover the best path from origin to destination from the path table
def get_path_from_origin_to_dest(onid, dnid):
    if IS_STOCHASTIC_CONSIDERED:
        lambda_idx = get_best_lambda_idx(onid, dnid)
    else:
        lambda_idx = 0
    path = [dnid]
    pre_node = PATH_TABLE_LIST[lambda_idx][onid - 1, dnid - 1]
    while pre_node > 0:
        path.append(pre_node)
        pre_node = PATH_TABLE_LIST[lambda_idx][onid - 1, pre_node - 1]
    path.reverse()

    if show_counting:
        global num_of_path
        global num_of_stochastic_path
        global avg_path_mean
        global avg_path_var
        global avg_path_mean_stochastic
        global avg_path_var_stochastic
        global avg_cdf
        global avg_cdf_0
        mean, var = get_path_mean_and_var(path)
        num_of_path += 1
        avg_path_mean += (mean - avg_path_mean) / num_of_path
        avg_path_var += (var - avg_path_var) / num_of_path
        if lambda_idx != 0:
            num_of_stochastic_path += 1
            avg_path_mean_stochastic += (mean - avg_path_mean_stochastic) / num_of_stochastic_path
            avg_path_var_stochastic += (var - avg_path_var_stochastic) / num_of_stochastic_path

            ddl = get_duration_from_origin_to_dest(onid, dnid) * 1.2
            path_0 = [dnid]
            pre_node_0 = PATH_TABLE_LIST[0][onid - 1, dnid - 1]
            while pre_node_0 > 0:
                path_0.append(pre_node_0)
                pre_node_0 = PATH_TABLE_LIST[0][onid - 1, pre_node_0 - 1]
            path_0.reverse()
            mean_0, var_0 = get_path_mean_and_var(path_0)
            cdf_0 = round(st.norm(mean_0, var_0).cdf(ddl) * 100, 2)
            avg_cdf_0 += (cdf_0 - avg_cdf_0) / num_of_stochastic_path
            cdf = round(st.norm(mean, var).cdf(ddl) * 100, 2)
            avg_cdf += (cdf - avg_cdf) / num_of_stochastic_path

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
    if IS_STOCHASTIC:
        return NETWORK_STOCHASTIC.get_edge_data(u, v, default={'dur': None})['dur']
    else:
        return NETWORK.get_edge_data(u, v, default={'dur': None})['dur']


def get_edge_std(u, v):
    return NETWORK.get_edge_data(u, v, default={'std': None})['std']


# return the distance of edge (u, v)
def get_edge_dist(u, v):
    return NETWORK.get_edge_data(u, v, default={'dist': None})['dist']


# return the geo of node [lng, lat]
def get_node_geo(nid):
    return list(NETWORK.nodes[nid]['pos'])


# update the traffic on road network
def upd_traffic_on_network():
    # sample from normal distribution
    for u, v in NETWORK_STOCHASTIC.edges():
        mean = get_edge_dur(u, v)
        std = get_edge_std(u, v)
        if mean is not np.inf:
            sample = np.random.normal(mean, std)
            while sample < 0:
                sample = np.random.normal(mean, std)
            NETWORK_STOCHASTIC.edges[u, v]['dur'] = round(sample, 2)


def get_best_lambda_idx(onid, dnid, num_of_l=NUM_OF_LAMBDA):
    ddl = get_duration_from_origin_to_dest(onid, dnid) * 1.2
    phi_0 = get_lambda_optimal_path_phi(0, onid, dnid, ddl)
    phi_inf = get_lambda_optimal_path_phi(num_of_l - 1, onid, dnid, ddl)
    if np.isclose(phi_0, phi_inf):
        return 0
    elif phi_0 > phi_inf:
        best_lambda_idx = 0
        phi_best = phi_0
    else:
        best_lambda_idx = num_of_l - 1
        phi_best = phi_inf

    for lambda_idx in range(1, num_of_l - 1):
        phi_new = get_lambda_optimal_path_phi(lambda_idx, onid, dnid, ddl)
        if phi_new > phi_best:
            best_lambda_idx = lambda_idx
            phi_best = phi_new
    return best_lambda_idx


def get_lambda_optimal_path_phi(lambda_idx, onid, dnid, ddl):
    mean = TIME_TABLE_LIST[lambda_idx][onid - 1, dnid - 1]
    var = VAR_TABLE_LIST[lambda_idx][onid - 1, dnid - 1]
    # avoid warning: RuntimeWarning: invalid value encountered in double_scalars
    if np.isclose(var, 0):
        var += 1
    phi = (ddl - mean) / (math.sqrt(var))
    return phi


# temp function, for debug use
def get_path_mean_and_var(path):
    mean = 0.0
    var = 0.0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        mean += NETWORK.get_edge_data(u, v, default={'dur': None})['dur']
        var += NETWORK.get_edge_data(u, v, default={'var': None})['var']
    return round(mean, 2), round(var, 2)


def print_counting():
    if show_counting:
        print('')
        print(f'{num_of_stochastic_path / num_of_path * 100:.2f}% ({num_of_stochastic_path}/{num_of_path}) '
              f'of the paths is different. The mean is ({avg_path_mean_stochastic:.2f}/{avg_path_mean:.2f}) '
              f'and var is ({avg_path_var_stochastic:.2f}/{avg_path_var:.2f})')
        print(f'cdf:{avg_cdf_0:.2f}% / {avg_cdf:.2f}%')
        print('                           ')
