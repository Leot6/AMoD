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
with open('./data/NOD_TTT.pickle', 'rb') as f:
    NOD_TTT = pickle.load(f)


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


def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in nodes:
        # d_ = get_haversine_distance(lng, lat, nlng, nlat)
        d_ = abs(lng-nlng) + abs(lat-nlat)
        if d_ < d:
            d = d_
            nearest_node_id = nid
    # if d > 150:
    #     print('distance of', [lng, lat], 'to node', nearest_node_id, 'is larger than 100m!!!!!!!!')
    return int(nearest_node_id)


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

    # olng = -74.017946
    # olat = 40.706991
    # dlng = -74.016979
    # dlat = 40.709037
    #
    olng = -74.016765
    olat = 40.709333
    # dlng = -74.016375
    # dlat = 40.710085

    # dlng = -73.931773
    # dlat = 40.800979

    dlng = -74.016765
    dlat = 40.709333

    onid = find_nearest_node(olng, olat)
    dnid = find_nearest_node(dlng, dlat)

    with open('./data/NET_NYC.pickle', 'rb') as f:
        NET_NYC = pickle.load(f)

    onid = 3525
    dnid = 3683

    bb = time.time()
    duration, path = nx.bidirectional_dijkstra(NET_NYC, onid, dnid)
    distance = 0.0
    path.append(path[-1])
    steps = []
    for i in range(len(path)-1):
        src = path[i]
        sink = path[i+1]
        src_geo = [nodes[src - 1][1], nodes[src - 1][2]]
        sink_geo = [nodes[sink - 1][1], nodes[sink - 1][2]]
        t = NOD_TTT[src - 1, sink - 1]
        d = get_haversine_distance(src_geo[0], src_geo[1], sink_geo[0], sink_geo[1])
        steps.append((t, d, [src_geo, sink_geo], [src, sink]))
        distance += d
    print(duration, path)
    print(sum([s[0] for s in steps]), sum([s[1] for s in steps]))
    assert np.isclose(duration, sum([s[0] for s in steps]))
    # for step in steps:
    #     print('  ', step)
    
    print('bb running time:', (time.time() - bb))







