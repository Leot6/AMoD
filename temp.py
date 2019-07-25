import mosek
import time
import requests
import pickle
import random
import copy
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from tqdm import tqdm
from itertools import islice
from lib.Configure import MAP_WIDTH, MAP_HEIGHT, Olng, Olat, Dlng, Dlat


def IsPtInPoly(lng, lat):
    # coordinates around Manhattan
    point_list = area
    iSum = 0
    iCount = len(point_list)

    if iCount < 3:
        return False

    for i in range(iCount):
        # vlng: vertex longtitude,  vlat: vertex latitude

        vlng1 = point_list[i][0]
        vlat1 = point_list[i][1]

        if i == iCount - 1:
            vlng2 = point_list[0][0]
            vlat2 = point_list[0][1]
        else:
            vlng2 = point_list[i + 1][0]
            vlat2 = point_list[i + 1][1]

        if ((lat >= vlat1) and (lat < vlat2)) or ((lat >= vlat2) and (lat < vlat1)):
            if abs(vlat1 - vlat2) > 0:
                pLon = vlng1 - ((vlng1 - vlng2) * (vlat1 - lat)) / (vlat1 - vlat2)
                if pLon < lng:
                    iSum += 1

    if iSum % 2 != 0:
        return True
    else:
        return False


def get_path_from_SPtable(onid, dnid):
    path = [dnid]
    pre_node = NOD_SPT[onid - 1, dnid - 1]
    while pre_node > 0:
        path.append(pre_node)
        pre_node = NOD_SPT[onid - 1, pre_node - 1]
    path.reverse()
    return path


# get the duration of a path
def get_dur_from_path(path):
    dur = 0
    for node_idx in range(len(path) - 1):
        u = path[node_idx]
        v = path[node_idx + 1]
        dur += G.edges[u, v]['dur']
    return dur


def k_shortest_paths_nx(source, target, k, weight='dur'):
    return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))


# find the nearest node to[lng, lat] in Manhattan network
def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in NOD_LOC:
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


def test_trip_path():
    with open('./data/REQ_DATA.pickle', 'rb') as f:
        REQ_DATA = pickle.load(f)
    test_list = set()
    pair_list = set()
    for req_idx in tqdm(range(100000), desc='test times'):
        olng = REQ_DATA.iloc[req_idx]['olng']
        olat = REQ_DATA.iloc[req_idx]['olat']
        dlng = REQ_DATA.iloc[req_idx]['dlng']
        dlat = REQ_DATA.iloc[req_idx]['dlat']
        onid = find_nearest_node(olng, olat)
        dnid = find_nearest_node(dlng, dlat)
        KSP = k_shortest_paths_nx(onid, dnid, 10, 'dur')
        tt = []
        for path in KSP:
            mean = 0
            variance = 0.0
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                mean += G.edges[u, v]['dur']
                variance += np.square(G.edges[u, v]['std'])
            standard_deviation = np.sqrt(variance)
            mean = round(mean, 2)
            thre = round(mean + 1.5 * standard_deviation, 2)
            tt.append([mean, thre, path])
        tt.sort(key=lambda e: e[0])
        aaaa = tt[0][1]
        tt1 = sorted(tt, key=lambda e: e[1])
        bbbb = tt1[0][1]
        test_list.add(req_idx)
        if aaaa > bbbb + 5:
            pair_list.add(req_idx)
            print('trip found:', [onid, dnid], ' travel time:', aaaa, bbbb,
                  ' found pair:', len(pair_list), '/', len(test_list))


def plot_path(onid, dnid, paths):
    fig = plt.figure(figsize=(MAP_WIDTH, MAP_HEIGHT))
    plt.xlim((Olng, Dlng))
    plt.ylim((Olat, Dlat))
    img = mpimg.imread('map.png')
    plt.imshow(img, extent=[Olng, Dlng, Olat, Dlat], aspect=(Dlng - Olng) / (Dlat - Olat) * MAP_HEIGHT / MAP_WIDTH)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    # [olng, olat] = G.nodes[onid]['pos']
    # [dlng, dlat] = G.nodes[dnid]['pos']
    # plt.scatter(olng, olat)
    # plt.scatter(dlng, dlat)
    for index, path in zip(range(len(paths)), paths):
        x = []
        y = []
        for node in path:
            [lng, lat] = G.nodes[node]['pos']
            x.append(lng)
            y.append(lat)
        if index == 0 or index == 1:
            plt.plot(x, y, marker='.')
        # else:
        #     plt.plot(x, y, '--')
        # if (index % 2) == 0:
        #     # the shortest path
        #     plt.plot(x, y, marker='.')
        # # else:
        # #     # higher probability path
        # #     plt.plot(x, y, '--')

    a = [area[-1][0]]
    b = [area[-1][1]]
    for node in area:
        a.append(node[0])
        b.append(node[1])
    plt.plot(a, b, 'r--')
    plt.show()


