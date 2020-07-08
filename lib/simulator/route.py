"""
definition of routes for the AMoD system
"""

from collections import deque


class Step(object):
    """
    Step is a class for steps in a leg
    Attributes:
        t: duration
        d: distance
        nid: a list of nodes id
        geo: geometry, a list of coordinates
    """

    def __init__(self, t=0.0, d=0.0, nid=[], geo=[]):
        self.t = t
        self.d = d
        self.nid = nid
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
        tnid: target (end of leg) node id in network
        ept: earliest possible arrival time
        ddl: latest arriving time
        t: total duration
        d: total distance
        steps: a list of steps
    """

    def __init__(self, rid, pod, tnid, ept, ddl, t=0.0, d=0.0, steps=[]):
        self.rid = rid
        self.pod = pod
        self.tnid = tnid
        self.ept = ept
        self.ddl = ddl
        self.t = t
        self.d = d
        self.steps = deque(steps)

    def __str__(self):
        return 'leg: distance = %.1f, duration = %.1f, number of steps = %d' % (self.d, self.t, len(self.steps))

