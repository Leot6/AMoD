"""
heuristic insertion: insert requests to vehicles in first-in-first-out manner
"""

import numpy as np
from tqdm import tqdm

from lib.A1_ScheduleFinder import compute_schedule
from lib.S_Route import get_duration


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

    def dispatch(self, amod):
        V_id_assigned = []
        l = len(amod.queue)
        for i in tqdm(range(l), desc='HI'):
            req = amod.queue.pop()
            best_veh, best_schedule = self.insert_heuristic(amod.vehs, req)
            if best_veh:
                best_veh.build_route(best_schedule, amod.reqs, amod.T)
                amod.reqs_picking.add(req)
                V_id_assigned.append(best_veh.id)
            else:
                amod.rejs.add(req)
        return V_id_assigned

    @staticmethod
    def insert_heuristic(vehs, req):
        best_veh = None
        best_schedule = None
        min_cost = np.inf
        for veh in tqdm(vehs, desc='Candidates_RideSharing'):
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

        if not best_veh:
            for veh in tqdm(vehs, desc='Candidates_NonSharing'):
                if veh.idle:
                    dt = get_duration(veh.nid, req.onid)
                    if dt < min_cost:
                        best_veh = veh
                        min_cost = dt
            if best_veh:
                best_schedule = [(req.id, 1, req.onid, req.Clp, None), (req.id, -1, req.dnid, req.Cld, None)]

        return best_veh, best_schedule
