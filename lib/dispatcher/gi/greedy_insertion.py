"""
greedy insertion: insert requests to vehicles in first-in-first-out manner
"""

import numpy as np
from tqdm import tqdm
from lib.simulator.config import REBALANCER
from lib.routing.routing_server import get_duration_from_origin_to_dest
from lib.dispatcher.osp.osp_schedule import compute_schedule


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

    def __init__(self, amod):
        self.vehs = amod.vehs
        self.reqs = amod.reqs
        self.queue = amod.queue
        self.reqs_picking = amod.reqs_picking
        self.rejs = amod.rejs

    def dispatch(self, T):
        clear_veh_candidate_sches(self.vehs)
        vids_assigned = []
        l= len(self.queue)
        for i in tqdm(range(l), desc=f'GI ({l} reqs)', leave=False):
            req = self.queue.pop()
            req_params = [req.id, req.onid, req.dnid, req.Tr, req.Ts, req.Clp, req.Cld]
            best_veh, best_sche = heuristic_insertion(self.vehs, req_params, T)
            if not best_veh and REBALANCER == 'NR':
                best_veh, best_sche = rebalancing_assign(self.vehs, req)
            if best_veh:
                best_veh.build_route(best_sche, self.reqs, T)
                self.reqs_picking.add(req)
                vids_assigned.append(best_veh.id)
            else:
                self.rejs.add(req)
        return vids_assigned

    def __str__(self):
        str = f'dispatcher: GI'
        return str


def heuristic_insertion(vehs, req_params, T):
    best_veh = None
    best_sche = None
    min_cost = np.inf

    for veh in tqdm(vehs, desc=f'Candidates ({len(vehs)} vehs)', leave=False):
        sub_sche = veh.sche
        veh_params = [veh.nid, veh.t_to_nid, veh.n]
        new_sche, cost, feasible_sches, n_s_c = compute_schedule(veh_params, [sub_sche], req_params, T)
        if cost < min_cost:
            best_veh = veh
            best_sche = new_sche
            min_cost = cost
        if new_sche:
            # veh.candidate_sches.append(new_sche)
            veh.candidate_sches_gi.append(new_sche)
    return best_veh, best_sche


def rebalancing_assign(vehs, req):
    best_veh = None
    best_sche = None
    min_cost = np.inf
    for veh in tqdm(vehs, desc=f'Candidates_Rebalancing ({len(vehs)} vehs)', leave=False):
        if veh.idle:
            dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
            if dt < min_cost:
                best_veh = veh
                min_cost = dt
    if best_veh:
        best_sche = [(req.id, 1, req.onid, req.Tr, req.Clp), (req.id, -1, req.dnid, req.Tr + req.Ts, req.Cld)]
    return best_veh, best_sche


def clear_veh_candidate_sches(vehs):
    for veh in vehs:
        # veh.candidate_sches.clear()
        veh.candidate_sches_gi.clear()
