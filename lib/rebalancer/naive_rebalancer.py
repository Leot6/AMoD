"""
rebalancing algorithm for the AMoD system
"""

import copy
import time
import numpy as np
from tqdm import tqdm
from lib.simulator.config import IS_DEBUG
from lib.dispatcher.osp.osp_assign import greedy_assign
from lib.routing.routing_server import get_duration_from_origin_to_dest


class NR(object):
    """
    NR is a naive rebalancing algorithm that assign idle vehicles to unassigned requests
    """

    def __init__(self, amod):
        self.vehs = amod.vehs
        self.reqs = amod.reqs
        self.reqs_picking = amod.reqs_picking
        self.reqs_unassigned = amod.reqs_unassigned

    def rebelancing(self, T):
        if IS_DEBUG:
            print('    -T = %d, start rebalancing...' % T)
            a4 = time.time()

        reqs_unassigned = sorted(self.reqs_unassigned, key=lambda r: r.id)
        veh_req_pairs = []
        for req in tqdm(reqs_unassigned, desc=f'rebalancing ({len(reqs_unassigned)} reqs)', leave=False):
            for veh in self.vehs:
                if veh.idle:
                    sche = [(req.id, 1, req.onid, req.Tr, req.Clp), (req.id, -1, req.dnid, req.Tr + req.Ts, req.Cld)]
                    dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
                    veh_req_pairs.append((veh, tuple([req]), copy.deepcopy(sche), dt))
        rids_rebl, vids_rebl, sches_rebl = greedy_assign(veh_req_pairs)
        assert len(rids_rebl) == len(vids_rebl)
        for rid, vid, sche in zip(rids_rebl, vids_rebl, sches_rebl):
            assert rid == sche[0][0]
            self.vehs[vid].build_route(sche, self.reqs, T)
            self.reqs_picking.add(self.reqs[rid])
            self.reqs_unassigned.remove(self.reqs[rid])
        if IS_DEBUG:
            print('        a4 running time:', round((time.time() - a4), 2))




