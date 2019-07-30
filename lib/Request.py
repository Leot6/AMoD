"""
definition of requests for the AMoD system
"""

import matplotlib.pyplot as plt
from lib.Configure import MAX_WAIT, MAX_DELAY, MAX_DETOUR
from lib.Route import find_nearest_node, get_duration


class Req(object):
    """
    Req is a class for requests
    Attributes:
        id: sequential unique id
        Tr: request time
        olng: origin longtitude
        olat: origin latitude
        dlng: destination longtitude
        dlat: destination latitude
        onid: nearest origin node id in network
        dnid: nearest destination node id in network
        Ts: shortest travel time
        Cep: constraint - earliest pickup
        Clp: constraint - latest pickup
        Cld: constraint - latest dropoff
        Tp: pickup time
        Td: dropoff time
        D: detour factor
    """

    def __init__(self, id, Tr, olng, olat, dlng, dlat):
        self.id = id
        self.Tr = Tr
        self.olng = olng
        self.olat = olat
        self.dlng = dlng
        self.dlat = dlat
        self.onid = find_nearest_node(olng, olat)
        self.dnid = find_nearest_node(dlng, dlat)
        self.Ts = get_duration(self.onid, self.dnid)
        self.Cep = Tr
        # self.Clp = Tr + MAX_WAIT
        # self.Cld = Tr + self.Ts + MAX_DELAY
        self.Clp = Tr + min(MAX_WAIT, self.Ts * (2-MAX_DETOUR))
        self.Cld = Tr + self.Ts + min(MAX_DELAY, self.Clp - Tr + self.Ts * (MAX_DETOUR-1))
        self.Tp = -1.0
        self.Td = -1.0
        self.D = 0.0

    # return origin
    def get_origin(self):
        return self.olng, self.olat

    # return destination
    def get_destination(self):
        return self.dlng, self.dlat

    # visualize
    def draw(self):
        plt.plot(self.olng, self.olat, 'r', marker='+')
        plt.plot(self.dlng, self.dlat, 'r', marker='x')
        plt.plot([self.olng, self.dlng], [self.olat, self.dlat], 'r', linestyle='--', dashes=(0.5, 1.5))

    def __str__(self):
        str = 'req %d from (%.7f, %.7f) to (%.7f, %.7f) at t = %.3f' % (
            self.id, self.olng, self.olat, self.dlng, self.dlat, self.Tr)
        str += '\n  latest pickup at t = %.3f, latest dropoff at t = %.3f' % (self.Clp, self.Cld)
        str += '\n  pickup at t = %.3f, dropoff at t = %.3f' % (self.Tp, self.Td)
        return str


class Trip(object):
    """
    Trip is a group of requests that can be served together by a single vehicle
    Attributes:
        reqs: a group of requests
        sche: the optimal schedule
        cost: travel cost
        all_sches: a list of all feasible schedules
    """

    def __init__(self, reqs, sche, cost, all_sches=[]):
        self.reqs = reqs
        self.sche = sche
        self.cost = cost
        self.all_schedules = all_sches



