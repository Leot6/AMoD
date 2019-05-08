"""
defination of routes for the AMoD system
"""

import time
import math
import requests
import numpy as np
import networkx as nx
from collections import deque
from lib.Configure import NOD_LOC, NOD_TTT, NET_NYC, COEF_TRAVEL


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
    duration, path = nx.bidirectional_dijkstra(NET_NYC, onid, dnid)
    distance = 0.0
    path.append(path[-1])
    steps = []
    for i in range(len(path) - 1):
        src = path[i]
        sink = path[i + 1]
        src_geo = [NOD_LOC[src - 1][1], NOD_LOC[src - 1][2]]
        sink_geo = [NOD_LOC[sink - 1][1], NOD_LOC[sink - 1][2]]
        d = get_euclidean_distance(src_geo[0], src_geo[1], sink_geo[0], sink_geo[1])
        t = NOD_TTT[src - 1, sink - 1]
        steps.append((t, d, [src_geo, sink_geo], [src, sink]))
        distance += d
    assert np.isclose(duration, sum([s[0] for s in steps]))

    # debug
    # if True:
    #     print(duration, len(path), (onid, dnid))
        # for step in steps:
        #     print('  ', step)

    return duration, distance, steps


# get the duration based on Euclidean distance
def get_euclidean_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


# find the nearest node to[lng, lat] in Manhattan network
def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in NOD_LOC:
        # d_ = get_euclidean_distance(lng, lat, nlng, nlat)
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



