"""
definition of requests for the AMoD system
"""

import numpy as np
import matplotlib.pyplot as plt
from src.simulator.config import MAX_PICKUP_WAIT_TIME_MIN, MAX_ONBOARD_DETOUR
from src.simulator.router_func import get_duration_from_origin_to_dest, get_distance_from_origin_to_dest
from src.simulator.types import OrderStatus


class Req(object):
    """
    Req is a class for requests
    Attributes:
        id: sequential unique id
        Tr: request time
        onid: nearest origin node id in network
        dnid: nearest destination node id in network
        Ts: shortest travel time
        Ds: shortest travel distance
        Clp: constraint - latest pickup
        Cld: constraint - latest dropoff
        Tp: actually pickup time
        Td: actually dropoff time
        D: detour factor
    """

    def __init__(self, id: int, Tr: int, onid: int, dnid: int):
        self.id = id
        self.status = OrderStatus.PENDING
        self.Tr = Tr
        self.onid = onid
        self.dnid = dnid
        self.Ts = get_duration_from_origin_to_dest(self.onid, self.dnid)
        self.Ds = get_distance_from_origin_to_dest(self.onid, self.dnid)
        self.Clp = Tr + min(MAX_PICKUP_WAIT_TIME_MIN * 60, self.Ts * (2 - MAX_ONBOARD_DETOUR))
        self.Cld = \
            Tr + self.Ts + min(MAX_PICKUP_WAIT_TIME_MIN * 60 * 2, self.Clp - Tr + self.Ts * (MAX_ONBOARD_DETOUR - 1))
        self.Clp_backup = self.Clp
        self.Tp = -1.0
        self.Td = -1.0
        self.D = 0.0

    def update_pick_info(self, t: int):
        self.Tp = t
        assert (self.status == OrderStatus.PICKING)
        self.status = OrderStatus.ONBOARD

    def update_drop_info(self, t: int):
        self.Td = t
        self.D = (self.Td - self.Tp) / self.Ts
        assert(self.status == OrderStatus.ONBOARD)
        self.status = OrderStatus.COMPLETE
