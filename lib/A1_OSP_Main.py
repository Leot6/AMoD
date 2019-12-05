"""
batch assignment: computing the optimal schedule pool and then assign them together
"""

import time
import copy

from lib.Configure import MODEE, IS_DEBUG
from lib.A1_VTtable import build_vt_table
from lib.A1_AssignPlanner import ILP_assign, greedy_assign
from lib.S_Route import get_duration


class OSP(object):
    """
    OSP is optimal schedule pool dispatch algorithm
    Used Parameters:
        AMoD.vehs
        AMoD.reqs
        AMoD.queue
        AMoD.reqs_picking
        AMoD.reqs_unassigned
        AMoD.T
    """

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

        # find the shared assignment
        R_id_shared, V_id_shared, S_shared = self.find_shared_trips(vehs, reqs_new, reqs_prev, reqs_picking, T)
        # execute the assignment and build (update) route for assigned vehicles
        for vid, schedule in zip(V_id_shared, S_shared):
            vehs[vid].build_route(schedule, reqs, T)

        # print('share', R_id_shared, V_id_shared)

        # add changed schedule in VT-replan
        vehs_unassigned = sorted(set(vehs) - set([vehs[vid] for vid in V_id_shared]), key=lambda v: v.id)
        V_id_remove_r, S_remove_r = self.find_chenged_trips(vehs_unassigned, V_id_shared, R_id_shared, T)
        # execute the assignment and build (update) route for assigned vehicles
        for vid, schedule in zip(V_id_remove_r, S_remove_r):
            vehs[vid].build_route(schedule, reqs, T)

        # assign unshared trips
        reqs_unassigned_in_rs = set(queue).union(reqs_unassigned) - {reqs[rid] for rid in R_id_shared}
        R_id_unshared, V_id_unshared, S_unshared = self.find_unshared_trips(vehs, reqs_unassigned_in_rs, T)
        # execute the assignment and build (update) route for assigned vehicles
        for rid, vid, schedule in zip(R_id_unshared, V_id_unshared, S_unshared):
            vehs[vid].build_route(schedule, reqs, T)
            vehs[vid].VTtable[0] = [(tuple([reqs[rid]]), schedule, 0, [schedule])]

        # print('unshare', R_id_unshared, V_id_unshared)

        # update reqs clustering status
        R_assigned = {reqs[rid] for rid in (R_id_shared + R_id_unshared)}
        amod.reqs_picking.update(R_assigned)
        amod.reqs_unassigned = set(queue).union(reqs_unassigned) - R_assigned
        amod.queue.clear()

        assert set(list(amod.reqs_picking) + list(amod.reqs_serving) + list(amod.reqs_served) +
                   list(amod.reqs_unassigned) + list(amod.rejs)) == set(amod.reqs)
        assert len(R_assigned) == len(set(R_assigned))

        # debug code (check each req is not assigned to multiple vehs)
        reqs_on_vehs = []
        for veh in vehs:
            trip = {leg.rid for leg in veh.route} - {-2}
            # if -2 in trip:
            #     trip.remove(-2)
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))

        return V_id_shared + V_id_remove_r + V_id_unshared

    @staticmethod
    def find_shared_trips(vehs, reqs_new, reqs_prev, reqs_picking, T):
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
        R_id_assigned, V_id_assigned, S_assigned = ILP_assign(veh_trip_edges, reqs_prev + reqs_new, reqs_picking)
        if IS_DEBUG:
            print('        a2 running time:', round((time.time() - a2), 2))
        return R_id_assigned, V_id_assigned, S_assigned

    @staticmethod
    # find vehicles with schedule changed
    def find_chenged_trips(vehs, V_id_shared, R_id_shared, T):
        if IS_DEBUG:
            print('    -T = %d, find vehicles with removed requests ...' % T)
            a3 = time.time()
        V_id_remove_r = []
        S_remove_r = []
        if MODEE == 'VT_replan':
            for veh in vehs:
                if not veh.idle and veh.id not in V_id_shared and 1 in {leg.pod for leg in veh.route}:
                    schedule = []
                    for leg in veh.route:
                        if leg.rid in veh.onboard_rid:
                            schedule.append((leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path))
                    if schedule != [(leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path) for leg in veh.route]:
                        rid_changed_assign = set([leg.rid for leg in veh.route]) - set([s[0] for s in schedule]) - {-2}
                        # print('R_id_shared', R_id_shared)
                        assert rid_changed_assign <= set(R_id_shared)
                        V_id_remove_r.append(veh.id)
                        S_remove_r.append(copy.deepcopy(schedule))
        if IS_DEBUG:
            print('        a3 running time:', round((time.time() - a3), 2))
        return V_id_remove_r, S_remove_r

    @staticmethod
    def find_unshared_trips(vehs, reqs_unassigned, T):
        if IS_DEBUG:
            print('    -T = %d, start assign unshared trips...' % T)
            a4 = time.time()
        reqs_unassigned = sorted(reqs_unassigned, key=lambda r: r.id)
        idle_veh_req = []
        for veh in vehs:
            if veh.idle:
                for req in reqs_unassigned:
                    schedule = [(req.id, 1, req.onid, req.Clp, None), (req.id, -1, req.dnid, req.Cld, None)]
                    dt = get_duration(veh.nid, req.onid)
                    idle_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))

        R_id_assigned, V_id_assigned, S_assigned = greedy_assign(idle_veh_req)
        # R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(idle_veh_req, reqs_unassigned, set())

        assert len(R_id_assigned) == len(V_id_assigned)
        for rid, schedule in zip(R_id_assigned, S_assigned):
            assert rid == schedule[0][0]

        if IS_DEBUG:
            print('        a4 running time:', round((time.time() - a4), 2))

        return R_id_assigned, V_id_assigned, S_assigned
