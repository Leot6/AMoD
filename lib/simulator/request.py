"""
definition of requests for the AMoD system
"""

import matplotlib.pyplot as plt
from lib.simulator.config import MAX_WAIT, MAX_DELAY, MAX_DETOUR
from lib.routing.routing_server import get_duration_from_origin_to_dest


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
        Etp: estimated pickup time
        Etd: estimated dropoff time
        Tp: actually pickup time
        Td: actually dropoff time
        D: detour factor
    """

    def __init__(self, id, Tr, onid, dnid, olng, olat, dlng, dlat):
        self.id = id
        self.Tr = Tr
        self.onid = onid
        self.dnid = dnid
        self.olng = olng
        self.olat = olat
        self.dlng = dlng
        self.dlat = dlat
        self.Ts = get_duration_from_origin_to_dest(self.onid, self.dnid)
        self.Cep = Tr
        if MAX_DETOUR == -1:
            self.Clp = Tr + MAX_WAIT
            self.Cld = Tr + self.Ts + MAX_DELAY
        else:
            self.Clp = Tr + min(MAX_WAIT, self.Ts * (2 - MAX_DETOUR))
            self.Cld = Tr + self.Ts + min(MAX_DELAY, self.Clp - Tr + self.Ts * (MAX_DETOUR - 1))
        self.Clp_backup = self.Clp
        self.Etp = -1.0
        self.Etd = -1.0
        self.Tp = -1.0
        self.Td = -1.0
        self.D = 0.0

    # return origin
    def get_origin(self):
        return self.onid, self.olng, self.olat

    # return destination
    def get_destination(self):
        return self.dnid, self.dlng, self.dlat

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
