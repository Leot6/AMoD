from test import *
from datetime import datetime, timedelta


def use_real_time():
    t1 = datetime(2018, 1, 1)
    print("t1:", t1)
    t2 = timedelta(seconds=30) + t1
    print("t2:", t2)
    print("time: %d s." % (t2 - t1).total_seconds())


if __name__ == "__main__":
    use_real_time()


class Graph(object):
    """
        Graph is a class for nodes and edges in a network
        Attributes:
        vehs: the list of vehicles
        reqs: the list of requests in queue
        trips: the list of possible feasible trips
        edge_rr: e(r1, r2)
        edge_rv: e(r, v)
        edge_rT: e(r, T)
        edge_vT: e(v, T)
        """
    
    def __init__(self, name="", vehs=[], reqs=[], trips=[]):
        self.name = name
        self.vehs = vehs
        self.reqs = reqs
        self.trips = trips
        self.edge_rr = []
        self.edge_rv = []
        self.edge_rT = []
        self.edge_Tv = []


class Edge(object):
    """
        RVgraph is a class for steps in a leg
        Attributes:
        w: cost of the trip
        """
    
    def __init__(self, node1=None, node2=None, weight=0):
        self.node1 = node1
        self.node2 = node2
        self.w = weight
    
    def add2(a):
        a.id = a.id + 2




