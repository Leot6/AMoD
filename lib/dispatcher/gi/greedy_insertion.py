"""
greedy insertion: insert requests to vehicles in first-in-first-out manner
"""

import numpy as np
from tqdm import tqdm
from lib.routing.routing_server import get_duration_from_origin_to_dest
from lib.dispatcher.osp.schedule_finder import compute_schedule


class GI(object):
    """
    GI is greedy insertion dispatch algorithm
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
        for i in range(l):  # tqdm(range(l), desc='GI'):
            req = amod.queue.pop()
            req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
            best_veh, best_sche = self.heuristic_insertion(amod.vehs, req_params, amod.T, amod.K)
            if not best_veh and amod.rebl == 'naive':
                best_veh, best_sche = self.non_share_assign(amod.vehs, req)
            if best_veh:
                best_veh.build_route(best_sche, amod.reqs, amod.T)
                amod.reqs_picking.add(req)
                V_id_assigned.append(best_veh.id)
            else:
                amod.rejs.add(req)
        return V_id_assigned

    @staticmethod
    # @jit
    def heuristic_insertion(vehs, req_params, T, K):
        best_veh = None
        best_sche = None
        min_cost = np.inf

        for veh in vehs:  # tqdm(vehs, desc='Candidates_RideSharing'):
            sub_sche = []
            if not veh.idle:
                for leg in veh.route:
                    if leg.pod == 1 or leg.pod == -1:
                        sub_sche.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
            veh_params = [veh.nid, veh.t_to_nid, veh.n]
            new_sche, cost, feasible_sches, n_s_c = compute_schedule(veh_params, [sub_sche], req_params, T, K)
            if cost < min_cost:
                best_veh = veh
                best_sche = new_sche
                min_cost = cost
        return best_veh, best_sche

    @staticmethod
    def non_share_assign(vehs, req):
        best_veh = None
        best_sche = None
        min_cost = np.inf
        for veh in vehs:  # tqdm(vehs, desc='Candidates_NonSharing'):
            if veh.idle:
                dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
                if dt < min_cost:
                    best_veh = veh
                    min_cost = dt
        if best_veh:
            best_sche = [(req.id, 1, req.onid, req.Tr, req.Clp), (req.id, -1, req.dnid, req.Tr + req.Ts, req.Cld)]
        return best_veh, best_sche
