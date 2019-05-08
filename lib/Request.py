"""
defination of requests for the AMoD system
"""

import matplotlib.pyplot as plt
from lib.Configure import MAX_WAIT, MAX_DELAY, MAX_DETOUR
from lib.Route import find_nearest_node, get_duration_from_osrm, get_duration


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

    def __init__(self, id, Tr, olng=-0.162139, olat=51.490439, dlng=-0.104428, dlat=51.514180):
        self.id = id
        self.Tr = Tr
        self.olng = olng
        self.olat = olat
        self.dlng = dlng
        self.dlat = dlat
        self.onid = find_nearest_node(olng, olat)
        self.dnid = find_nearest_node(dlng, dlat)
        # self.Ts = get_duration_from_osrm(olng, olat, dlng, dlat)
        self.Ts = get_duration(olng, olat, dlng, dlat, self.onid, self.dnid)
        self.Cep = Tr
        self.Clp = Tr + MAX_WAIT if self.Ts * (MAX_DETOUR-1) > MAX_DELAY else Tr + self.Ts * (MAX_DETOUR -1) / 2
        # self.Cld = None
        self.Cld = Tr + self.Ts + MAX_DELAY if self.Ts * (MAX_DETOUR-1) > MAX_DELAY else Tr + self.Ts * MAX_DETOUR
        self.Tp = -1.0
        self.Td = -1.0
        self.D = 0.0

        # debug code starts
        # if id == 130:
        #     print()
        #     print('req', id)
        #     print('Tr', Tr)
        #     print('Ts', self.Ts)
        #     print('Clp', self.Clp)
        #     print('Cld', self.Cld)
        #     print()
        # debug code ends

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



