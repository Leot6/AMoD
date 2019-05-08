"""
main structure for the AMoD simulator
"""

import time
import copy
import numpy as np
import matplotlib.pyplot as plt
from dateutil.parser import parse

from lib.Configure import DMD_VOL, FLEET_SIZE, VEH_CAPACITY, MET_ASSIGN, MET_REBL, STN_LOC, REQ_DATA, DMD_SST, \
    INT_ASSIGN, INT_REBL, MODEE, IS_DEBUG
from lib.Vehicle import Veh
from lib.Request import Req
from lib.VTtable import build_vt_table
from lib.VTtableReplan import build_vt_table_replan
from lib.AssignPlanner import ILP_assign
from lib.Rebalancer import naive_rebalance
from lib.ScheduleFinder import compute_schedule_cost
from lib.Route import get_duration_from_table, get_routing_from_networkx


class Model(object):
    """
    Model is the initial class for the AMoD system
    Attributes:
        T: system time at current state
        D: demand volume (percentage of total)
        V: number of vehicles
        K: capacity of vehicles
        N: number of requests received
        assign: assignment method
        rebl: rebalancing method
        vehs: the list of vehicles
        reqs_data: the list of collected real taxi requests data
        req_init_idx: init index to read reqs_data
        queue: requests in the queue
        reqs: the list of all received requests
        reqs_served: the list of completed requests
        reqs_serving: the list of requests on board
        reqs_picking: the list of requests being picked up
        reqs_unassigned: the list of requests unassigned in the planning pool
        rejs: the list of rejected requests

    """

    def __init__(self):
        self.T = 0.0
        self.D = DMD_VOL
        self.V = FLEET_SIZE
        self.K = VEH_CAPACITY
        self.N = 0
        self.assign = MET_ASSIGN
        self.rebl = MET_REBL
        self.vehs = []
        for i in range(self.V):
            idx = int(i * len(STN_LOC) / self.V)
            self.vehs.append(Veh(i, STN_LOC.iloc[idx]['lng'], STN_LOC.iloc[idx]['lat'], K=self.K))
        self.reqs_data = REQ_DATA
        self.req_init_idx = 0
        while parse(self.reqs_data.iloc[self.req_init_idx]['ptime']) < DMD_SST:
            self.req_init_idx += 1
        self.queue = []
        self.reqs = []
        self.reqs_served = set()
        self.reqs_serving = set()
        self.reqs_picking = set()
        self.reqs_unassigned = set()
        self.rejs = []
        self.rid_assigned_last = set()

        # debug
        self.rid_assigned = set()
        self.rid_unassigned = set()

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        self.T = T
        if IS_DEBUG:
            print('    -updating status of vehicles and requests...')
        self.upd_vehs_and_reqs_stat_to_time()

        # debug code starts
        print('   Veh route after move:')
        for veh in self.vehs:
            d_to_nid = 0
            if veh.step_to_nid:
                d_to_nid = veh.step_to_nid.d
            # print('          veh:', veh.id, (veh.nid, round(veh.lng, 4), round(veh.lat, 4)),
            #       ', onboard:', veh.onboard_rid, ', Ts:', round(veh.Ts, 2), ', Ts+V.t:', round(veh.Ts + veh.t, 2),
            #       ', Ds+V.d', round(veh.Ds + veh.d, 2), ', t2nid', round(veh.t_to_nid, 2), ', d2nid', round(d_to_nid, 2))
            sche = [(leg.rid, leg.pod, leg.tlng, leg.tlat, leg.tnid, leg.ddl) for leg in veh.route]
            trip = tuple({self.reqs[leg.rid] for leg in veh.route})
            c = compute_schedule_cost(veh, trip, sche)
            # print('              *route:', [(leg.rid, leg.pod) for leg in veh.route],
            #       't:', round(veh.t, 2), 'd:', round(veh.d, 2), ', c:', c)
            nids = [veh.nid] + [leg.tnid for leg in veh.route]
            t = 0
            d = 0
            for i in range(len(nids) - 1):
                duration1 = get_duration_from_table(nids[i], nids[i + 1])
                duration, distance, steps = get_routing_from_networkx(nids[i], nids[i + 1])
                assert np.isclose(duration1, duration)
                t += duration
                d += distance
            # print('               travel time total', round(t, 2), round(t + veh.t_to_nid, 2))
            # print('               travel dist total', round(d, 2), round(d + d_to_nid, 2))
            assert np.isclose(t + veh.t_to_nid, veh.t)
            assert np.isclose(d + d_to_nid, veh.d)
        # debug code ends

        if IS_DEBUG:
            print('    -loading new reqs ...')
        self.gen_reqs_to_time()

        # debug code starts
        if IS_DEBUG:
            noi = 0  # number of idle vehicles
            for veh in self.vehs:
                if veh.idle:
                    noi += 1
            print('        T = %.0f, reqs in queue: %d, reqs in pool: %d, idle vehs: %d / %d'
                  % (self.T, len(self.queue), len(self.queue) + len(self.reqs_picking) + len(self.reqs_unassigned), noi,
                     self.V))
        # debug code ends

        if np.isclose(T % INT_ASSIGN, 0):
            if IS_DEBUG:
                print('    -building VT-table ...')
            if MODEE == 'VT_replan' or MODEE == 'VT_replan_all':
                reqs_old = sorted(self.reqs_picking.union(self.reqs_unassigned), key=lambda r: r.id)
                veh_trip_edges = build_vt_table_replan(self.vehs, self.queue, reqs_old, T)
            if MODEE == 'VT':
                veh_trip_edges = build_vt_table(self.vehs, self.queue, T)

            if self.assign == 'ILP':
                if IS_DEBUG:
                    print('    -start ILP assign with %d edges...' % len(veh_trip_edges))
                # R_id_assigned1, V_id_assigned1, schedule_assigned1 = greedy_assign(veh_trip_edges)
                if MODEE == 'VT_replan' or MODEE == 'VT_replan_all':
                    R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(veh_trip_edges, reqs_old + self.queue,
                                                                                 self.rid_assigned_last)
                if MODEE == 'VT':
                    R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(veh_trip_edges, self.queue,
                                                                                 self.rid_assigned_last)
                # assert len(R_id_assigned1) <= len(R_id_assigned)
                # if len(R_id_assigned1) > len(R_id_assigned):
                #     R_id_assigned = R_id_assigned1
                #     V_id_assigned = V_id_assigned1
                #     schedule_assigned = schedule_assigned1

            if IS_DEBUG:
                print('    -execute the assignments...')

            # # debug
            # print()
            # noi = 0  # number of idle vehicles
            # for veh in self.vehs:
            #     if veh.idle:
            #         noi += 1
            # print(' - T = %.0f, reqs in queue: %d, reqs in pool: %d, idle vehs: %d / %d'
            #       % (self.T, len(self.queue), len(self.queue) + len(self.reqs_picking) + len(self.reqs_unassigned), noi,
            #          self.V))

            self.exec_assign(R_id_assigned, V_id_assigned, schedule_assigned)

            # # debug code starts
            # print('   Veh route after assign:')
            # for veh in self.vehs:
            # # if True:
            # #     veh = self.vehs[1071]
            #     d_to_nid = 0
            #     if veh.step_to_nid:
            #         d_to_nid = veh.step_to_nid.d
            #     print('          veh:', veh.id, (veh.nid, round(veh.lng, 4), round(veh.lat, 4)),
            #           ', onboard:', veh.onboard_rid, ', Ts:', round(veh.Ts, 2), ', Ts+V.t:', round(veh.Ts + veh.t, 2),
            #           ', Ds+V.d', round(veh.Ds + veh.d, 2), ', t2nid', round(veh.t_to_nid, 2), ', d2nid',
            #           round(d_to_nid, 2))
            #     sche = [(leg.rid, leg.pod, leg.tlng, leg.tlat, leg.tnid, leg.ddl) for leg in veh.route]
            #     trip = tuple({self.reqs[leg.rid] for leg in veh.route})
            #     c = compute_schedule_cost(veh, trip, sche)
            #     print('              *route:', [(leg.rid, leg.pod) for leg in veh.route],
            #           't:', round(veh.t, 2), 'd:', round(veh.d, 2), ', c:', c)
            #     nids = [veh.nid] + [leg.tnid for leg in veh.route]
            #     t = 0
            #     d = 0
            #     for i in range(len(nids) - 1):
            #         duration1 = get_duration_from_table(nids[i], nids[i + 1])
            #         duration, distance, steps = get_routing_from_networkx(nids[i], nids[i + 1])
            #         assert np.isclose(duration1, duration)
            #         t += duration
            #         d += distance
            #     print('               travel time total', round(t, 2), round(t + veh.t_to_nid, 2))
            #     print('               travel dist total', round(d, 2), round(d + d_to_nid, 2))
            #     assert np.isclose(t+veh.t_to_nid, veh.t)
            #     assert np.isclose(d+d_to_nid, veh.d)
            # # debug code ends

        if np.isclose(T % INT_REBL, 0):
            if self.rebl == 'naive':
                if IS_DEBUG:
                    print('    -start rebalancing...')
                R_id_rebl, V_id_rebl, schedule_rebl = naive_rebalance(self.vehs, self.reqs_unassigned)
                self.exec_rebl(R_id_rebl, V_id_rebl, schedule_rebl)
            # else:
            #     self.rejs.extend(list(self.reqs_unassigned))
            #     self.reqs_unassigned.clear()

    # update vehs and reqs status to their current positions at time T
    def upd_vehs_and_reqs_stat_to_time(self):
        for veh in self.vehs:
            veh.new_pick_rid.clear()
            veh.new_drop_rid.clear()
            done = veh.move_to_time(self.T)
            for (rid, pod, t) in done:
                if pod == 1:
                    veh.new_pick_rid.append(rid)
                    veh.onboard_rid.append(rid)
                    veh.onboard_reqs.add(self.reqs[rid])
                    self.reqs[rid].Tp = t
                    self.reqs_picking.remove(self.reqs[rid])
                    self.reqs_serving.add(self.reqs[rid])
                elif pod == -1:
                    veh.new_drop_rid.append(rid)
                    veh.onboard_rid.remove(rid)
                    veh.onboard_reqs.remove(self.reqs[rid])
                    self.reqs[rid].Td = t
                    self.reqs[rid].D = (self.reqs[rid].Td - self.reqs[rid].Tp) / self.reqs[rid].Ts
                    self.reqs_serving.remove(self.reqs[rid])
                    self.reqs_served.add(self.reqs[rid])

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self):
        req_idx = self.req_init_idx + int(self.N / self.D)
        while (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds <= self.T:
            req = Req(self.N, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds,
                      self.reqs_data.iloc[req_idx]['olng'], self.reqs_data.iloc[req_idx]['olat'],
                      self.reqs_data.iloc[req_idx]['dlng'], self.reqs_data.iloc[req_idx]['dlat'])
            # print('req_idx:', req_idx, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds, req.Ts)

            # check the travel time of a trip is not zero
            if req.Ts > 1:
                self.reqs.append(req)
                self.N += 1
                req_idx = self.req_init_idx + int(self.N / self.D)
                self.queue.append(self.reqs[-1])
            else:
                print('bad data found: req', self.N, req.olng, req.olat)
        assert self.N == len(self.reqs)

    # execute the assignment from AssignPlanner and build (update) route for vehicles
    def exec_assign(self, R_id_assigned, V_id_assigned, schedule_assigned):
        if MODEE == 'VT_replan' or MODEE == 'VT_replan_all':
            reqs_pool = list(self.reqs_picking) + list(self.reqs_unassigned) + self.queue
            assert len(reqs_pool) == len(set(reqs_pool))
            self.queue.clear()
            self.reqs_picking.clear()
            R_assigned_failed = set()
            for veh in self.vehs:
                schedule = []
                if veh.id in V_id_assigned:
                    schedule = schedule_assigned[V_id_assigned.index(veh.id)]
                else:
                    if not veh.idle:
                        for leg in veh.route:
                            if leg.rid in veh.onboard_rid:
                                schedule.append((leg.rid, leg.pod, leg.tlng, leg.tlat, leg.tnid, leg.ddl))
                rid_fail = veh.build_route(schedule, self.reqs, self.T)
                if rid_fail:
                    R_assigned_failed.update({self.reqs[rid] for rid in rid_fail})
            R_assigned = {self.reqs[rid] for rid in R_id_assigned} - R_assigned_failed
            self.reqs_picking.update(R_assigned)
            self.reqs_unassigned = set(reqs_pool) - R_assigned
            self.rid_assigned_last = set(R_id_assigned) - {req.id for req in R_assigned_failed}

        if MODEE == 'VT':
            R_assigned_failed = set()
            for veh_id, schedule in zip(V_id_assigned, schedule_assigned):
                rid_fail = self.vehs[veh_id].build_route(schedule, self.reqs, self.T)
                if rid_fail:
                    R_assigned_failed.update({self.reqs[rid] for rid in rid_fail})
            R_assigned = {self.reqs[rid] for rid in R_id_assigned} - R_assigned_failed
            self.reqs_picking.update(R_assigned)
            R_unassigned = set(self.queue) - R_assigned
            self.reqs_unassigned.update(R_unassigned)
            self.queue.clear()

        # debug code starts
        reqs_on_vehs = []
        for veh in self.vehs:
            trip = {leg.rid for leg in veh.route}
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))
        # debug code ends

    # execute the assignment from Rebalancer and build route for ilde vehicles
    def exec_rebl(self, R_id_rebl, V_id_rebl, schedule_rebl):
        for rid, vid, schedule in zip(R_id_rebl, V_id_rebl, schedule_rebl):
            rid_fail = self.vehs[vid].build_route(schedule, self.reqs, self.T)
            assert rid_fail is None
            self.vehs[vid].VTtable[0] = [(tuple([self.reqs[rid]]), [schedule])]
        self.rid_assigned_last.update(R_id_rebl)
        R_rebl = {self.reqs[rid] for rid in R_id_rebl}
        self.reqs_picking.update(R_rebl)
        self.reqs_unassigned.difference_update(R_rebl)
        if len(self.reqs_unassigned) > 0:
            reqs_rejected = set()
            for req in self.reqs_unassigned:
                if req.Clp >= self.T:
                    self.rejs.append(req)
                    reqs_rejected.add(req)
            self.reqs_unassigned.difference_update(reqs_rejected)

        # debug code starts
        reqs_on_vehs = []
        for veh in self.vehs:
            trip = {leg.rid for leg in veh.route}
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))
        # debug code ends

    # visualize
    def draw(self):
        fig = plt.figure(figsize=(5, 6))
        plt.xlim((-0.02, 0.18))
        plt.ylim((51.29, 51.44))
        for veh in reversed(self.vehs):
            veh.draw()
        for req in self.queue:
            req.draw()
        plt.show()

    def __str__(self):
        str = 'AMoD system at t = %.2f: %d requests in queue' % (self.T, len(self.queue))
        # for r in self.queue:
        #     str += '\n' + r.__str__()
        return str
