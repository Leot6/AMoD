"""
initialization for the AMoD system
"""

from lib.Request import*
from lib.Dispatcher_FIFO import *
from lib.Dispatcher_RTV import *


class Model(object):
    """
    Model is the initial class for the AMoD system
    Attributes:
        rs1: a seeded random generator for requests
        rs2: a seeded random generator for vehicle locations
        T: system time at current state
        M: demand matrix
        D: demand volume (trips/hour)
        V: number of vehicles
        K: capacity of vehicles
        vehs: the list of vehicles
        N: number of requests
        queue: requests in the queue
        reqs: the list of requests
        reqs_served: the list of completed requests
        reqs_serving: the list of requests on board
        reqs_picking: the list of requests being picked up
        rejs: the list of rejected requests
        assign: assignment method
        rebl: rebalancing method
    """

    def __init__(self, M, D, V=2, K=4, assign="ins", rebl="no"):
        # two random generators, the seed of which could be modified for debug use
        self.rs1 = np.random.RandomState(np.random.randint(0, 1000000))
        self.rs2 = np.random.RandomState(np.random.randint(0, 1000000))
        self.T = 0.0
        self.M = M
        self.D = D
        self.V = V
        self.K = K
        self.vehs = []
        for i in range(V):
            self.vehs.append(Veh(i, self.rs2, K=K))
        self.N = 0
        self.queue = []
        self.queue_ = []  # for plotting requests only
        self.reqs = []
        self.reqs_served = set()
        self.reqs_serving = set()
        self.reqs_picking = set()
        self.rejs = []
        self.assign = assign
        self.rebl = rebl

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, osrm, T):
        self.T = T
        noi = 0
        for veh in self.vehs:
            if veh.idle:
                noi += 1
            done = veh.move_to_time(T)
            for (rid, pod, t) in done:
                if pod == 1:
                    self.reqs[rid].Tp = t
                elif pod == -1:
                    self.reqs[rid].Td = t
                    self.reqs[rid].D = (self.reqs[rid].Td - self.reqs[rid].Tp) / self.reqs[rid].Ts

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

        self.generate_requests_to_time(osrm, T)

        self.queue_ = copy.deepcopy(self.queue)
        if T >= 30:
            print(self, ", idle vehs:", noi, "/", self.V)
            if np.isclose(T % INT_ASSIGN, 0):
                if self.assign == "ins":
                    # print("Running insertion_heuristics...")
                    # stime_assign = time.clock()
                    insertion_heuristics(self, osrm, T)
                    # runtime_assign = time.clock() - stime_assign
                    # print("...running time of assign: %.05f seconds" % runtime_assign)
                elif self.assign == "rtv":
                    build_rtv_graph(self, osrm, T)
#            if np.isclose(T % INT_REBL, 0):
#                self.rebalance_sar(osrm)

    # generate requests up to time T, following Poisson process
    def generate_requests_to_time(self, osrm, T):
        if self.N == 0:
            req = self.generate_request(osrm)
            self.reqs.append(req)
            self.N += 1
            self.queue.append(self.reqs[-1])
        while self.reqs[-1].Tr <= T:
            req = self.generate_request(osrm)
            self.reqs.append(req)
            self.N += 1
            self.queue.append(self.reqs[-1])
        assert self.N == len(self.reqs)

    # generate one request, following exponential arrival interval
    def generate_request(self, osrm):
        dt = 3600.0 / self.D * self.rs1.exponential()
        rand = self.rs1.rand()
        for m in self.M:
            if m[5] > rand:
                req = Req(osrm,
                          0 if self.N == 0 else self.reqs[-1].id + 1,
                          dt if self.N == 0 else self.reqs[-1].Tr + dt,
                          m[0], m[1], m[2], m[3])
                break

        print("req", req.id, " Ts:", req.Ts)
        return req

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
        str = "AMoD system at t = %.3f: %d requests in queue" % (self.T, len(self.queue))
        # for r in self.queue:
        #     str += "\n" + r.__str__()
        return str
