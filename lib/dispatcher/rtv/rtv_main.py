"""
rtv assignment: implementation of Alonso-Mora et al. 2017 
(On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment)
"""

import time

from lib.simulator.config import IS_DEBUG
from lib.dispatcher.rtv.rtv_graph import search_feasible_trips, CUTOFF_RTV, RTV_SIZE
from lib.dispatcher.osp.osp_main import find_changed_trips
from lib.dispatcher.osp.osp_pool import get_prev_assigned_edges
from lib.dispatcher.osp.osp_assign import ILP_assign


class RTV(object):
    """
    RTV is a batch assignment algorithm
    """

    def __init__(self, amod):
        self.vehs = amod.vehs
        self.reqs = amod.reqs
        self.queue = amod.queue
        self.reqs_picking = amod.reqs_picking
        self.reqs_unassigned = amod.reqs_unassigned

    def dispatch(self, T):
        """
        :param T:
        :return:
        """
        reqs_pool = sorted(self.reqs_picking.union(self.reqs_unassigned), key=lambda r: r.id) + self.queue

        # compute the ride-sharing assignment
        prev_assigned_edges = get_prev_assigned_edges(self.vehs, self.reqs)
        rids_assigned, vids_assigned, sches_assigned, num_edges = \
            ridesharing_match_rtv(self.vehs, reqs_pool, self.reqs_picking, prev_assigned_edges, T)

        # execute the assignment and update routes for assigned vehicles
        for vid, sche in zip(vids_assigned, sches_assigned):
            self.vehs[vid].build_route(sche, self.reqs, T)

        # find out vehs with reqs that are reassigned to other vehs
        vids_remove_r, sches_remove_r = find_changed_trips(self.vehs, vids_assigned, T)
        # execute the assignment and build (update) route for assigned vehicles
        for vid, sche in zip(vids_remove_r, sches_remove_r):
            self.vehs[vid].build_route(sche, self.reqs, T)

        return vids_assigned + vids_remove_r

    def __str__(self):
        str = f'dispatcher: RTV, timeout: {CUTOFF_RTV} s, size: {RTV_SIZE}'
        return str


def ridesharing_match_rtv(vehs, reqs_pool, reqs_picking, prev_assigned_edges, T):
    if IS_DEBUG:
        print('    -T = %d, building RTV graph ...' % T)
        a1 = time.time()
    veh_trip_edges = search_feasible_trips(vehs, reqs_pool, T)
    num_edges = len(veh_trip_edges)
    veh_trip_edges.extend(prev_assigned_edges)
    if IS_DEBUG:
        print('        a1 running time:', round((time.time() - a1), 2))
    if IS_DEBUG:
        print('    -T = %d, start ILP assign with %d edges...' % (T, len(veh_trip_edges)))
        a2 = time.time()
    rids_assigned, vids_assigned, sches_assigned = ILP_assign(veh_trip_edges, reqs_pool, reqs_picking)
    if IS_DEBUG:
        print('        a2 running time:', round((time.time() - a2), 2))
    return rids_assigned, vids_assigned, sches_assigned, num_edges
