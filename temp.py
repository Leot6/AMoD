import mosek
import time
import requests
import pickle
import numpy as np
import pandas as pd
import networkx as nx
from tqdm import tqdm
from time import sleep



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


if __name__ == "__main__":

    # with open('NOD_SPT.pickle', 'rb') as f:
    #     SPT = pickle.load(f)
    #
    # print(SPT)
    # SPT = SPT.values
    #
    # aa = time.time()
    #
    # c = SPT[0, 0].replace('[', '').replace(']', '').split(', ')
    # dur = float(c[0])
    # path = list(map(int, c[1:]))
    #
    # print('aa running time:', (time.time() - aa))
    # print(dur, path)

    with open('./data/NET_NYC.pickle', 'rb') as f:
        G = pickle.load(f)
    time1 = time.time()
    print('computing all pairs dijkstra...')
    len_path = dict(nx.all_pairs_dijkstra(G, cutoff=None, weight='weight'))
    print('all_pairs_dijkstra running time : %.05f seconds' % (time.time() - time1))

    print(len_path[799][1][811], len_path[799][0][811])

    # NOD_LOC = pd.read_csv('./data/nodes.csv')
    # nodes_id = list(range(1, NOD_LOC.shape[0] + 1))
    # num_nodes = len(nodes_id)
    # NOD_SPT = pd.DataFrame(-np.ones((num_nodes, num_nodes)), index=nodes_id, columns=nodes_id)
    #
    # # paths = []
    #
    # for o in tqdm(nodes_id):
    #     for d in tqdm(nodes_id):
    #         try:
    #             # aa = time.time()
    #
    #             # duration = round(len_path[o][0][d], 2)
    #             path = len_path[o][1][d]
    #             if len(path) == 1 or len(path) == 2:
    #                 continue
    #             if len(path) == 3:
    #                 pp = path[1]
    #             else:
    #                 u_1 = path[1]
    #                 v_1 = path[-2]
    #                 pp = u_1 * 10000 + v_1
    #
    #             NOD_SPT.iloc[o - 1, d - 1] = pp
    #
    #             # paths.append(path)
    #             # item = str(duration)
    #             # item = str([duration, path])
    #             # print('aa1 running time:', (time.time() - aa))
    #             # duration = 238711119999999922223333444555
    #             # NOD_SPT.iloc[o - 1, d - 1] = duration
    #             # NOD_SPT[o - 1, d - 1] = item
    #             # print('aa2 running time:', (time.time() - aa))
    #
    #         except nx.NetworkXNoPath:
    #             print('no path between', o, d)
    #
    # # paths = sorted(paths, key=lambda p: len(p))
    # # print(len(paths))
    # # print(paths[-1])
    # # with open('NOD_SPT.pickle', 'wb') as f:
    # #     pickle.dump(NOD_SPT, f)
    # #
    # NOD_SPT.to_csv('NOD_SPT.csv')


