"""
defination of routes for the AMoD system
"""

import time
import math
import copy
import requests
import numpy as np
import networkx as nx
from collections import deque
from heapq import heappush, heappop
from itertools import count
from lib.Configure import NOD_LOC, NOD_TTT, NET_NYC, COEF_TRAVEL

G = copy.deepcopy(NET_NYC)


class Step(object):
    """
    Step is a class for steps in a leg
    Attributes:
        t: duration
        d: distance
        geo: geometry, a list of coordinates
    """

    def __init__(self, t=0.0, d=0.0, geo=[], nid=[]):
        self.t = t
        self.d = d
        self.geo = geo
        self.nid = nid

    def __str__(self):
        return 'step: distance = %.1f, duration = %.1f' % (self.d, self.t)


class Leg(object):
    """
    Leg is a class for legs in the route
    A leg may consists of a series of steps
    Attributes:
        rid: request id (if rebalancing then -1)
        pod: pickup (+1) or dropoff (-1), rebalancing (0)
        tlng: target (end of leg) longitude
        tlat: target (end of leg) latitude
        nid: target nearest node id in network
        ddl: latest arriving time
        t: total duration
        d: total distance
        steps: a list of steps
    """

    def __init__(self, rid, pod, tlng, tlat, tnid, ddl, t=0.0, d=0.0, steps=[]):
        self.rid = rid
        self.pod = pod
        self.tlng = tlng
        self.tlat = tlat
        self.tnid = tnid
        self.ddl = ddl
        self.t = t
        self.d = d
        self.steps = deque(steps)

    def __str__(self):
        return 'leg: distance = %.1f, duration = %.1f, number of steps = %d' % (self.d, self.t, len(self.steps))


# get the duration of the best route from origin to destination
def get_duration(olng, olat, dlng, dlat, onid, dnid):
    # duration = get_duration_from_osrm(olng, olat, dlng, dlat)
    duration = get_duration_from_table(onid, dnid)
    return duration


# get the duration of the best route from origin to destination
def get_routing(olng, olat, dlng, dlat, onid, dnid):
    route = get_routing_from_osrm(olng, olat, dlng, dlat)
    # route = get_routing_from_networkx(onid, dnid)
    return route


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
def get_routing_from_osrm(olng, olat, dlng, dlat):
    url = create_url(olng, olat, dlng, dlat, steps='true', annotations='false')
    response, code = call_url(url)
    if code:
        return response['routes'][0]['legs'][0]
    else:
        return None


# get the duration of the best route from origin to destination
def get_duration_from_osrm(olng, olat, dlng, dlat):
    url = create_url(olng, olat, dlng, dlat, steps='false', annotations='false')
    response, code = call_url(url)
    if code:
        return response['routes'][0]['duration'] * COEF_TRAVEL
    else:
        return None


# get the duration of the best route from origin to destination
def get_duration_from_table(onid, dnid):
    duration = NOD_TTT[onid - 1, dnid - 1]
    if duration != -1:
        return duration * COEF_TRAVEL
    else:
        None


# get the best route from origin to destination
def get_routing_from_networkx(onid, dnid):
    duration, path = nx.bidirectional_dijkstra(G, onid, dnid)
    duration = duration * COEF_TRAVEL
    distance = 0.0
    steps = []
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        u_geo = [NOD_LOC[u - 1][1], NOD_LOC[u - 1][2]]
        v_geo = [NOD_LOC[v - 1][1], NOD_LOC[v - 1][2]]
        d = get_haversine_distance(u_geo[0], u_geo[1], v_geo[0], v_geo[1])
        # t = NOD_TTT[u - 1, v - 1] * COEF_TRAVEL
        t = G.get_edge_data(u, v, default={'weight': np.inf})['weight'] * COEF_TRAVEL
        steps.append((t, d, [u_geo, v_geo], [u, v]))
        distance += d
    dnid_geo = [NOD_LOC[dnid - 1][1], NOD_LOC[dnid - 1][2]]
    steps.append((0.0, 0.0, [dnid_geo, dnid_geo], [dnid, dnid]))
    assert np.isclose(duration, sum([s[0] for s in steps]))
    return duration, distance, steps


