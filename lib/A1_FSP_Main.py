"""
batch assignment: computing the feaible schedule pool and then assign them together
"""

import time
import copy

from lib.Configure import MODEE, IS_DEBUG
from lib.A1_VTtable import build_vt_table
from lib.A1_AssignPlanner import ILP_assign
from lib.A1_Rebalancer import find_unshared_trips


class FSP(object):
    """
    FSP is feasible schedule pool dispatch algorithm
    Attributes:
        rid_assigned_last: the list of id of requests assigned in last dispatching period
    Used Parameters:
        AMoD.vehs
        AMoD.reqs
        AMoD.queue
        AMoD.reqs_picking
        AMoD.reqs_unassigned
        AMoD.T
    """

    def __init__(self):
        self.rid_assigned_last = set()

    def dispatch(self, amod):
        vehs = amod.vehs
        reqs = amod.reqs
        queue = amod.queue
        reqs_picking = amod.reqs_picking
        reqs_unassigned = amod.reqs_unassigned
        T = amod.T

        reqs_new = queue
        if MODEE == 'VT':
            reqs_prev = []
        else:  # 'VT_replan'
            reqs_prev = sorted(reqs_picking.union(reqs_unassigned), key=lambda r: r.id)

        # build VT-table
        if IS_DEBUG:
            print('    -T = %d, building VT-table ...' % T)
        a1 = time.time()
        veh_trip_edges = build_vt_table(vehs, reqs_new, reqs_prev, T)
        if IS_DEBUG:
            print('        a1 running time:', round((time.time() - a1), 2))

        # ILP assign shared trips using VT-table
        if IS_DEBUG:
            print('    -T = %d, start ILP assign with %d edges...' % (T, len(veh_trip_edges)))
        a2 = time.time()
        R_assigned, V_assigned, S_assigned = ILP_assign(veh_trip_edges, reqs_prev + reqs_new, self.rid_assigned_last)
        if IS_DEBUG:
            print('        a2 running time:', round((time.time() - a2), 2))

        # print('share', [r.id for r in R_assigned], [v.id for v in V_assigned])

        # assign unshared trips
        if IS_DEBUG:
            print('    -T = %d, start assign unshared trips...' % T)
        a3 = time.time()
        reqs_unassigned_in_ridesharing = set(queue).union(reqs_unassigned) - set(R_assigned)
        vehs_unassigned = set(vehs) - set(V_assigned)
        R_unshared, V_unshared, S_unshared = find_unshared_trips(vehs_unassigned, reqs_unassigned_in_ridesharing)
        R_assigned.extend(R_unshared)
        V_assigned.extend(V_unshared)
        S_assigned.extend(S_unshared)
        if IS_DEBUG:
            print('        a3 running time:', round((time.time() - a3), 2))

        # print('unshare', [r.id for r in R_unshared], [v.id for v in V_unshared])

        # add changed schedule in VT-replan
        if MODEE == 'VT_replan':
            R_id_assigned = [req.id for req in R_assigned]
            assert len(R_id_assigned) == len(set(R_id_assigned))
            self.rid_assigned_last = set(R_id_assigned)
            vehs_unassigned = sorted(set(vehs) - set(V_assigned), key=lambda v: v.id)
            for veh in vehs_unassigned:
                schedule = []
                if not veh.idle and 1 in {leg.pod for leg in veh.route}:
                    for leg in veh.route:
                        if leg.rid in veh.onboard_rid:
                            schedule.append((leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path))
                    if schedule != [(leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path) for leg in veh.route]:
                        # vehicles with schedule changed
                        # rid_changed_assign = set([leg.rid for leg in veh.route]) - set([s[0] for s in schedule])
                        # assert rid_changed_assign.issubset(R_id_assigned)
                        V_assigned.append(veh)
                        S_assigned.append(copy.deepcopy(schedule))
        # debug
        assert len(R_assigned) == len(set(R_assigned))
        assert len(V_assigned) == len(set(V_assigned))
        assert len(V_assigned) == len(S_assigned)

        # execute the assignment and build (update) route for assigned vehicles
        for veh, schedule in zip(V_assigned, S_assigned):
            veh.build_route(schedule, reqs, T)

        # debug code (check each req is not assigned to multiple vehs)
        reqs_on_vehs = []
        for veh in amod.vehs:
            trip = {leg.rid for leg in veh.route}
            if -2 in trip:
                trip.remove(-2)
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))

        # update reqs clustering status
        reqs_pool = sorted(reqs_picking.union(reqs_unassigned), key=lambda r: r.id) + queue
        debug = len(reqs_pool)
        amod.queue.clear()
        assert debug == len(reqs_pool)
        amod.reqs_picking.update(set(R_assigned))
        assert debug == len(reqs_pool)
        amod.reqs_unassigned = set(reqs_pool) - reqs_picking
        assert debug == len(reqs_pool)

        return V_assigned