if __name__ == "__main__":

    area = [(-73.98483, 40.75481), (-73.97973, 40.75278), (-73.98101, 40.75006), (-73.98638, 40.75222)]
    NOD_LOC = pd.read_csv('./data/nodes.csv').values.tolist()
    with open('./data/NET_NYC.pickle', 'rb') as f:
        G = pickle.load(f)
    with open('./data/NOD_SPT.pickle', 'rb') as f:
        NOD_SPT = pickle.load(f)
    with open('./data/NOD_TTT.pickle', 'rb') as f:
        NOD_TTT = pickle.load(f)

    onid = 800
    dnid = 2300

    # path = get_path_from_SPtable(onid, dnid)
    # print(get_dur_from_path(path))
    # KSP = [path]

    aa = time.time()
    KSP = k_shortest_paths_nx(onid, dnid, 10, 'dur')
    print('find k shortest paths running time:', (time.time() - aa))

    tt = []
    for path in KSP:
        # print()
        # print()
        mean = 0
        variance = 0.0
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            mean += G.edges[u, v]['dur']
            [olng, olat] = G.nodes[u]['pos']
            [dlng, dlat] = G.nodes[v]['pos']
            if IsPtInPoly(olng, olat) and IsPtInPoly(dlng, dlat):
                variance += 3*np.square(G.edges[u, v]['std'])
            variance += np.square(G.edges[u, v]['std'])
        standard_deviation = np.sqrt(variance)
        mean = round(mean, 2)
        thre = round(mean + 1.5 * standard_deviation, 2)
        tt.append([mean, thre])
    tt.sort(key=lambda e: e[0])
    aaaa = tt[0][1]
    for i in range(2):
        print('t1', tt[i], round((thre / mean - 1) * 100, 2), '%')
    tt.sort(key=lambda e: e[1])
    bbbb = tt[0][1]
    for i in range(2):
        print('t2', tt[i], round((thre / mean - 1) * 100, 2), '%')
    if aaaa != bbbb:
        print('path found:', [onid, dnid], ' travel time:', aaaa, bbbb)

    bb = time.time()
    plot_path(onid, dnid, KSP)
    print('plot k shortest paths running time:', (time.time() - bb))
    #
    # # random test any node pair
    # paths = []
    # mo = 2
    # if mo == 1:
    #     mode = '(std)'
    # elif mo == 2:
    #     mode = '(std, t<25m)'
    # nid_list = list(range(1, 4092))
    # test_list = set()
    # pair_list = set()
    # for i in tqdm(range(50000), desc='test times'+mode):
    #     onid = random.choice(nid_list)
    #     dnid = random.choice(nid_list)
    #     if mo == 3 and NOD_TTT[onid - 1, dnid - 1] > 200:
    #         continue
    #     KSP = k_shortest_paths_nx(onid, dnid, 10, 'dur')
    #     tt = []
    #     for path in KSP:
    #         mean = 0
    #         variance = 0.0
    #         for i in range(len(path) - 1):
    #             u = path[i]
    #             v = path[i + 1]
    #             mean += G.edges[u, v]['dur']
    #             variance += np.square(G.edges[u, v]['std'])
    #         standard_deviation = np.sqrt(variance)
    #         mean = round(mean, 2)
    #         thre = round(mean + 1.5 * standard_deviation, 2)
    #         tt.append([mean, thre, path])
    #     tt.sort(key=lambda e: e[0])
    #     aaaa = tt[0][1]
    #     tt1 = sorted(tt, key=lambda e: e[1])
    #     bbbb = tt1[0][1]
    #     test_list.add((onid, dnid))
    #     if aaaa > bbbb + 5:
    #         pair_list.add((onid, dnid))
    #         paths.append(tt[0][2])
    #         paths.append(tt1[0][2])
    #         print('path found:', [onid, dnid], ' travel time:', aaaa, bbbb,
    #               ' found pair:', len(pair_list), '/', len(test_list))
    #
    # plot_path(onid, dnid, paths)

    # test_trip_path()





