"""
definition of routes for the AMoD system
"""

from collections import deque
from enum import Enum


##################################################################################
# Request (order) and Vehicle Status Types
##################################################################################
class OrderStatus(Enum):
    PENDING = 1
    PICKING = 2
    ONBOARD = 3
    COMPLETE = 4
    WALKAWAY = 5


class VehicleStatus(Enum):
    IDLE = 1
    WORKING = 2
    REBALANCING = 3


##################################################################################
# Dispatch Types
##################################################################################
class DispatcherMethod(Enum):
    SBA = 1
    OSP_NR = 2
    OSP = 3


class RebalancerMethod(Enum):
    NONE = 1
    RVS = 2
    NPO = 3


##################################################################################
# Route Types
##################################################################################
class Step(object):
    """
    Step is a class for steps in a leg
    Attributes:
        t: duration
        d: distance
        nid_pair: [origin_node_id, destination_node_id]
        geo_pair: [origin_node_geo, destination_node_geo]
    """

    def __init__(self, t=0.0, d=0.0, nid: [int, int] = [], geo: [[float, float], [float, float]] = []):
        self.t = t
        self.d = d
        self.nid_pair = nid
        self.geo_pair = geo


class Leg(object):
    """
    Leg is a class for legs in the route
    A leg may consists of a series of steps
    Attributes:
        rid: request id (if rebalancing then -1)
        pod: pickup (+1) or dropoff (-1), rebalancing (0)
        tnid: target (end of leg) node id in network
        ddl: latest arriving time
        t: total duration
        d: total distance
        steps: a list of steps
    """

    def __init__(self, rid: int, pod: int, tnid: int, ddl: int,
                 t: float = 0.0, d: float = 0.0,
                 steps: deque[Step] = []):
        self.rid = rid
        self.pod = pod
        self.tnid = tnid
        self.ddl = ddl
        self.t = t
        self.d = d
        self.steps = deque(steps)


##################################################################################
# Types Only Used For Loading Node and Request Info From Files
##################################################################################
class Pos(object):
    def __init__(self):
        self.node_id = 1  # Note: the node id starts from 1, for the provided manhattan data.
        self.lng = 0.0
        self.lat = 0.0


class RawRequest(object):
    def __init__(self):
        self.origin_node_id = 1
        self.destination_node_id = 2
        self.request_time_sec = 0
        self.request_time_date = "0000-00-00 00:00:00"