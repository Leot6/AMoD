"""
batch assignment: computing the feaible schedule pool and then assign them together
"""

import time
import numpy as np
from lib.S_Configure import MODEE, IS_DEBUG
from lib.A1_VTtable import build_vt_table
from lib.A1_AssignPlanner import ILP_assign
from lib.A1_Rebalancer import find_non_shared_trips, naive_rebalancing


class FSP(object):
    """
        FSP is feasible schedule pool dispatch algorithm
        Attributes:
            rid_assigned_last: the list of id of requests assigned in last dispatching period
        """

    def __init__(self):
        self.rid_assigned_last = set()

    def dispatch(self, vehs, queue, reqs_picking, reqs_unassigned):
        reqs_new = queue
        if MODEE == 'VT':
            reqs_old = []
        else:  # 'VT_replan'
            reqs_old = sorted(reqs_picking.union(reqs_unassigned), key=lambda r: r.id)

        if IS_DEBUG:
            print('    -T = %d, building VT-table ...' % self.T)
        a3 = time.time()
        veh_trip_edges = build_vt_table(self.vehs, reqs_new, reqs_old, T)
        if IS_DEBUG:
            print('        a3 running time:', round((time.time() - a3), 2))


