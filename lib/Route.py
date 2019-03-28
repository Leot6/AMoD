"""
defination of routes for the AMoD system
"""

import time
import math
import requests
import numpy as np
from collections import deque
from lib.Configure import NOD_LOC, NOD_TTT


class Step(object):
    """
    Step is a class for steps in a leg
    Attributes:
        d: distance
        t: duration
        geo: geometry, a list of coordinates
    """

    def __init__(self, d=0.0, t=0.0, geo=[]):
        self.d = d
        self.t = t
        self.geo = geo

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
        ddl: latest arriving time
        d: total distance
        t: total duration
        steps: a list of steps
    """

    def __init__(self, rid, pod, tlng, tlat, ddl, d=0.0, t=0.0, steps=[]):
        self.rid = rid
        self.pod = pod
        self.tlng = tlng
        self.tlat = tlat
        self.ddl = ddl
        self.d = d
        self.t = t
        self.steps = deque(steps)

    def __str__(self):
        return 'leg: distance = %.1f, duration = %.1f, number of steps = %d' % (self.d, self.t, len(self.steps))


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

    # onid = find_nearest_node(olng, olat)
    # dnid = find_nearest_node(dlng, dlat)
    # return NOD_TTT[onid-1, dnid-1]


def get_duration_from_table(onid, dnid):
    return NOD_TTT.iloc[onid - 1, dnid - 1]


# get the duration based on Euclidean distance
def get_euclidean_distance(olng, olat, dlng, dlat):
    dist = (6371000 * 2 * math.pi / 360 * np.sqrt((math.cos((olat + dlat) * math.pi / 360)
                                                   * (olng - dlng)) ** 2 + (olat - dlat) ** 2))
    return dist


def find_nearest_node(lng, lat):
    nearest_node_id = None
    d = np.inf
    for nid, nlng, nlat in NOD_LOC:
        # d_ = get_euclidean_distance(lng, lat, nlng, nlat)
        d_ = abs(lng-nlng) + abs(lat-nlat)
        if d_ < d:
            d = d_
            nearest_node_id = nid
    return int(nearest_node_id)



