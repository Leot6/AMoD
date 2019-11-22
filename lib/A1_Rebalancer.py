"""
rebalancing algorithm for the AMoD system
"""

import copy
import time
import mosek
import numpy as np

from lib.Configure import IS_DEBUG
from lib.A1_AssignPlanner import ILP_assign, greedy_assign
from lib.S_Route import get_duration


def find_unshared_trips(vehs, reqs_unassigned):
    # debug code
    ss = time.time()

    vehs = sorted(vehs, key=lambda v: v.id)
    reqs_unassigned = sorted(reqs_unassigned, key=lambda r: r.id)
    idle_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = [(req.id, 1, req.onid, req.Clp, None), (req.id, -1, req.dnid, req.Cld, None)]
                dt = get_duration(veh.nid, req.onid)
                idle_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))

    R_assigned, V_assigned, S_assigned = greedy_assign(idle_veh_req)
    # R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(idle_veh_req, reqs_unassigned, set())

    for req, veh, schedule in zip(R_assigned, V_assigned, S_assigned):
        veh.VTtable[0] = [(tuple([req]), schedule, 0, [schedule])]

    assert len(R_assigned) == len(V_assigned) == len(S_assigned)
    for req, schedule in zip(R_assigned, S_assigned):
        assert req.id == schedule[0][0]

    return R_assigned, V_assigned, S_assigned


# not used
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
