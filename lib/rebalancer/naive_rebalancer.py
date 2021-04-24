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
            t = time.time()
            noi = 0  # number of idle vehicles
            for veh in self.vehs:
                if veh.idle:
                    noi += 1
            print(f'        -repositioning {noi} idle vehs to {len(self.reqs_unassigned)} positions through NR...')

        reqs_unassigned = sorted(self.reqs_unassigned, key=lambda r: r.id)
        veh_rebl_pairs = []
        for req in tqdm(reqs_unassigned, desc=f'rebalancing ({len(reqs_unassigned)} reqs)', leave=False):
            for veh in self.vehs:
                if veh.idle:
                    dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
                    sche = [(-1, 0, req.onid, dt * 1.1)]
                    veh_rebl_pairs.append((veh, tuple([req]), copy.deepcopy(sche), dt))
        rids_rebl, vids_rebl, sches_rebl = greedy_assign(veh_rebl_pairs)
        assert len(rids_rebl) == len(vids_rebl)
        for rid, vid, sche in zip(rids_rebl, vids_rebl, sches_rebl):
            assert self.reqs[rid].onid == sche[0][2]
            self.vehs[vid].build_route(sche, self.reqs, T)

        if IS_DEBUG:
            print(f'            +rebalancing vehs {len(vids_rebl)}  ({round((time.time() - t), 2)}s)')

