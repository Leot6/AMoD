"""
greedy insertion: insert requests to vehicles in first-in-first-out manner
"""

import time
import numpy as np
from tqdm import tqdm
from lib.simulator.config import REBALANCER, IS_DEBUG
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
        if IS_DEBUG:
            print('        -assigning reqs to vehs through GI...')
            t = time.time()

        num_dispatched_req = 0
        vids_assigned = []
        l = len(self.queue)
        # for i in tqdm(range(l), desc=f'GI ({l} reqs)', leave=False):
        for i in range(l):
            req = self.queue[i]
            req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
            best_veh, best_sche = heuristic_insertion(self.vehs, req_params, T)
            if not best_veh and REBALANCER == 'NR':
                best_veh, best_sche = rebalancing_assign(self.vehs, req)
            if best_veh:
                best_veh.build_route(best_sche, self.reqs, T)
                self.reqs_picking.add(req)
                vids_assigned.append(best_veh.id)
                num_dispatched_req += 1
            else:
                self.rejs.add(req)
        self.queue.clear()

        if IS_DEBUG:
            print(f'            +assigned reqs: {num_dispatched_req} ({round((time.time() - t), 2)}s)')
        return vids_assigned

    def __str__(self):
        str = f'dispatcher: GI'
        return str


def heuristic_insertion(vehs, req_params, T):
    best_veh = None
    best_sche = None
    min_cost = np.inf
    [req_id, req_onid, req_dnid, req_Clp, req_Cld] = req_params

    # for veh in tqdm(vehs, desc=f'Candidates ({len(vehs)} vehs)', leave=False):
    for veh in vehs:
        if get_duration_from_origin_to_dest(veh.nid, req_onid) + veh.t_to_nid + T > req_Clp:
            continue
        sub_sche = veh.sche
        veh_params = [veh.nid, veh.t_to_nid, veh.n]
        new_sche, cost, feasible_sches, n_s_c = compute_schedule(veh_params, [sub_sche], req_params, T)
        if cost < min_cost:
            best_veh = veh
            best_sche = new_sche
            min_cost = cost
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
        # best_sche = [(req.id, 1, req.onid, req.Clp), (req.id, -1, req.dnid, req.Cld)]
        best_sche = [(-1, 0, req.onid, dt * 1.1)]
    return best_veh, best_sche
