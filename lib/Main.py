"""
main structure for the AMoD simulator
"""

import time
import pickle
import numpy as np
import matplotlib.pyplot as plt
from dateutil.parser import parse

from lib.Configure import DMD_VOL, FLEET_SIZE, VEH_CAPACITY, MET_ASSIGN, NON_SHARE, MET_REBL, STN_LOC, REQ_DATA, \
    DMD_SST, INT_ASSIGN, INT_REBL, MODEE, IS_DEBUG, IS_STOCHASTIC
from lib.Request import Req
from lib.VTtable import build_vt_table
from lib.AssignPlanner import ILP_assign
from lib.Rebalancer import find_non_shared_trips, naive_rebalancing
from lib.Route import upd_traffic_on_network
from lib.Vehicle import Veh


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
        self.rejs = set()
        self.rid_assigned_last = set()

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        self.T = T
        if IS_DEBUG:
            print('    -updating status of vehicles and requests...')
        a1 = time.time()
        self.upd_vehs_and_reqs_stat_to_time()
        if IS_DEBUG:
            print('        a1 running time:', round((time.time() - a1), 2))

        if IS_STOCHASTIC:
            _h = int((T-30)/3600)
            h = int(T/3600)
            if IS_DEBUG:
                print('    -updating traffics (h = %d) ...' % h)
            a11 = time.time()
            if T == 30 or _h != h:
                upd_traffic_on_network(h)
            if IS_DEBUG:
                print('        a11 running time:', round((time.time() - a11), 2))

        if IS_DEBUG:
            print('    -loading new reqs ...')
        a2 = time.time()
        self.gen_reqs_to_time()
        if IS_DEBUG:
            print('        a2 running time:', round((time.time() - a2), 2))

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
            if MODEE == 'VT':
                reqs_old = []
                reqs_new = self.queue
            else:  # 'VT_replan'
                reqs_old = sorted(self.reqs_picking.union(self.reqs_unassigned), key=lambda r: r.id)
                reqs_new = self.queue

            if IS_DEBUG:
                print('    -building VT-table ...')
            a3 = time.time()
            veh_trip_edges = build_vt_table(self.vehs, reqs_new, reqs_old, T)
            if IS_DEBUG:
                print('        a3 running time:', round((time.time() - a3), 2))

            # # debug
            # if len(self.rid_assigned_last) != 0:
            #     vehs = self.vehs
            #     with open('vehs.pickle', 'wb') as f:
            #         pickle.dump(vehs, f)
            #     with open('veh_trip_edges.pickle', 'wb') as f:
            #         pickle.dump(veh_trip_edges, f)
            #     reqs_pool = reqs_old + reqs_new
            #     with open('reqs_pool.pickle', 'wb') as f:
            #         pickle.dump(reqs_pool, f)
            #     rid_assigned_last = self.rid_assigned_last
            #     with open('rid_assigned_last.pickle', 'wb') as f:
            #         pickle.dump(rid_assigned_last, f)

            if self.assign == 'ILP':
                if IS_DEBUG:
                    print('    -start ILP assign with %d edges...' % len(veh_trip_edges))
                a4 = time.time()
                R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(veh_trip_edges, reqs_old + reqs_new,
                                                                             self.rid_assigned_last)
                if IS_DEBUG:
                    print('        a4 running time:', round((time.time() - a4), 2))

            # # debug
            # if len(self.rid_assigned_last) != 0:
            #     quit()

            if IS_DEBUG:
                print('    -execute the assignments...')
            a5 = time.time()
            self.exec_assign(R_id_assigned, V_id_assigned, schedule_assigned)
            if IS_DEBUG:
                print('        a5 running time:', round((time.time() - a5), 2))

            if NON_SHARE:
                if IS_DEBUG:
                    print('    -start assigning non-shared trips...')
                a6 = time.time()
                R_id_non_shared, V_id_non_shared, schedule_non_shared = find_non_shared_trips(self.vehs,
                                                                                              self.reqs_unassigned)
                self.exec_non_shared_assign(R_id_non_shared, V_id_non_shared, schedule_non_shared)
                if IS_DEBUG:
                    print('        a6 running time:', round((time.time() - a6), 2))
                    # debug code starts
                    noi = 0  # number of idle vehicles
                    for veh in self.vehs:
                        if veh.idle:
                            noi += 1
                    print('            idle vehs: %d / %d' % (noi, self.V))
                    # debug code ends

        if np.isclose(T % INT_REBL, 0):
            if self.rebl == 'naive':
                if IS_DEBUG:
                    print('    -start rebalancing...')
                a7 = time.time()
                rebalancing_reqs = [self.reqs[rid] for rid in R_id_non_shared]
                V_id_rebl, schedule_rebl = naive_rebalancing(self.vehs, rebalancing_reqs)
                self.exec_rebalancing(V_id_rebl, schedule_rebl)
                if IS_DEBUG:
                    print('        a7 running time:', round((time.time() - a7), 2))
                    # debug code starts
                    noi = 0  # number of idle vehicles
                    for veh in self.vehs:
                        if veh.idle:
                            noi += 1
                    print('            idle vehs: %d / %d' % (noi, self.V))
                    # debug code ends

        if len(self.reqs_unassigned) > 0:
            reqs_rejected = set()
            for req in self.reqs_unassigned:
                # if req.Clp <= self.T:
                if min(req.Tr + 150, req.Clp) <= self.T:
                    reqs_rejected.add(req)
            self.reqs_unassigned.difference_update(reqs_rejected)
            self.rejs.update(reqs_rejected)

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
            assert len(veh.onboard_rid) == len(veh.onboard_reqs)

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self):
        req_idx = self.req_init_idx + int(self.N / self.D)
        while (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds <= self.T:
            req = Req(self.N, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds,
                      self.reqs_data.iloc[req_idx]['olng'], self.reqs_data.iloc[req_idx]['olat'],
                      self.reqs_data.iloc[req_idx]['dlng'], self.reqs_data.iloc[req_idx]['dlat'])
            # print('req_idx:', req_idx, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds, req.Ts)
            self.reqs.append(req)
            self.N += 1
            req_idx = self.req_init_idx + int(self.N / self.D)
            self.queue.append(self.reqs[-1])
            # check the travel time of a trip is not zero
            assert req.Ts > 1
        assert self.N == len(self.reqs)

    # execute the assignment from AssignPlanner and build (update) route for assigned vehicles
    def exec_assign(self, R_id_assigned, V_id_assigned, schedule_assigned):
        if MODEE == 'VT':
            for veh_id, schedule in zip(V_id_assigned, schedule_assigned):
                self.vehs[veh_id].build_route(schedule, self.reqs, self.T)
            if IS_STOCHASTIC:
                for veh in self.vehs:
                    schedule = []
                    if veh.id not in V_id_assigned:
                        if not veh.idle:
                            for leg in veh.route:
                                if leg.pod == 1 or leg.pod == -1:
                                    schedule.append((leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path))
                            veh.build_route(schedule, self.reqs, self.T)
            R_assigned = {self.reqs[rid] for rid in R_id_assigned}
            self.reqs_picking.update(R_assigned)
            R_unassigned = set(self.queue) - R_assigned
            self.reqs_unassigned.update(R_unassigned)
            self.queue.clear()

        if MODEE == 'VT_replan' or MODEE == 'VT_replan_all':
            reqs_pool = list(self.reqs_picking) + list(self.reqs_unassigned) + self.queue
            assert len(reqs_pool) == len(set(reqs_pool))
            self.queue.clear()
            self.reqs_picking.clear()
            for veh in self.vehs:
                schedule = []
                if veh.id in V_id_assigned:
                    schedule = schedule_assigned[V_id_assigned.index(veh.id)]
                    if not IS_STOCHASTIC:
                        if schedule == [(leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path) for leg in veh.route]:
                            # vehicles with the same trip
                            continue
                else:
                    if not veh.idle:
                        if not IS_STOCHASTIC:
                            if 1 not in {leg.pod for leg in veh.route}:
                                # vehicles neither assigned new requests nor having new request to pick up
                                continue
                        for leg in veh.route:
                            if leg.rid in veh.onboard_rid:
                                    schedule.append((leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path))
                veh.build_route(schedule, self.reqs, self.T)
            R_assigned = {self.reqs[rid] for rid in R_id_assigned}
            self.reqs_picking.update(R_assigned)
            self.reqs_unassigned = set(reqs_pool) - R_assigned
            self.rid_assigned_last = set(R_id_assigned)

        # debug code starts
        reqs_on_vehs = []
        for veh in self.vehs:
            trip = {leg.rid for leg in veh.route}
            if -2 in trip:
                trip.remove(-2)
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))
        # debug code ends

    # execute the assignment from 'find_non_shared_trips' and build route for assigned vehicles
    def exec_non_shared_assign(self, R_id_assigned, V_id_assigned, schedule_assigned):
        for rid, vid, schedule in zip(R_id_assigned, V_id_assigned, schedule_assigned):
            assert self.vehs[vid].idle
            self.vehs[vid].build_route(schedule, self.reqs, self.T)
            self.vehs[vid].VTtable[0] = [(tuple([self.reqs[rid]]), schedule, 0, [schedule])]
        R_assigned = {self.reqs[rid] for rid in R_id_assigned}
        self.reqs_picking.update(R_assigned)
        self.reqs_unassigned.difference_update(R_assigned)
        if MODEE == 'VT_replan' or MODEE == 'VT_replan_all':
            self.rid_assigned_last.update(R_id_assigned)

        # debug code starts
        reqs_on_vehs = []
        for veh in self.vehs:
            trip = {leg.rid for leg in veh.route}
            if -2 in trip:
                trip.remove(-2)
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))
        # debug code ends

    # execute the assignment from Rebalancer and build route for rebalancing vehicles
    def exec_rebalancing(self, V_id_assigned, schedule_assigned):
        for vid, schedule in zip(V_id_assigned, schedule_assigned):
            assert self.vehs[vid].idle
            assert self.vehs[vid].t_to_nid == 0
            self.vehs[vid].build_route(schedule, self.reqs, self.T)
            assert schedule[0][0] == -1

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
