import time
import math
import requests
import pandas as pd
import numpy as np
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


# def find_nearest_node(lng, lat):
#     nearest_node_id = 1
#     d = np.inf
#     nearest_node_id1 = 1
#     d1 = np.inf
#
#     for nid, nlng, nlat in nodes:
#         d_ = get_euclidean_distance(lng, lat, nlng, nlat)
#         if d_ < d:
#             d = d_
#             nearest_node_id = nid
#
#         # d1_ = abs(lng-nlng) + abs(lat-nlat)
#         # if d1_ < d1:
#         #     d1 = d1_
#         #     nearest_node_id1 = nid
#
#     nearest_node_id = int(nearest_node_id)
#     nearest_node_id1 = int(nearest_node_id1)
#
#     # if d > 150:
#     #     print('distance to node is larger than 150m!!!!!!!!')
#     #     print([round(lng, 6), round(lat, 6)], int(nearest_node_id), round(d, 2))
#     #
#     # if nearest_node_id != nearest_node_id1:
#     #     d1 = get_euclidean_distance(lng, lat, nodes[nearest_node_id1-1][1], nodes[nearest_node_id1-1][2])
#     #     print('   !!!!!!!!!not the same:', nearest_node_id, d, nearest_node_id1, d1)
#
#     return int(nearest_node_id)

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

    node_id = find_nearest_node(-73.99002075195312, 40.73868179321289)
    print(node_id)



