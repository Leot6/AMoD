"""
main structure for the AMoD simulator
"""

import time
import datetime
import numpy as np
import matplotlib.pyplot as plt

from lib.simulator.config import *
from lib.simulator.request import Req
from lib.simulator.vehicle import Veh
from lib.routing.routing_server import upd_traffic_on_network, print_counting
from lib.dispatcher.gi.greedy_insertion import GI
from lib.dispatcher.sba.single_req_batch_assign import SBA
from lib.dispatcher.rtv.rtv_main import RTV
from lib.dispatcher.osp.osp_main import OSP
from lib.rebalancer.naive_rebalancer import NR


class Model(object):
    """
    Model is the initial class for the AMoD system
    Attributes:
        T: system time at current state
        D: demand volume (percentage of total)
        V: number of vehicles
        K: capacity of vehicles
        N: number of requests received
        vehs: the list of vehicles
        reqs_data: the list of collected real taxi requests data
        req_init_idx: init index to read reqs_data
        queue: requests in the queue
        reqs: the list of all received requests
        reqs_served: the list of completed requests
        reqs_onboard: the list of requests on board
        reqs_picking: the list of requests being picked up
        reqs_unassigned: the list of requests unassigned in the planning pool
        rejs: the list of rejected requests
        dispatcher: the algorithm used to do the dispatching

    """

    def __init__(self, init_time):
        self.T = 0.0
        self.D = DMD_VOL
        self.V = FLEET_SIZE
        self.K = VEH_CAPACITY
        self.N = 0
        self.vehs = []
        for i in range(self.V):
            idx = int(i * len(STN_LOC) / self.V)
            self.vehs.append(Veh(i, int(STN_LOC.iloc[idx]['id']),
                                 STN_LOC.iloc[idx]['lng'], STN_LOC.iloc[idx]['lat'], K=self.K))
        self.reqs_data = REQ_DATA
        self.req_init_idx = REQ_INIT_IDX
        while parse(self.reqs_data.iloc[self.req_init_idx]['ptime']) < DMD_SST:
            self.req_init_idx += 1
        print('self.req_init_idx', self.req_init_idx)
        self.queue = []
        self.reqs = []
        self.reqs_served = set()
        self.reqs_onboard = set()
        self.reqs_picking = set()
        self.reqs_unassigned = set()
        self.rejs = set()
        if DISPATCHER == 'OSP':
            self.dispatcher = OSP(self)
        elif DISPATCHER == 'RTV':
            self.dispatcher = RTV(self)
        elif DISPATCHER == 'GI':
            self.dispatcher = GI(self)
        elif DISPATCHER == 'SBA':
            self.dispatcher = SBA(self)
        if REBALANCER == 'NR':
            self.rebalancer = NR(self)
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M')
        self.end_time = None
        self.time_of_init = round(time.time() - init_time, 2)
        self.time_of_run = None
        self.avg_time_of_run = None

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        self.T = T

        # 1. reject long waited requests
        self.reject_long_wait_reqs()
        # 2. update statuses of vehicles and requests
        self.upd_vehs_and_reqs_stat_to_time()
        # 3. update traffic
        self.update_traffic()
        # 4. generate new reqs
        self.gen_reqs_to_time()
        if np.isclose(T % INT_ASSIGN, 0):
            # 5. compute the assignment
            vids_assigned = self.dispatcher.dispatch(T)
            print_counting()
            # 6. update traffic on routes of vehicles
            self.upd_traffic_on_route_of_vehs(vids_assigned)
            # check assignment and update reqs clustering status
            self.assign_constraint_check_and_upd_reqs_grouping_status()

        if np.isclose(T % INT_REBL, 0):
            # 7. rebalancing
            self.rebalancing_idle_vehs()

    def reject_long_wait_reqs(self):
        if len(self.reqs_unassigned) > 0:
            reqs_rejected = set()
            for req in self.reqs_unassigned:
                # if req.Clp <= self.T:
                if min(req.Tr + 150, req.Clp) <= self.T:
                    reqs_rejected.add(req)
            self.reqs_unassigned.difference_update(reqs_rejected)
            self.rejs.update(reqs_rejected)

    def update_traffic(self):
        if IS_STOCHASTIC:
            if IS_DEBUG:
                print('    -T = %d, updating traffics ...' % self.T)
            s2 = time.time()
            upd_traffic_on_network()
            if IS_DEBUG:
                print('        s2 running time:', round((time.time() - s2), 2))

    # update vehs and reqs status to their current positions at time T
    def upd_vehs_and_reqs_stat_to_time(self):
        if IS_DEBUG:
            print('    -T = %d, updating status of vehicles and requests...' % self.T)
            s1 = time.time()
        for veh in self.vehs:
            done = veh.move_to_time(self.T)
            for (rid, pod, t) in done:
                if pod == 1:
                    self.reqs[rid].Tp = t
                    self.reqs_picking.remove(self.reqs[rid])
                    self.reqs_onboard.add(self.reqs[rid])
                    # print('veh', veh.id, 'picked', rid)

                elif pod == -1:
                    self.reqs[rid].Td = t
                    self.reqs[rid].D = (self.reqs[rid].Td - self.reqs[rid].Tp) / self.reqs[rid].Ts
                    self.reqs_onboard.remove(self.reqs[rid])
                    self.reqs_served.add(self.reqs[rid])

                    # print('veh', veh.id, 'dropped', rid)

        if IS_DEBUG:
            print('        s1 running time:', round((time.time() - s1), 2))

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self):
        if IS_DEBUG:
            print('    -T = %d, loading new reqs ...' % self.T)
            s3 = time.time()
        req_idx = self.req_init_idx + int(self.N / self.D)
        while (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds <= self.T:
            req = Req(self.N, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds,
                      self.reqs_data.iloc[req_idx]['onid'], self.reqs_data.iloc[req_idx]['dnid'],
                      self.reqs_data.iloc[req_idx]['olng'], self.reqs_data.iloc[req_idx]['olat'],
                      self.reqs_data.iloc[req_idx]['dlng'], self.reqs_data.iloc[req_idx]['dlat'])
            # print('req_idx:', req_idx, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds, req.Ts)
            self.reqs.append(req)
            self.N += 1
            req_idx = self.req_init_idx + int(self.N / self.D)
            self.queue.append(self.reqs[-1])
            assert req.Ts > 150
        assert self.N == len(self.reqs)
        if IS_DEBUG:
            print('        s3 running time:', round((time.time() - s3), 2))
            noi = 0  # number of idle vehicles
            for veh in self.vehs:
                if veh.idle:
                    noi += 1
            print(f'            reqs in queue: {len(self.queue)}, '
                  f'reqs in pool: {len(self.queue) + len(self.reqs_picking) + len(self.reqs_unassigned)}, '
                  f'idle vehs: {noi} / {self.V}')

    def upd_traffic_on_route_of_vehs(self, vids_assigned):
        if IS_STOCHASTIC:
            if IS_DEBUG:
                print('    -T = %d, update traffic on routes of vehicles...' % self.T)
                s4 = time.time()
            for veh in self.vehs:
                schedule = []
                if not veh.idle and veh.id not in vids_assigned:
                    for leg in veh.route:
                        if leg.pod == 1 or leg.pod == -1:
                            schedule.append((leg.rid, leg.pod, leg.tnid, leg.ept, leg.ddl))
                    veh.build_route(schedule, self.reqs, self.T)
            if IS_DEBUG:
                print('        s4 running time:', round((time.time() - s4), 2))

    def assign_constraint_check_and_upd_reqs_grouping_status(self):
        #  check each req is not assigned to multiple vehs
        rids_enroute = []
        rids_picking = []
        rids_onboard = []
        for veh in self.vehs:
            T_id = {leg.rid for leg in veh.route} - {-2}
            rids_enroute.extend(list(T_id))
            rids_picking.extend(veh.picking_rids)
            rids_onboard.extend(veh.onboard_rids)
        assert len(rids_enroute) == len(set(rids_enroute))
        assert sorted(rids_enroute) == sorted(rids_onboard + rids_picking)
        assert set(rids_onboard) == {req.id for req in self.reqs_onboard}

        # update reqs grouping status
        if not DISPATCHER == 'GI':
            rids_enroute.sort()
            reqs_picking = {self.reqs[rid] for rid in rids_picking}
            reqs_unassigned = set(self.queue).union(self.reqs_unassigned).union(self.reqs_picking) - reqs_picking
            self.queue.clear()
            self.reqs_picking.clear()
            self.reqs_unassigned.clear()
            self.reqs_picking.update(reqs_picking)
            self.reqs_unassigned.update(reqs_unassigned)

        # req status check
        all_reqs = list(self.reqs_picking) + list(self.reqs_onboard) + list(self.reqs_served) \
                   + list(self.reqs_unassigned) + list(self.rejs)
        assert len(all_reqs) == len(self.reqs)
        assert set(all_reqs) == set(self.reqs)

    def rebalancing_idle_vehs(self):
        if REBALANCER == 'NR':
            self.rebalancer.rebelancing(self.T)

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
        str = f'scenario: {DMD_STR}' \
              f'\nsimulation starts at {self.start_time}, initializing time: {self.time_of_init} s' \
              f'\nsimulation ends at {self.end_time}, runtime time: {self.time_of_run}, ' \
              f'average: {self.avg_time_of_run}' \
              f'\nsystem settings:' \
              f'\n  - from {DMD_SST} to {DMD_SST + datetime.timedelta(seconds=T_TOTAL)}, ' \
              f'with {round(T_TOTAL / INT_ASSIGN)} intervals' \
              f'\n  - fleet size: {self.V}; capacity: {self.K}; coef_wait: {COEF_WAIT}, interval: {INT_ASSIGN} s' \
              f'\n  - demand value: {DMD_VOL}({TRIP_NUM}), max waiting time: {MAX_WAIT} s; max delay: {MAX_DELAY} s' \
              f'\n  - {self.dispatcher}, rebalancer: {REBALANCER}' \
              f'\n  - stochastic travel time: {IS_STOCHASTIC}, stochastic planning: {IS_STOCHASTIC_CONSIDERED}'
        return str
