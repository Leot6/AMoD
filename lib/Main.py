"""
main structure for the AMoD simulator
"""

import time
import copy
import numpy as np
import matplotlib.pyplot as plt
from dateutil.parser import parse
from lib.Configure import DMD_VOL, FLEET_SIZE, VEH_CAPACITY, MET_ASSIGN, MET_REBL, \
    STN_LOC, REQ_DATA, DMD_SST, INT_ASSIGN, INT_REBL
from lib.Vehicle import Veh
from lib.Request import Req
from lib.RTVgenerator import build_rtv_graph
from lib.AssignPlanner import greedy_assign, ILP_assign
from lib.Rebalancer import rebalance


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
        self.queue_ = []  # for plotting requests only
        self.reqs = []
        self.reqs_served = set()
        self.reqs_serving = set()
        self.reqs_picking = set()
        self.reqs_unassigned = set()
        self.rejs = []

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        self.T = T
        print('updating vehicle status...')
        self.upd_vehs_stat_to_time()
        print('updating served reqs status...')
        self.upd_reqs_stat_to_time()
        print('loading new reqs ...')
        self.gen_reqs_to_time()
        self.queue_ = copy.deepcopy(self.queue)

        # debug code starts
        noi = 0  # number of idle vehicles
        for veh in self.vehs:
            if veh.idle:
                noi += 1
        print(self, ', idle vehs:', noi, '/', self.V)
        # debug code ends

        if np.isclose(T % INT_ASSIGN, 0):
            print('  building RTV-graph...')
            veh_trip_edges = build_rtv_graph(self.vehs, self.queue, T)
            if self.assign == 'ILP':
                R_id_assigned, V_id_assigned, schedule_assigned = greedy_assign(veh_trip_edges)
                print('    -start ILP assign with %d edges:' % len(veh_trip_edges))
                R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(veh_trip_edges, self.queue)
            elif self.assign == 'greedy':
                print('    -start greedy assign with %d edges:' % len(veh_trip_edges))
                R_id_assigned, V_id_assigned, schedule_assigned = greedy_assign(veh_trip_edges)
            self.exec_assign(R_id_assigned, V_id_assigned, schedule_assigned)
        if np.isclose(T % INT_REBL, 0):
            if self.rebl == 'simple':
                print('  -start rebalancing...')
                rebalance(self, T)
            else:
                self.rejs.extend(list(self.reqs_unassigned))
                self.reqs_unassigned.clear()

    # update vehs status to their current positions at time T
    def upd_vehs_stat_to_time(self):
        for veh in self.vehs:
            done = veh.move_to_time(self.T)
            for (rid, pod, t) in done:
                if pod == 1:
                    self.reqs[rid].Tp = t
                elif pod == -1:
                    self.reqs[rid].Td = t
                    self.reqs[rid].D = (self.reqs[rid].Td - self.reqs[rid].Tp) / self.reqs[rid].Ts

    # update reqs statues to time T
    def upd_reqs_stat_to_time(self):
        picked = set()
        dropped = set()
        for req in self.reqs_picking:
            if not np.isclose(req.Tp, -1.0):
                picked.add(req)
        for req in self.reqs_serving:
            if not np.isclose(req.Td, -1.0):
                dropped.add(req)
        self.reqs_picking.difference_update(picked)
        self.reqs_serving.update(picked)
        self.reqs_serving.difference_update(dropped)
        self.reqs_served.update(dropped)

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self):
        req_idx = self.req_init_idx + int(self.N / self.D)
        while (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds <= self.T:
            req = Req(self.N,  (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds,
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

    # execute the assignment from AssignPlanner
    def exec_assign(self, R_id_assigned, V_id_assigned, schedule_assigned):
        for veh_id, schedule in zip(V_id_assigned, schedule_assigned):
            self.vehs[veh_id].build_route(schedule, self.reqs, self.T)
        R_assigned = set()
        for req_id in R_id_assigned:
            R_assigned.add(self.reqs[req_id])
        self.reqs_picking.update(R_assigned)
        R_unassigned = set(self.queue) - R_assigned
        self.reqs_unassigned.update(R_unassigned)
        self.queue.clear()

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
        str = 'AMoD system at t = %.3f: %d requests in queue' % (self.T, len(self.queue))
        # for r in self.queue:
        #     str += '\n' + r.__str__()
        return str
