import time
import math
import requests
import pickle
import pandas as pd
import numpy as np
import networkx as nx
import copy
from heapq import heappush, heappop
from itertools import count

from tqdm import tqdm
from collections import deque


# nodes = pd.read_csv('data/nodes.csv').values.tolist()
# with open('./data/NOD_TTT.pickle', 'rb') as f:
#     NOD_TTT = pickle.load(f)


# generate the request in url format
def create_url(olng, olat, dlng, dlat, steps='false', annotations='false'):
    ghost = '0.0.0.0'
    gport = 5000
    return 'http://{0}:{1}/route/v1/driving/{2},{3};{4},{5}?alternatives=false&steps=' \
           '{6}&annotations={7}&geometries=geojson'.format(
        ghost, gport, olng, olat, dlng, dlat, steps, annotations)


# send the request and get the response in Json format
def call_url(url):
    while True:
        try:
            response = requests.get(url, timeout=1)
            json_response = response.json()
            code = json_response['code']
            if code == 'Ok':
                return json_response, True
            else:
                print('Error: %s' % (json_response['message']))
                return json_response, False
        except requests.exceptions.Timeout:
            # print('Time out: %s' % url)
            time.sleep(2)
        except Exception as err:
            print('Failed: %s' % url)
            # return None
            time.sleep(2)


# get the best route from origin to destination
def get_routing(olng, olat, dlng, dlat):
    url = create_url(olng, olat, dlng, dlat, steps='true', annotations='false')
    response, code = call_url(url)
    if code:
        return response['routes'][0]['legs'][0]
    else:
        return None


# get the duration of the best route from origin to destination
def get_duration(olng, olat, dlng, dlat):
    url = create_url(olng, olat, dlng, dlat, steps='false', annotations='false')
    response, code = call_url(url)
    if code:
        return response['routes'][0]['duration']
    else:
        return None


def get_haversine_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


# def find_nearest_node(lng, lat):
#     nearest_node_id = None
#     d = np.inf
#     for nid, nlng, nlat in nodes:
#         # d_ = get_haversine_distance(lng, lat, nlng, nlat)
#         d_ = abs(lng-nlng) + abs(lat-nlat)
#         if d_ < d:
#             d = d_
#             nearest_node_id = nid
#     # if d > 150:
#     #     print('distance of', [lng, lat], 'to node', nearest_node_id, 'is larger than 100m!!!!!!!!')
#     return int(nearest_node_id)


