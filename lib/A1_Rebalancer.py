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


# not used
def naive_rebalancing(vehs, reqs_unassigned):
    rebl_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = [(-1, 0, req.onid, np.inf)]
                dt = get_duration(veh.nid, req.onid)
                rebl_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))
    R_id_rebl, V_id_rebl, schedule_rebl = greedy_assign(rebl_veh_req)
    # R_id_rebl, V_id_rebl, schedule_rebl = ILP_assign(rebl_veh_req, reqs_unassigned, set())
    return V_id_rebl, schedule_rebl


# execute the assignment from Rebalancer and build route for rebalancing vehicles (not used)
def exec_rebalancing(V_assigned, S_assigned, reqs, T):
    for veh, schedule in zip(V_assigned, S_assigned):
        assert veh.idle
        assert veh.t_to_nid == 0
        veh.build_route(schedule, reqs, T)
        assert schedule[0][0] == -1



