"""
batch assignment: computing the optimal schedule pool and then assign them together
"""

import time
import copy

from lib.simulator.config import DISPATCHER, IS_DEBUG
from lib.dispatcher.osp.schedule_pool import build_vt_table
from lib.dispatcher.osp.linear_assignment import ILP_assign, greedy_assign
from lib.routing.routing_server import get_duration_from_origin_to_dest


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
        K = amod.K

        reqs_new = queue
        if DISPATCHER == 'OSP-RO':
            reqs_prev = sorted(reqs_picking.union(reqs_unassigned), key=lambda r: r.id)
        else:
            reqs_prev = []

        # find the shared assignment
        R_id_shared, V_id_shared, S_shared = self.find_shared_trips(vehs, reqs_new, reqs_prev, reqs_picking, T, K)
        # execute the assignment and build (update) route for assigned vehicles
        for vid, sche in zip(V_id_shared, S_shared):
            vehs[vid].build_route(sche, reqs, T)

        # print('share', R_id_shared, V_id_shared)

        # add changed sche in VT-replan
        vehs_unassigned = sorted(set(vehs) - set([vehs[vid] for vid in V_id_shared]), key=lambda v: v.id)
        V_id_remove_r, S_remove_r = self.find_changed_trips(vehs_unassigned, V_id_shared, R_id_shared, T)
        # execute the assignment and build (update) route for assigned vehicles
        for vid, sche in zip(V_id_remove_r, S_remove_r):
            vehs[vid].build_route(sche, reqs, T)

        # assign unshared trips
        if amod.rebl == 'naive':
            reqs_unassigned_in_rs = set(queue).union(reqs_unassigned) - {reqs[rid] for rid in R_id_shared}
            R_id_unshared, V_id_unshared, S_unshared = self.find_unshared_trips(vehs, reqs_unassigned_in_rs, T)
            # execute the assignment and build (update) route for assigned vehicles
            for rid, vid, sche in zip(R_id_unshared, V_id_unshared, S_unshared):
                vehs[vid].build_route(sche, reqs, T)
                vehs[vid].VTtable[0].append((tuple([reqs[rid]]), sche, 0, [sche]))
        else:
            R_id_unshared = []
            V_id_unshared = []

        # print('unshare', R_id_unshared, V_id_unshared)

        # veh_sample = amod.vehs[42]
        # print('veh_sample', veh_sample.nid, [veh_sample.lng, veh_sample.lat])
        # print('veh_sample', veh_sample.VTtable[0])
        # print('veh_sample', veh_sample.VTtable[1])

        # update reqs clustering status
        R_assigned = {reqs[rid] for rid in (R_id_shared + R_id_unshared)}
        amod.reqs_picking.update(R_assigned)
        amod.reqs_unassigned = set(queue).union(reqs_unassigned) - R_assigned
        amod.queue.clear()

        assert set(list(amod.reqs_picking) + list(amod.reqs_serving) + list(amod.reqs_served) +
                   list(amod.reqs_unassigned) + list(amod.rejs)) == set(amod.reqs)
        assert len(R_assigned) == len(set(R_assigned))

        # debug code (check each req is not assigned to multiple vehs)
        R_id_enroute = []
        for veh in vehs:
            T_id = {leg.rid for leg in veh.route} - {-2}
            R_id_enroute.extend(list(T_id))
        assert len(R_id_enroute) == len(set(R_id_enroute))

        return V_id_shared + V_id_remove_r + V_id_unshared

    @staticmethod
    def find_shared_trips(vehs, reqs_new, reqs_prev, reqs_picking, T, K):
        # build VT-table
        if IS_DEBUG:
            print('    -T = %d, building VT-table ...' % T)
            a1 = time.time()
        veh_trip_edges = build_vt_table(vehs, reqs_new, reqs_prev, T, K)
        if IS_DEBUG:
            print('        a1 running time:', round((time.time() - a1), 2))

        # ILP assign shared trips using VT-table
        if IS_DEBUG:
            print('    -T = %d, start ILP assign with %d edges...' % (T, len(veh_trip_edges)))
            a2 = time.time()
        R_id_assigned, V_id_assigned, S_assigned = ILP_assign(veh_trip_edges, reqs_prev + reqs_new, reqs_picking)
        if IS_DEBUG:
            print('        a2 running time:', round((time.time() - a2), 2))

        # R_id_in_sche = set()
        # for sche in S_assigned:
        #     for (rid, pod, tnid, ept, ddl) in sche:
        #         if pod == 1:
        #             R_id_in_sche.add(rid)
        # print('R_id_assigned', sorted(R_id_assigned))
        # print('R_id_in_sche', R_id_in_sche)
        # assert set(R_id_assigned) == R_id_in_sche
        # print('R_id_assigned', sorted(R_id_assigned))
        # print('R_id_in_sche', R_id_in_sche)

        return R_id_assigned, V_id_assigned, S_assigned

    @staticmethod
    # find vehicles with schedule changed
    def find_changed_trips(vehs, V_id_shared, R_id_shared, T):
        if IS_DEBUG:
            print('    -T = %d, find vehicles with removed requests ...' % T)
            a3 = time.time()
        V_id_remove_r = []
        S_remove_r = []
        if DISPATCHER == 'OSP-RO':
            for veh in vehs:
                if not veh.idle and veh.id not in V_id_shared and 1 in {leg.pod for leg in veh.route}:
                    sche = []
                    for leg in veh.route:
                        if leg.rid in veh.onboard_rid:
                            sche.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
                    veh_route = [(leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl) for leg in veh.route]
                    if len(veh_route) > 0 and veh_route[0] == (-2, 0):
                        veh_route.remove(veh_route[0])
                    if sche != veh_route:
                        rid_changed_assign = {leg.rid for leg in veh.route} - {s[0] for s in sche} - {-2}
                        # print('R_id_shared', R_id_shared)
                        # assert rid_changed_assign <= set(R_id_shared)
                        V_id_remove_r.append(veh.id)
                        S_remove_r.append(copy.deepcopy(sche))
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
                    sche = [(req.id, 1, req.onid, req.Tr, req.Clp), (req.id, -1, req.dnid, req.Tr + req.Ts, req.Cld)]
                    dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
                    idle_veh_req.append((veh, tuple([req]), copy.deepcopy(sche), dt))

        R_id_assigned, V_id_assigned, S_assigned = greedy_assign(idle_veh_req)
        # R_id_assigned, V_id_assigned, S_assigned = ILP_assign(idle_veh_req, reqs_unassigned, set())

        assert len(R_id_assigned) == len(V_id_assigned)
        for rid, sche in zip(R_id_assigned, S_assigned):
            assert rid == sche[0][0]

        if IS_DEBUG:
            print('        a4 running time:', round((time.time() - a4), 2))

        return R_id_assigned, V_id_assigned, S_assigned
