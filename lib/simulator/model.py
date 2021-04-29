"""
main structure for the AMoD simulator
"""

import time
import copy
import datetime
import numpy as np
import matplotlib.pyplot as plt

from lib.simulator.config import *
from lib.simulator.request import Req
from lib.simulator.vehicle import Veh
from lib.routing.routing_server import print_counting
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

        # if IS_DEBUG:
        #     print(f"[DEBUG] Check vehicles initial positions")
        #     for veh in self.vehs:
        #         print(f" -vehicle {veh.id} at station {veh.nid}")

        self.reqs_data = REQ_DATA
        self.req_init_idx = REQ_INIT_IDX
        while parse(self.reqs_data.iloc[self.req_init_idx]['ptime']) < DMD_SST:
            self.req_init_idx += 1
        # print('self.req_init_idx', self.req_init_idx)
        self.queue = []
        self.reqs = []
        self.reqs_served = set()
        self.reqs_onboard = set()
        self.reqs_picking = set()
        self.reqs_unassigned = set()
        self.rejs = set()
        self.default_dispatcher = SBA(self)
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

        if IS_DEBUG:
            stime = time.time()
            print(f'[DEBUG] T = {T-INT_ASSIGN}s: '
                  f'Epoch {round(T / INT_ASSIGN)}/{round(T_TOTAL / INT_ASSIGN)} is running.')

        # 1. reject long waited requests
        self.reject_long_wait_reqs()
        # 2. update statuses of vehicles and requests
        self.upd_vehs_and_reqs_stat_to_time()
        # 3. generate new reqs
        self.gen_reqs_to_time()
        if np.isclose(T % INT_ASSIGN, 0):
            # 4. compute the assignment
            if T_WARM_UP <= T <= T_WARM_UP + T_STUDY:
                vids_assigned = self.dispatcher.dispatch(T)
            else:
                vids_assigned = self.default_dispatcher.dispatch(T)
            print_counting()
            # 5. update traffic on routes of vehicles
            self.upd_traffic_on_route_of_vehs(vids_assigned)
            # 6. check assignment and update reqs clustering status
            self.assign_constraint_check_and_upd_reqs_grouping_status()

        if np.isclose(T % INT_REBL, 0):
            # 7. rebalancing
            self.rebalancing_idle_vehs()

        if IS_DEBUG:
            print(f'        T = {T}s: Epoch {round(T / INT_ASSIGN)}/{round(T_TOTAL / INT_ASSIGN)} has finished. '
                  f'Total reqs received = {self.N}, of which {len(self.reqs_served)} complete '
                  f'+ {len(self.reqs_onboard)} onboard + {len(self.reqs_picking)} picking '
                  f'+ {len(self.reqs_unassigned)} pending + {len(self.rejs)} walkaway '
                  f'({round((time.time() - stime), 2)}s)')
            print()

    def reject_long_wait_reqs(self):
        if len(self.reqs_unassigned) > 0:
            if MAX_DETOUR != np.inf:
                reqs_rejected = set()
                for req in self.reqs_unassigned:
                    # if req.Clp <= self.T:
                    if min(req.Tr + 150, req.Clp) <= self.T:
                        reqs_rejected.add(req)
                self.reqs_unassigned.difference_update(reqs_rejected)
                self.rejs.update(reqs_rejected)
            else:
                assert len(self.queue) == 0
                for req in sorted(self.reqs_unassigned, key=lambda r: r.id):
                    assert req.Clp >= req.Clp_backup
                    req.Clp += 120
                    req.Clp_backup = req.Clp
                    req.Cld += 120
                    self.queue.append(req)
                self.reqs_unassigned.difference_update(set(self.queue))
                assert len(self.reqs_unassigned) == 0

    # update vehs and reqs status to their current positions at time T
    def upd_vehs_and_reqs_stat_to_time(self):
        if IS_DEBUG:
            print('        -updating status of vehicles and requests...')
            s1 = time.time()
        for veh in self.vehs:
            done = veh.move_to_time(self.T)
            for (rid, pod, t) in done:
                if pod == 1:
                    self.reqs[rid].update_pick_info(t)
                    self.reqs_picking.remove(self.reqs[rid])
                    self.reqs_onboard.add(self.reqs[rid])
                    # print('veh', veh.id, 'picked', rid)

                elif pod == -1:
                    self.reqs[rid].update_drop_info(t)
                    self.reqs_onboard.remove(self.reqs[rid])
                    self.reqs_served.add(self.reqs[rid])

                    # print('veh', veh.id, 'dropped', rid)

        if IS_DEBUG:
            noi = 0  # number of idle vehicles
            nor = 0  # number of rebalancing vehicles
            nop = 0  # number of picked requests
            nod = 0  # number of dropped requests
            for veh in self.vehs:
                nop += len(veh.new_picked_rids)
                nod += len(veh.new_dropped_rids)
                if veh.idle:
                    noi += 1
                if veh.rebl:
                    nor += 1
            print(f'            +picked reqs: {nop}, dropped reqs: {nod}')
            print(f'            +idle vehs: {noi}/{self.V}, rebl vehs: {nor}/{self.V}  '
                  f'({round((time.time() - s1), 2)}s)')

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self):
        if IS_DEBUG:
            print('        -loading new reqs ...')
            s3 = time.time()
        req_idx = self.req_init_idx + int(self.N / self.D)
        while (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds < self.T:
            req = Req(self.N, (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds,
                      self.reqs_data.iloc[req_idx]['onid'], self.reqs_data.iloc[req_idx]['dnid'],
                      self.reqs_data.iloc[req_idx]['olng'], self.reqs_data.iloc[req_idx]['olat'],
                      self.reqs_data.iloc[req_idx]['dlng'], self.reqs_data.iloc[req_idx]['dlat'])
            self.reqs.append(req)
            self.N += 1
            req_idx = self.req_init_idx + int(self.N / self.D)
            self.queue.append(self.reqs[-1])
            assert req.Ts > 150

            # if IS_DEBUG:
            #     new_req = self.reqs[-1]
            #     print(f'            +req {new_req.id} requested at {new_req.Tr}, '
            #           f'from {new_req.onid} to {new_req.dnid}, Ts = {new_req.Ts}s')

        assert self.N == len(self.reqs)
        if IS_DEBUG:
            print(f'            +new received reqs: {len(self.queue)}  ({round((time.time() - s3), 2)}s)')

            # debug
            # print(f'reqs in queue: {[r.id for r in self.queue]}; reqs picking:{[r.id for r in self.reqs_picking]};'
            #       f'reqs onboard: {[r.id for r in self.reqs_onboard]}')
            # print(f'reqs unassign: {[r.id for r in self.reqs_unassigned]}')
            # for veh in self.vehs:
            #     print(f'veh {veh.id} picking: {veh.picking_rids} dropping: {veh.onboard_rids}')

    def upd_traffic_on_route_of_vehs(self, vids_assigned):
        if IS_STOCHASTIC_TRAFFIC:
            if IS_DEBUG:
                print('    -T = %d, update traffic on routes of vehicles...' % self.T)
                s4 = time.time()
            for veh in self.vehs:
                if not veh.idle and veh.id not in vids_assigned:
                    veh.build_route(copy.deepcopy(veh.sche), self.reqs, self.T)
            if IS_DEBUG:
                print('        s4 running time:', round((time.time() - s4), 2))

    def assign_constraint_check_and_upd_reqs_grouping_status(self):
        # check each req is not assigned to multiple vehs
        rids_enroute = []
        rids_picking = []
        rids_onboard = []
        for veh in self.vehs:
            T_id = {leg.rid for leg in veh.route} - {-2, -1}
            rids_enroute.extend(list(T_id))
            rids_picking.extend(veh.picking_rids)
            rids_onboard.extend(veh.onboard_rids)
        assert len(rids_enroute) == len(set(rids_enroute))
        assert set(rids_onboard) == {req.id for req in self.reqs_onboard}
        assert sorted(rids_enroute) == sorted(rids_onboard + rids_picking)

        # # check that no servable request is unassigned in last epoch
        # rids_unassigned_in_last_epoch = [req.id for req in self.reqs_unassigned]
        # num_reqs_unassigned = len(rids_unassigned_in_last_epoch)
        # rids_missed = set(rids_unassigned_in_last_epoch) - (set(rids_unassigned_in_last_epoch) - set(rids_picking))
        # num_rids_missed = len(rids_missed)
        # if num_rids_missed != 0:
        #     print('rids_missed', rids_missed)
        # if set(rids_unassigned_in_last_epoch) - set(rids_picking) != set(rids_unassigned_in_last_epoch):
        #     print('rids_unassigned_in_last_epoch', rids_unassigned_in_last_epoch)
        #     print('picking', rids_picking)
        #     print('set(rids_unassigned_in_last_epoch) - set(rids_picking)',
        #           set(rids_unassigned_in_last_epoch) - set(rids_picking))
        # assert set(rids_unassigned_in_last_epoch) - set(rids_picking) == set(rids_unassigned_in_last_epoch)

        # update reqs grouping status
        if DISPATCHER != 'GI':
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
        param = f'scenario: {DMD_STR}' \
                f'\nsimulation starts at {self.start_time}, initializing time: {self.time_of_init} s' \
                f'\nsimulation ends at {self.end_time}, runtime time: {self.time_of_run},' \
                f' average: {self.avg_time_of_run} s' \
                f'\nsystem settings:' \
                f'\n  - from {DMD_SST} to {DMD_SST + datetime.timedelta(seconds=T_TOTAL)},' \
                f' with {round(T_WARM_UP / INT_ASSIGN)}+{round(T_STUDY / INT_ASSIGN)}+' \
                f'{round(T_COOL_DOWN / INT_ASSIGN)}={round(T_TOTAL / INT_ASSIGN)} intervals' \
                f'\n  - fleet size: {self.V}, capacity: {self.K}, interval: {INT_ASSIGN} s, objective: {OBJECTIVE}' \
                f' ({Reliability_Shreshold})' \
                f'\n  - demand value: {DMD_VOL}({TRIP_NUM}), max waiting: {MAX_WAIT} s, max delay: {MAX_DELAY} s' \
                f' ({MAX_DETOUR})' \
                f'\n  - {self.dispatcher}, rebalancer: {REBALANCER}' \
                f'\n  - stochastic traffic: {IS_STOCHASTIC_TRAFFIC}, scheduling: {IS_STOCHASTIC_SCHEDULE},' \
                f' routing: {IS_STOCHASTIC_ROUTING} ({LEVEl_OF_STOCHASTIC})'
        return param
