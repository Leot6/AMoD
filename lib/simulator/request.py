"""
definition of requests for the AMoD system
"""

import numpy as np
import matplotlib.pyplot as plt
from lib.simulator.config import MAX_WAIT, MAX_DELAY, MAX_DETOUR
from lib.routing.routing_server import get_duration_from_origin_to_dest, get_distance_from_origin_to_dest


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
        Ds: shortest travel distance
        Cep: constraint - earliest pickup
        Clp: constraint - latest pickup
        Cld: constraint - latest dropoff
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
        self.Ds = get_distance_from_origin_to_dest(self.onid, self.dnid)
        self.Cep = Tr
        if MAX_DETOUR == 0 or MAX_DETOUR == np.inf:
            self.Clp = Tr + MAX_WAIT
            self.Cld = Tr + self.Ts + MAX_DELAY
        else:
            self.Clp = Tr + min(MAX_WAIT, self.Ts * (2 - MAX_DETOUR))
            self.Cld = Tr + self.Ts + min(MAX_DELAY, self.Clp - Tr + self.Ts * (MAX_DETOUR - 1))
        self.Clp_backup = self.Clp
        self.Tp = -1.0
        self.Td = -1.0
        self.D = 0.0
        self.base_fee = round(self.Ds / 1000 * 2, 2)
        self.price_est = self.base_fee
        self.price_act = self.base_fee

    def update_price_est(self, extra_delay_est):
        self.price_est = round(self.base_fee - extra_delay_est * 0.02, 2)

    def update_price_act(self, extra_delay_act):
        self.price_act = round(self.base_fee - extra_delay_act * 0.02, 2)

    def update_pick_info(self, t):
        self.Tp = t

    def update_drop_info(self, t):
        self.Td = t
        self.D = (self.Td - self.Tp) / self.Ts

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
