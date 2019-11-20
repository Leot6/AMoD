"""
rebalancing algorithm for the AMoD system
"""

import copy
import time
import mosek
import numpy as np
from lib.S_Route import get_duration
from lib.S_Configure import IS_DEBUG
from lib.A1_AssignPlanner import ILP_assign, greedy_assign


def find_non_shared_trips(vehs, reqs_unassigned):
    # debug code
    ss = time.time()

    reqs_unassigned = sorted(reqs_unassigned, key=lambda r: r.id)
    idle_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = [(req.id, 1, req.onid, req.Clp, None), (req.id, -1, req.dnid, req.Cld, None)]
                dt = get_duration(veh.nid, req.onid)
                idle_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))

    R_id_assigned, V_id_assigned, schedule_assigned = greedy_assign(idle_veh_req)
    # R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(idle_veh_req, reqs_unassigned, set())

    assert len(R_id_assigned) == len(V_id_assigned)
    for rid, schedule in zip(R_id_assigned, schedule_assigned):
        assert rid == schedule[0][0]

    return R_id_assigned, V_id_assigned, schedule_assigned


def naive_rebalancing(vehs, reqs_unassigned):
    rebl_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = [(-1, 0, req.onid, np.inf, None)]
                dt = get_duration(veh.nid, req.onid)
                rebl_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))
    R_id_rebl, V_id_rebl, schedule_rebl = greedy_assign(rebl_veh_req)
    # R_id_rebl, V_id_rebl, schedule_rebl = ILP_assign(rebl_veh_req, reqs_unassigned, set())
    return V_id_rebl, schedule_rebl
