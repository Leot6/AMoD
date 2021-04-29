"""
batch assignment: computing the optimal schedule pool and then assign them together
"""

import time
import copy

from lib.simulator.config import IS_DEBUG, T_WARM_UP, T_STUDY
from lib.dispatcher.osp.osp_pool import build_vt_table, get_prev_assigned_edges, CUTOFF_VT, FAST_COMPUTE
from lib.dispatcher.osp.osp_assign import ILP_assign, greedy_assign
from lib.analysis.dispatcher_analysis import DispatcherAnalysis
from lib.analysis.objective_analysis import ObjectiveAnalysis

# Ensure_Picking = True if not FAST_COMPUTE else False
Ensure_Picking = True
# Ensure_Picking = False

# Reject_Unassigned = True
Reject_Unassigned = False


class OSP(object):
    """
    OSP is optimal schedule pool dispatch algorithm
    """

    def __init__(self, amod):
        self.vehs = amod.vehs
        self.reqs = amod.reqs
        self.queue = amod.queue
        self.reqs_picking = amod.reqs_picking
        self.reqs_unassigned = amod.reqs_unassigned
        # self.analysis = DispatcherAnalysis()
        self.analysis = ObjectiveAnalysis()

    def dispatch(self, T):
        t = time.time()

        reqs_new = self.queue
        if Reject_Unassigned:
            reqs_prev = sorted(self.reqs_picking, key=lambda r: r.id)
        else:
            reqs_prev = sorted(self.reqs_picking.union(self.reqs_unassigned), key=lambda r: r.id)

        if IS_DEBUG:
            print(f'        -assigning {len(reqs_prev) + len(reqs_new)} reqs to vehs through OSP...')

        # compute the ride-sharing assignment
        prev_assigned_edges = get_prev_assigned_edges(self.vehs, self.reqs)

        rids_assigned, vids_assigned, sches_assigned, num_edges = \
            ridesharing_match_osp(self.vehs, self.reqs, reqs_new, reqs_prev, self.reqs_picking, prev_assigned_edges, T)

        # if IS_DEBUG and T_WARM_UP < T <= T_WARM_UP + T_STUDY:
        #     self.analysis.run_comparison_analysis(self.vehs, self.reqs, self.queue, self.reqs_picking,
        #                                           self.reqs_unassigned, prev_assigned_edges, T, rids_assigned,
        #                                           num_edges, osp_run_time)

        if T_WARM_UP <= T <= T_WARM_UP + T_STUDY:
            self.analysis.append_anime_data(self.vehs, self.reqs, self.queue)

        # execute the assignment and build (update) route for assigned vehicles
        for vid, sche in zip(vids_assigned, sches_assigned):
            self.vehs[vid].build_route(sche, self.reqs, T)

        # add changed sche in VT-replan
        vids_remove_r, sches_remove_r = find_changed_trips(self.vehs, vids_assigned, T)
        # execute the assignment and build (update) route for assigned vehicles
        for vid, sche in zip(vids_remove_r, sches_remove_r):
            self.vehs[vid].build_route(sche, self.reqs, T)

        if IS_DEBUG:
            print(f'            +assigned reqs: {len(rids_assigned)}  ({round((time.time() - t), 2)}s)')

        return vids_assigned + vids_remove_r

    def __str__(self):
        RU_or_CU = 'RU' if Reject_Unassigned else 'CU'
        str = f'dispatcher: OSP ({RU_or_CU}), timeout: {CUTOFF_VT} s, fast: {FAST_COMPUTE}'
        return str


def ridesharing_match_osp(vehs, reqs_all, reqs_new, reqs_prev, reqs_picking, prev_assigned_edges, T):
    # build VT-table
    veh_trip_edges = build_vt_table(vehs, reqs_new, reqs_prev, T)
    veh_trip_edges = sorted(veh_trip_edges, key=lambda e: (e[0].id, -len(e[1]), e[3]))
    num_edges = len(veh_trip_edges)

    vid_Tid_edges = [(veh.id, [r.id for r in trip]) for (veh, trip, sche, cost) in veh_trip_edges]
    missed_prev_assigned_edges = []
    for (veh, trip, sche, cost) in prev_assigned_edges:
        if (veh.id, [r.id for r in trip]) not in vid_Tid_edges:
            missed_prev_assigned_edges.append((veh, trip, sche, cost))
    veh_trip_edges.extend(missed_prev_assigned_edges)

    # ILP assign shared trips using VT-table
    reqs_pool = reqs_prev + reqs_new
    ensure_picking_list = reqs_picking if Ensure_Picking else []
    rids_assigned, vids_assigned, sches_assigned = \
        ILP_assign(veh_trip_edges, reqs_pool, reqs_all, ensure_picking_list, prev_assigned_edges)

    return rids_assigned, vids_assigned, sches_assigned, num_edges


# find vehicles with schedule changed
def find_changed_trips(vehs, vids_assigned_in_ILP, T):
    vids_remove_r = []
    sches_remove_r = []
    for veh in vehs:
        if veh.id not in vids_assigned_in_ILP and not veh.picking_rids == []:
            new_sche = []
            for (rid, pod, tnid, ddl) in veh.sche:
                if rid in veh.onboard_rids:
                    new_sche.append((rid, pod, tnid, ddl))
            vids_remove_r.append(veh.id)
            sches_remove_r.append(copy.deepcopy(new_sche))
    return vids_remove_r, sches_remove_r


