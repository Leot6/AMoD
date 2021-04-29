"""
single request batch assignment, where requests cannot be combined in the same interval
"""

import time
from tqdm import tqdm
from lib.simulator.config import IS_DEBUG
from lib.routing.routing_server import get_duration_from_origin_to_dest
from lib.dispatcher.osp.osp_pool import build_vt_table
from lib.dispatcher.osp.osp_assign import ILP_assign, greedy_assign
from lib.dispatcher.osp.osp_schedule import compute_schedule

# MULTI_ASSIGN = True
MULTI_ASSIGN = False


class SBA(object):
    """
    SBA is a single request batch assignment algorithm
    """

    def __init__(self, amod):
        self.vehs = amod.vehs
        self.reqs = amod.reqs
        self.queue = amod.queue

    def dispatch(self, T):
        # compute the single request batch assignment
        rids_assigned, vids_assigned, sches_assigned, num_edges = \
            ridesharing_match_sba(self.vehs, self.reqs, self.queue, T)
        # execute the assignment and update routes for assigned vehicles
        for vid, sche in zip(vids_assigned, sches_assigned):
            self.vehs[vid].build_route(sche, self.reqs, T)

        return vids_assigned

    def __str__(self):
        single_or_multi = 'multi' if MULTI_ASSIGN else 'single'
        str = f'dispatcher: SBA ({single_or_multi})'
        return str


def ridesharing_match_sba(vehs, reqs_all, reqs_pool, T):
    if IS_DEBUG:
        t = time.time()
        print(f'        -assigning {len(reqs_pool)} reqs to vehs through SBA...')

    if MULTI_ASSIGN:
        reqs_prev = []
        veh_req_edges = build_vt_table(vehs, reqs_pool, reqs_prev, T, Re_Optimization=False)
    else:
        veh_req_edges = build_rv_graph(vehs, reqs_pool, T)
        # veh_req_edges = search_feasible_veh_req_edges(vehs, reqs_pool, T)
    num_edges = len(veh_req_edges)

    # ILP assign
    rids_assigned, vids_assigned, sches_assigned = ILP_assign(veh_req_edges, reqs_pool, reqs_all)
    # rids_assigned, vids_assigned, sches_assigned = greedy_assign(veh_req_edges)

    if IS_DEBUG:
        print(f'            +assigned reqs: {len(rids_assigned)}  ({round((time.time() - t), 2)}s)')

    return rids_assigned, vids_assigned, sches_assigned, num_edges


# when numreqs << numvehs, this one runs faster than the following one
def build_rv_graph(vehs, reqs_pool, T):
    t = time.time()
    veh_req_edges = []
    for req in tqdm(reqs_pool, desc=f'req search ({len(reqs_pool)} reqs)', leave=False):
        req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
        trip = tuple([req])
        for veh in tqdm(vehs, desc=f'candidate veh ({len(vehs)} vehs)', leave=False):
            if get_duration_from_origin_to_dest(veh.nid, req.onid) + veh.t_to_nid + T > req.Clp:
                continue
            veh_params = [veh.nid, veh.t_to_nid, veh.n]
            sub_sche = veh.sche
            best_sche, cost, feasible_sches, n_s_c = compute_schedule(veh_params, [sub_sche], req_params, T)
            if best_sche:
                veh_req_edges.append((veh, trip, best_sche, cost))
    if IS_DEBUG:
        print(f'                +computing feasible veh req pairs...  ({round((time.time() - t), 2)}s)')
    return veh_req_edges

# def search_feasible_veh_req_edges(vehs, reqs_pool, T):
#     veh_req_edges = []
#     for veh in tqdm(vehs, desc=f'veh search ({len(vehs)} vehs)', leave=False):
#         veh_params = [veh.nid, veh.t_to_nid, veh.n]
#         sub_sche = veh.sche
#         for req in tqdm(reqs_pool, desc=f'candidate req ({len(reqs_pool)} reqs)', leave=False):
#             # filter out the req which can not be served even when the veh is idle
#             if get_duration_from_origin_to_dest(veh.nid, req.onid) + veh.t_to_nid + T > req.Clp:
#                 continue
#             trip = tuple([req])
#             req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
#             best_sche, min_cost, feasible_sches, num_of_sche_searched \
#                 = compute_schedule(veh_params, [sub_sche], req_params, T)
#             if best_sche:
#                 veh_req_edges.append((veh, trip, best_sche, min_cost))
#     return veh_req_edges