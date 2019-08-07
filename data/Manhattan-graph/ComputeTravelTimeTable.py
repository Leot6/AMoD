"""
compute the travel time table for edges in Manhattan
"""

import time
import sys
import pickle
import math
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from tqdm import tqdm

# sys.path.append('../..')


# get the duration based on haversine formula
def get_haversine_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


def load_Manhattan_graph():
    edges = pd.read_csv('edges.csv')
    nodes = pd.read_csv('nodes.csv')
    aa = time.time()
    # set the mean travel time of all day (24 hours) as the travel time
    travel_time_edges = pd.read_csv('time-sat.csv', index_col=0)
    mean_travel_times = travel_time_edges.mean(1)
    std_travel_times = travel_time_edges.std(1)
    G = nx.DiGraph()
    num_edges = edges.shape[0]
    rng = tqdm(edges.iterrows(), total=num_edges, ncols=100, desc='Loading Manhattan Graph')
    for i, edge in rng:
        u = edge['source']
        v = edge['sink']
        u_pos = np.array([nodes.iloc[u - 1]['lng'], nodes.iloc[u - 1]['lat']])
        v_pos = np.array([nodes.iloc[v - 1]['lng'], nodes.iloc[v - 1]['lat']])
        G.add_node(u, pos=u_pos)
        G.add_node(v, pos=v_pos)
        travel_time = round(mean_travel_times.iloc[i], 2)
        standard_deviation = round(std_travel_times.iloc[i], 2)
        travel_dist = get_haversine_distance(u_pos[0], u_pos[1], v_pos[0], v_pos[1])
        G.add_edge(u, v, dur=travel_time, std=standard_deviation, dist=travel_dist)
    print('...running time : %.05f seconds' % (time.time() - aa))

    # # store_map_as_pickle_file
    # with open('map.pickle', 'wb') as f:
    #     pickle.dump(G, f)
    return G


def compute_table_nx(G, nodes_id, travel_time_table):
    time1 = time.time()
    length = dict(nx.all_pairs_dijkstra_path_length(G, cutoff=None, weight='dur'))
    print('...running time : %.05f seconds' % (time.time() - time1))

    for o in tqdm(nodes_id):
        for d in tqdm(nodes_id):
            try:
                duration = round(length[o][d], 2)
                travel_time_table.iloc[o - 1, d - 1] = duration
            except nx.NetworkXNoPath:
                print('no path between', o, d)


def compute_shortest_path_table(nodes, G):
    time1 = time.time()
    len_path = dict(nx.all_pairs_dijkstra(G, cutoff=None, weight='dur'))
    print('all_pairs_dijkstra running time : %.05f seconds' % (time.time() - time1))
    # nodes = pd.read_csv('nodes.csv')
    nodes_id = list(range(1, nodes.shape[0] + 1))
    num_nodes = len(nodes_id)
    shortest_path_table = pd.DataFrame(-np.ones((num_nodes, num_nodes), dtype=int), index=nodes_id, columns=nodes_id)
    for o in tqdm(nodes_id):
        for d in tqdm(nodes_id):
            try:
                path = len_path[o][1][d]
                if len(path) == 1:
                    continue
                else:
                    pre_node = path[-2]
                    shortest_path_table.iloc[o - 1, d - 1] = pre_node
            except nx.NetworkXNoPath:
                print('no path between', o, d)
    # shortest_path_table.to_csv('shortest-path-table.csv')
    return shortest_path_table


def compute_k_shortest_path_table(nodes, G, NOD_SPT):
    pass


if __name__ == '__main__':
    load_Manhattan_graph()

    # # for travel time table
    # nodes = pd.read_csv('nodes.csv')
    # nodes_id = list(range(1, nodes.shape[0] + 1))
    # # travel_time_table = pd.DataFrame(-np.ones((num_nodes, num_nodes)), index=nodes_id, columns=nodes_id)
    # # travel_time_table.to_csv('time-table-empty.csv')
    #
    # travel_time_table = pd.read_csv('time-table-empty.csv', index_col=0)
    # # print(travel_time_table.head(2))
    # # print(travel_time_table.shape[0])
    # # print(travel_time_table.shape[1])
    #
    # compute_table_OSRM(nodes, nodes_id, travel_time_table)
    #
    # # compute_table_nx(G, nodes_id, travel_time_table)
    #
    # travel_time_table.to_csv('time-table-osrm.csv')

    # travel_time_table = pd.read_csv('time-table-osrm.csv', index_col=0)
    # # print(travel_time_table.iloc[3826, 3833])
    # # print(travel_time_table.iloc[3910, 3920])
    # print(travel_time_table.iloc[5:10, 1800:2000])
    # travel_time_table = pd.read_csv('time-table-sat.csv', index_col=0)
    # print(travel_time_table.iloc[5:10, 1800:2000])







