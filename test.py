import time
import math
import requests
import pickle
import pandas as pd
import numpy as np
import re
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

    with open('./data/NET_NYC.pickle', 'rb') as f:
        G = pickle.load(f)
    # G_original = copy.deepcopy(G)
    # with open('./data/NOD_TTT.pickle', 'rb') as f:
    #     NOD_TTT = pickle.load(f)
    # NOD_LOC = pd.read_csv('./data/nodes.csv')
    # nodes_id = list(range(1, NOD_LOC.shape[0] + 1))

    # nodes_id = list(range(1, 6))
    # num_nodes = len(nodes_id)

    aa = time.time()
    count = 0
    for u, v in G.edges():
        u_v = str(u) + str(v)
        if '0660' in u_v:
            print('not ok: ', u, v)
        # print(u_v)
        count += 1
        # if count > 3:
    #
    print('aa running time:', (time.time() - aa))
    print(count)

    bb = time.time()
    duration, path = nx.bidirectional_dijkstra(G, 21, 6)
    print('bb running time:', (time.time() - bb))
    print(duration, path)





