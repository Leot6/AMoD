"""
heuristic insertion: insert requests to vehicles in first-in-first-out manner
"""

import time
import copy
import numpy as np

from lib.A1_ScheduleFinder import compute_schedule


class HI(object):
    """
        HI is heuristic insertion dispatch algorithm
        Attributes:
            rid_assigned_last: the list of id of requests assigned in last dispatching period
        """

    def __init__(self):
        self.rid_assigned_last = set()

    def dispatch(self, vehs, queue, reqs, reqs_picking, rejs, T):
        l = len(queue)
        for i in range(l):
            req = queue.pop()
            if not self.insert_heuristics(vehs, req, reqs, reqs_picking, T):
                rejs.add(req)

    def insert_heuristics(self, vehs, req, reqs, reqs_picking, T):
        best_veh = None
        best_schedule = None
        min_cost = np.inf
        for veh in vehs:
            schedule = []
            if not veh.idle:
                for leg in veh.route:
                    if leg.pod == 1 or leg.pod == -1:
                        schedule.append((leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path))
            new_schedule, cost, feasible_schedules = compute_schedule(veh, tuple([req]), [], [schedule])
            if new_schedule and cost < min_cost:
                best_veh = veh
                best_schedule = new_schedule
                min_cost = cost
        if best_veh:
            best_veh.build_route(best_schedule, reqs, T)
            reqs_picking.add(req)
            return True
        else:
            return False



