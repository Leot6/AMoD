"""
heuristic insertion: insert requests to vehicles in first-in-first-out manner
"""

import numpy as np

from lib.A1_ScheduleFinder import compute_schedule


class HI(object):
    """
    HI is heuristic insertion dispatch algorithm
    Used Parameters:
        AMoD.vehs
        AMoD.reqs
        AMoD.queue
        AMoD.reqs_picking
        AMoD.rejs
        AMoD.T
    """

    def __init__(self):
        self.rid_assigned_last = set()

    def dispatch(self, amod):
        V_assigned = []
        l = len(amod.queue)
        for i in range(l):
            req = amod.queue.pop()
            best_veh, best_schedule = self.insert_heuristic(amod.vehs, req)
            if best_veh:
                best_veh.build_route(best_schedule, amod.reqs, amod.T)
                V_assigned.append(best_veh)
                amod.reqs_picking.add(req)
            else:
                amod.rejs.add(req)
        return V_assigned

    def insert_heuristic(self, vehs, req):
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

        return best_veh, best_schedule
