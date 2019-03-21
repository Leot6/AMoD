"""
main structure for the AMoD simulator
"""

from lib.Request import*
from lib.Dispatcher_FIFO import *
from lib.Dispatcher_RTV import *
from lib.Rebalancer import *


class Model(object):
    """
    Model is the initial class for the AMoD system
    Attributes:
        T: system time at current state
        stn_loc: locations (lng, lat) of stations
        reqs_data: the list of collected real taxi requests data
        req_init_idx: init index to read reqs_data
        D: demand volume (percentage of total)
        V: number of vehicles
        K: capacity of vehicles
        vehs: the list of vehicles
        N: number of requests received
        queue: requests in the queue
        reqs: the list of all received requests
        reqs_served: the list of completed requests
        reqs_serving: the list of requests on board
        reqs_picking: the list of requests being picked up
        reqs_unassigned: the list of requests unassigned in the planning pool
        rejs: the list of rejected requests
        assign: assignment method
        rebl: rebalancing method
    """

    def __init__(self, stn_loc=None, reqs_data=None, D=1, V=2, K=4, assign='ins', rebl='no'):
        self.T = 0.0
        self.stn_loc = stn_loc
        self.reqs_data = reqs_data
        self.req_init_idx = 0
        while parse(self.reqs_data.iloc[self.req_init_idx]['ptime']) < DMD_SST:
            self.req_init_idx += 1
        self.D = D
        self.V = V
        self.K = K
        self.vehs = []
        self.N = 0
        self.queue = []
        self.queue_ = []  # for plotting requests only
        self.reqs = []
        self.reqs_served = set()
        self.reqs_serving = set()
        self.reqs_picking = set()
        self.reqs_unassigned = set()
        self.rejs = []
        self.assign = assign
        self.rebl = rebl

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        self.T = T
        noi = 0  # number of idle vehicles
        print('updating vehicle status...')
        for veh in self.vehs:
            done = veh.move_to_time(T)
            if veh.idle:
                noi += 1
            for (rid, pod, t) in done:
                if pod == 1:
                    self.reqs[rid].Tp = t
                elif pod == -1:
                    self.reqs[rid].Td = t
                    self.reqs[rid].D = (self.reqs[rid].Td - self.reqs[rid].Tp) / self.reqs[rid].Ts

        print('updating served reqs status...')
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

        print('loading new reqs ...')
        self.generate_requests_to_time(T)
        self.queue_ = copy.deepcopy(self.queue)
        print(self, ', idle vehs:', noi, '/', self.V)

        if np.isclose(T % INT_ASSIGN, 0):
            if self.assign == 'ins':
                insertion_heuristics(self, T)
            elif self.assign == 'rtv':
                veh_trip_edges = build_rtv_graph(self.vehs, self.queue, T)
                greedy_assign(self, veh_trip_edges, T)
                # ILP_assign(self, veh_trip_edges, self.queue, T)
        if np.isclose(T % INT_REBL, 0):
            if self.rebl == 'sar':
                rebalance(self, T)

    def init_vehicles(self):
        coef = len(self.stn_loc) / self.V
        for i in range(self.V):
            idx = int(i * coef)
            self.vehs.append(Veh(i, self.stn_loc.iloc[idx]['lng'], self.stn_loc.iloc[idx]['lat'], K=self.K))

    # generate requests up to time T, loading from reqs data file
    def generate_requests_to_time(self, T):
        req_idx = self.req_init_idx + int(self.N / self.D)
        while (parse(self.reqs_data.iloc[req_idx]['ptime']) - DMD_SST).seconds <= T:
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
