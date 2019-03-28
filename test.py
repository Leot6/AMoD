import time
import math
import requests
import pandas as pd
import numpy as np
from tqdm import tqdm

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


def get_duration_from_table(onid, dnid):
    return travel_time_table[onid-1, dnid-1]


def get_duration_from_table1(olng, olat, dlng, dlat):
    onid = find_nearest_node(olng, olat)
    dnid = find_nearest_node(dlng, dlat)
    return travel_time_table[onid-1, dnid-1]


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
    travel_time_table = pd.read_csv('data/travel-time-table.csv', index_col=0).values

    # print(travel_time_table[0, 0])
    # print(travel_time_table[0, 1])


    # onid = 3827
    # dnid = 3834
    # onlng = nodes[onid-1][1]
    # onlat = nodes[onid-1][2]
    # dnlng = nodes[dnid-1][1]
    # dnlat = nodes[dnid-1][2]
    #
    # print([onlng, onlat])
    # print([dnlng, dnlat])
    # print(get_duration(onlng, onlat, dnlng, dnlat))
    # print(get_duration_from_table1(onlng, onlat, dnlng, dnlat))




    # # 0.9 km
    # olng = -73.9983139038086
    # olat = 40.745506286621094
    # dlng = -73.98994445800781
    # dlat = 40.75670623779297
    # #
    # onid = find_nearest_node(olng, olat)
    # dnid = find_nearest_node(dlng, dlat)
    # onlng = nodes[onid-1][1]
    # onlat = nodes[onid-1][2]
    # dnlng = nodes[dnid-1][1]
    # dnlat = nodes[dnid-1][2]
    # print(onid, [onlng, onlat], dnid, [dnlng, dnlat])
    #
    # d = get_euclidean_distance(olng, olat, dlng, dlat)
    # print('distance form eu', d)
    # r = get_routing(olng, olat, dlng, dlat)
    # print('distance form osrm', r['distance'])
    # print('duration from osrm', r['duration'])
    # du = get_duration_from_table(onid, dnid)
    # print('duration from table', du)
    #
    # e1 = get_euclidean_distance(olng, olat, onlng, onlat)
    # e2 = get_euclidean_distance(dnlng, dnlat, dlng, dlat)
    # print('e1', e1, ', e2', e2)
    #
    # w1 = get_routing(olng, olat, onlng, onlat)
    # w2 = get_routing(dnlng, dnlat, dlng, dlat)
    # print('w1d', w1['distance'], ', w2d', w2['distance'])
    # print('w1d', w1['duration'], ', w2d', w2['duration'])




    # REQ_DATA = pd.read_csv('./data/Manhattan-taxi-20160501.csv')
    # for i in tqdm(range(1, 200000)):
    #     # print('req', i)
    #     olng = REQ_DATA.iloc[i]['olng']
    #     olat = REQ_DATA.iloc[i]['olat']
    #     dlng = REQ_DATA.iloc[i]['dlng']
    #     dlat = REQ_DATA.iloc[i]['dlat']
    #
    #     onid = find_nearest_node(olng, olat)
    #     dnid = find_nearest_node(dlng, dlat)
    #     # onlng = nodes[onid-1][1]
    #     # onlat = nodes[onid-1][2]
    #     # dnlng = nodes[dnid-1][1]
    #     # dnlat = nodes[dnid-1][2]
    #
    #     d_o = get_duration(olng, olat, dlng, dlat)
    #     d_t = get_duration_from_table(onid, dnid)
    #     # print(d_o, d_t)
    #
    #     # if abs(d_t-d_o) > 100:
    #     #     print(i, d_o, d_t, olng, olat)
    #     if onid == 3827 or onid == 3834 or onid == 3911 or onid == 3921:
    #         print([olng, olat], onid)
    #     elif dnid == 3827 or dnid == 3834 or dnid == 3911 or dnid == 3921:
    #         print([dlng, dlat], dnid)




    #
    # eee = time.time()
    # ed = get_euclidean_distance(olng, olat, dlng, dlat)
    # print('euclidean running time:', (time.time() - eee))
    # print(ed)
    #
    # ooo = time.time()
    # d = get_duration(olng, olat, dlng, dlat)
    # print('osrm running time:', (time.time() - ooo))
    # print(d)
    # #
    # nnn = time.time()
    # nid = find_nearest_node(olng, olat)
    # print(nid)
    # print('nearest running time:', (time.time() - nnn))
    #
    # ttt = time.time()
    # t = get_duration_from_table(onid, dnid)
    # print('table running time:', (time.time() - ttt))
    #
    # ttt1 = time.time()
    # t1 = get_duration_from_table1(olng, olat, dlng, dlat)
    # print('table1 running time:', (time.time() - ttt1))















