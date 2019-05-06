import time
import math
import requests
import pickle
import pandas as pd
import numpy as np
import networkx as nx

from tqdm import tqdm
from collections import deque


nodes = pd.read_csv('data/nodes.csv').values.tolist()


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


def get_euclidean_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in nodes:
        # d_ = get_euclidean_distance(lng, lat, nlng, nlat)
        d_ = abs(lng-nlng) + abs(lat-nlat)
        if d_ < d:
            d = d_
            nearest_node_id = nid
    # if d > 150:
    #     print('distance of', [lng, lat], 'to node', nearest_node_id, 'is larger than 100m!!!!!!!!')
    return int(nearest_node_id)


def test():
    row = np.array([0, 0, 0, 1, 2, 3, 6])
    col = np.array([1, 2, 3, 4, 5, 6, 7])
    value = np.array([1, 2, 1, 8, 1, 3, 5])

    print('生成一个空的有向图')
    G = nx.DiGraph()
    print('为这个网络添加节点...')
    for i in range(0, np.size(col) + 1):
        G.add_node(i)
    print('在网络中添加带权中的边...')
    for i in range(np.size(row)):
        G.add_weighted_edges_from([(row[i], col[i], value[i])])


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

    aa = time.time()
    # REQ_DATA = pd.read_csv('./data/Manhattan-taxi-20160507.csv')
    # STN_LOC = pd.read_csv('./data/stations-630.csv')
    # NOD_LOC = pd.read_csv('./data/nodes.csv').values.tolist()
    NOD_TTT = pd.read_csv('./data/travel-time-table.csv', index_col=0).values
    print('deque running time:', (time.time() - aa))

    # with open('./data/REQ_DATA.pickle', 'wb') as f:
    #     pickle.dump(REQ_DATA, f)
    # with open('./data/STN_LOC.pickle', 'wb') as f:
    #     pickle.dump(STN_LOC, f)
    # with open('./data/NOD_LOC.pickle', 'wb') as f:
    #     pickle.dump(NOD_LOC, f)
    with open('./data/NOD_TTT.pickle', 'wb') as f:
        pickle.dump(NOD_TTT, f)

    bb = time.time()
    # with open('./data/REQ_DATA.pickle', 'rb') as f:
    #     REQ_DATA = pickle.load(f)
    # with open('./data/STN_LOC.pickle', 'rb') as f:
    #     STN_LOC = pickle.load(f)
    # with open('./data/NOD_LOC.pickle', 'rb') as f:
    #     NOD_LOC = pickle.load(f)
    with open('./data/NOD_TTT.pickle', 'rb') as f:
        NOD_TTT = pickle.load(f)

    print('deque running time:', (time.time() - bb))