if __name__ == "__main__":

    # l = 200
    # aa = time.time()
    # a = deque([])
    # for i in range(l):
    #     a.append(i)
    # a.popleft()
    # print('deque running time:', (time.time() - aa))
    #
    # bb = time.time()
    # b = []
    # for i in range(l):
    #     b.append(i)
    # del b[0:3]
    # print('list running time:', (time.time() - bb))

    # G = nx.DiGraph()
    # G.add_edge('C', 'D', weight=3)
    # G.add_edge('C', 'E', weight=2)
    # G.add_edge('D', 'F', weight=4)
    # G.add_edge('E', 'D', weight=1)
    # G.add_edge('E', 'F', weight=2)
    # G.add_edge('E', 'G', weight=3)
    # G.add_edge('F', 'G', weight=2)
    # G.add_edge('F', 'H', weight=1)
    # G.add_edge('G', 'H', weight=2)
    # source = 'C'
    # target = 'H'

    # with open('./data/NET_NYC.pickle', 'rb') as f:
    #     G = pickle.load(f)
    # G_original = copy.deepcopy(G)
    # with open('./data/NOD_TTT.pickle', 'rb') as f:
    #     NOD_TTT = pickle.load(f)
    # NOD_LOC = pd.read_csv('./data/nodes.csv')
    # nodes_id = list(range(1, NOD_LOC.shape[0] + 1))

    # nodes_id = list(range(1, 6))
    # num_nodes = len(nodes_id)
    # shortest_path_table = [[-1 for i in range(num_nodes)] for j in range(num_nodes)]
    #
    # time1 = time.time()
    # len_path = dict(nx.all_pairs_dijkstra(G, cutoff=None, weight='weight'))
    # print('all_pairs_dijkstra running time : %.05f seconds' % (time.time() - time1))

    # for o in tqdm(nodes_id):
    #     for d in tqdm(nodes_id):
    #         try:
    #             duration = round(len_path[o][0][d], 2)
    #             # path = len_path[o][1][d]
    #
    #             # shortest_path_table[o - 1][d - 1] = tuple((duration, path))
    #             shortest_path_table[o - 1][d - 1] = duration
    #         except nx.NetworkXNoPath:
    #             print('no path between', o, d)
    #
    # with open('NOD_SPT1.pickle', 'wb') as f:
    #     pickle.dump(shortest_path_table, f)


    # # Determine the shortest path from the source to the target
    # duration, path = nx.bidirectional_dijkstra(G, source, target)
    # A = [tuple([duration, path])]  # k_shortest_paths
    # B = []
    # # G_copy = G.copy()  # computational time might be long
    #
    # for i in range(1, k):
    #     i_path = A[-1][1]  # k-1 shortest path
    #     #  The spur node ranges from the first node to the next to last node in the previous k-shortest path
    #     for j in range(len(i_path) - 1):
    #         # Spur node is retrieved from the previous k-shortest path, k − 1.
    #         spur_node = i_path[j]
    #         root_path = i_path[:j + 1]
    #
    #         root_path_duration = 0
    #         for u_i in range(len(root_path)-1):
    #             u = root_path[u_i]
    #             v = root_path[u_i+1]
    #             root_path_duration += G.edges[u, v]['weight']
    #
    #         # print('root_path', root_path)
    #         # print('root_path_duration', root_path_duration)
    #
    #         edges_removed = []
    #         for path_k in A:
    #             curr_path = path_k[1]
    #             # Remove the links that are part of the previous shortest paths which share the same root path
    #             if len(curr_path) > j and root_path == curr_path[:j + 1]:
    #                 u = curr_path[j]
    #                 v = curr_path[j + 1]
    #                 if G.has_edge(u, v):
    #                     edge_duration = G.edges[u, v]['weight']  # need to be compared to NOD_TTT
    #                     G.remove_edge(u, v)
    #                     edges_removed.append((u, v, edge_duration))
    #                     # print('u, v, edge_duration (remove)', u, v, edge_duration)
    #
    #         # # remove rootPathNode (except spurNode) from Graph
    #         # for n in range(len(root_path) - 1):
    #         #     node = root_path[n]
    #         #     print('node', node)
    #         #     # out-edges
    #         #     for u, v, edge_duration in G.edges_iter(node, data=True):
    #         #         print('u, v, edge_duration (out)', u, v, edge_duration)
    #         #         G.remove_edge(u, v)
    #         #         edges_removed.append((u, v, edge_duration))
    #         #
    #         #     if G.is_directed():
    #         #         # in-edges
    #         #         for u, v, edge_duration in G.in_edges_iter(node, data=True):
    #         #             print('u, v, edge_duration (in)', u, v, edge_duration)
    #         #             G.remove_edge(u, v)
    #         #             edges_removed.append((u, v, edge_duration))
    #
    #         try:
    #             # Calculate the spur path from the spur node to the target
    #             spur_path_duration, spur_path = nx.bidirectional_dijkstra(G, spur_node, target)
    #             # Entire path is made up of the root path and spur path
    #             total_path = root_path[:-1] + spur_path
    #             total_path_duration = root_path_duration + spur_path_duration
    #             potential_k = tuple([total_path_duration, total_path])
    #             # Add the potential k-shortest path to the heap
    #             if potential_k not in B:
    #                 B.append(potential_k)
    #                 # print('potential_k', potential_k)
    #         except nx.NetworkXNoPath:
    #             # print('NetworkXNoPath')
    #             pass
    #
    #         # Add back the edges and nodes that were removed from the graph
    #         for u, v, edge_duration in edges_removed:
    #             G.add_edge(u, v, weight=edge_duration)
    #             # print('u, v, edge_duration (add)', u, v, edge_duration)
    #
    #     if len(B):
    #         B = sorted(B, key=lambda e: e[0])
    #         A.append(B[0])
    #         B.pop(0)
    #     else:
    #         break

    dur = 2
    sample = np.random.normal(dur, dur * 0.2236)
    # while sample < 0:
    #     sample = np.random.normal(dur, dur * 0.2236)
