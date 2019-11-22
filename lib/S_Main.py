"""
main structure for the AMoD simulator
"""

import time
import datetime
import pickle
import numpy as np
import matplotlib.pyplot as plt
from dateutil.parser import parse

from lib.Configure import DMD_VOL, FLEET_SIZE, VEH_CAPACITY, MET_ASSIGN, MET_REBL, STN_LOC, REQ_DATA, \
    DMD_SST, INT_ASSIGN, INT_REBL, MODEE, IS_DEBUG, IS_STOCHASTIC
from lib.S_Request import Req
from lib.S_Route import upd_traffic_on_network
from lib.S_Vehicle import Veh
from lib.A1_FSP_Main import FSP


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
        rid_assigned_last: the list of id of requests being picked up or on board

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
        self.dispatcher = FSP()
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M')

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        self.T = T
        # update status of vehicles and requests
        if IS_DEBUG:
            print('    -T = %d, updating status of vehicles and requests...' % self.T)
        s1 = time.time()
        self.upd_vehs_and_reqs_stat_to_time()
        if IS_DEBUG:
            print('        s1 running time:', round((time.time() - s1), 2))
        # update traffic
        if IS_STOCHASTIC:
            if IS_DEBUG:
                print('    -T = %d, updating traffics ...' % self.T)
            s2 = time.time()
            upd_traffic_on_network()
            if IS_DEBUG:
                print('        s2 running time:', round((time.time() - s2), 2))
        # generate new reqs
        if IS_DEBUG:
            print('    -T = %d, loading new reqs ...' % self.T)
        s3 = time.time()
        self.gen_reqs_to_time()
        if IS_DEBUG:
            print('        s3 running time:', round((time.time() - s3), 2))

        # debug code starts
        if IS_DEBUG:
            noi = 0  # number of idle vehicles
            for veh in self.vehs:
                if veh.idle:
                    noi += 1
            print('            reqs in queue: %d, reqs in pool: %d, idle vehs: %d / %d'
                  % (len(self.queue), len(self.queue) + len(self.reqs_picking) + len(self.reqs_unassigned), noi,
                     self.V))
        # debug code ends

        if np.isclose(T % INT_ASSIGN, 0):
            # compute the assignment
            R_assigned, V_assigned, S_assigned = \
                self.dispatcher.dispatch(self.vehs, self.queue, self.reqs_picking, self.reqs_unassigned, self.T)
            # execute the assignment
            if IS_DEBUG:
                print('    -T = %d, execute the assignments...' % self.T)
            s4 = time.time()
            self.exec_assign(R_assigned, V_assigned, S_assigned)
            if IS_DEBUG:
                print('        s4 running time:', round((time.time() - s4), 2))
                # debug code starts
                noi = 0  # number of idle vehicles
                for veh in self.vehs:
                    if veh.idle:
                        noi += 1
                print('            idle vehs: %d / %d' % (noi, self.V))
                # debug code ends

        # reject long waited requests
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
    def exec_assign(self, R_assigned, V_assigned, S_assigned):
        for veh, schedule in zip(V_assigned, S_assigned):
            veh.build_route(schedule, self.reqs, self.T)
        if IS_STOCHASTIC:
            for veh in self.vehs:
                schedule = []
                if not veh.idle and veh not in V_assigned:
                    for leg in veh.route:
                        if leg.pod == 1 or leg.pod == -1:
                            schedule.append((leg.rid, leg.pod, leg.tnid, leg.ddl, leg.pf_path))
                    veh.build_route(schedule, self.reqs, self.T)

        reqs_pool = sorted(self.reqs_picking.union(self.reqs_unassigned), key=lambda r: r.id) + self.queue
        debug = len(reqs_pool)
        self.queue.clear()
        assert debug == len(reqs_pool)
        self.reqs_picking.update(set(R_assigned))
        assert debug == len(reqs_pool)
        self.reqs_unassigned = set(reqs_pool) - self.reqs_picking
        assert debug == len(reqs_pool)

        # debug code starts
        reqs_on_vehs = []
        for veh in self.vehs:
            trip = {leg.rid for leg in veh.route}
            if -2 in trip:
                trip.remove(-2)
            reqs_on_vehs.extend(list(trip))
        assert len(reqs_on_vehs) == len(set(reqs_on_vehs))
        # debug code ends

    # # execute the assignment from Rebalancer and build route for rebalancing vehicles (not used)
    # def exec_rebalancing(self, V_id_assigned, schedule_assigned):
    #     for vid, schedule in zip(V_id_assigned, schedule_assigned):
    #         assert self.vehs[vid].idle
    #         assert self.vehs[vid].t_to_nid == 0
    #         self.vehs[vid].build_route(schedule, self.reqs, self.T)
    #         assert schedule[0][0] == -1

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