# update the traffic on road network
def upd_traffic_on_network():
    for u, v in G.edges():
        dur = NET_NYC.get_edge_data(u, v, default={'weight': np.inf})['weight']
        if dur is not np.inf:
            sample = np.random.normal(dur, dur * 0.2236)
            while sample < 0:
                sample = np.random.normal(dur, dur * 0.2236)
            G.edges[u, v]['weight'] = sample


# get the duration based on haversine formula
def get_haversine_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


# find the nearest node to[lng, lat] in Manhattan network
def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in NOD_LOC:
        # d_ = get_haversine_distance(lng, lat, nlng, nlat)
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


# returns the k-shortest paths from source to target in a weighted graph G
def k_shortest_paths(G, source, target, k=1):
    # Determine the shortest path from the source to the target
    duration, path = nx.bidirectional_dijkstra(G, source, target)
    A = [tuple([duration, path])]  # k_shortest_paths
    B = []
    # G_copy = G.copy()  # computational time might be long

    for i in range(1, k):
        i_path = A[-1][1]  # k-1 shortest path
        #  The spur node ranges from the first node to the next to last node in the previous k-shortest path
        for j in range(len(i_path) - 1):
            # Spur node is retrieved from the previous k-shortest path, k − 1.
            spur_node = i_path[j]
            root_path = i_path[:j + 1]

            root_path_duration = 0
            for u_i in range(len(root_path) - 1):
                u = root_path[u_i]
                v = root_path[u_i + 1]
                root_path_duration += G.edges[u, v]['weight']

            # print('root_path', root_path)
            # print('root_path_duration', root_path_duration)

            edges_removed = []
            for path_k in A:
                curr_path = path_k[1]
                # Remove the links that are part of the previous shortest paths which share the same root path
                if len(curr_path) > j and root_path == curr_path[:j + 1]:
                    u = curr_path[j]
                    v = curr_path[j + 1]
                    if G.has_edge(u, v):
                        edge_duration = G.edges[u, v]['weight']  # need to be compared to NOD_TTT
                        G.remove_edge(u, v)
                        edges_removed.append((u, v, edge_duration))
                        # print('u, v, edge_duration (remove)', u, v, edge_duration)

            # # remove rootPathNode (except spurNode) from Graph (seems not necessary)
            # for n in range(len(root_path) - 1):
            #     node = root_path[n]
            #     print('node', node)
            #     # out-edges
            #     for u, v, edge_duration in G.edges_iter(node, data=True):
            #         print('u, v, edge_duration (out)', u, v, edge_duration)
            #         G.remove_edge(u, v)
            #         edges_removed.append((u, v, edge_duration))
            #
            #     if G.is_directed():
            #         # in-edges
            #         for u, v, edge_duration in G.in_edges_iter(node, data=True):
            #             print('u, v, edge_duration (in)', u, v, edge_duration)
            #             G.remove_edge(u, v)
            #             edges_removed.append((u, v, edge_duration))

            try:
                # Calculate the spur path from the spur node to the target
                spur_path_duration, spur_path = nx.bidirectional_dijkstra(G, spur_node, target)
                # Entire path is made up of the root path and spur path
                total_path = root_path[:-1] + spur_path
                total_path_duration = root_path_duration + spur_path_duration
                potential_k = tuple([total_path_duration, total_path])
                # Add the potential k-shortest path to the heap
                if potential_k not in B:
                    B.append(potential_k)
                    # print('potential_k', potential_k)
            except nx.NetworkXNoPath:
                # print('NetworkXNoPath')
                pass

            # Add back the edges and nodes that were removed from the graph
            for u, v, edge_duration in edges_removed:
                G.add_edge(u, v, weight=edge_duration)
                # print('u, v, edge_duration (add)', u, v, edge_duration)

        if len(B):
            B = sorted(B, key=lambda e: e[0])
            A.append(B[0])
            B.pop(0)
        else:
            break
    return A






