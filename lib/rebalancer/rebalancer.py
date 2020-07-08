"""
rebalancing algorithm for the AMoD system
"""

import copy
import numpy as np

from lib.dispatcher.osp.linear_assignment import ILP_assign
from lib.routing.routing_server import get_duration_from_origin_to_dest


# not used
def naive_rebalancing(vehs, reqs_unassigned):
    rebl_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = [(-1, 0, req.onid, np.inf)]
                dt = get_duration_from_origin_to_dest(veh.nid, req.onid)
                rebl_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))
    # R_id_rebl, V_id_rebl, schedule_rebl = greedy_assign(rebl_veh_req)
    R_id_rebl, V_id_rebl, schedule_rebl = ILP_assign(rebl_veh_req, reqs_unassigned, set())
    return V_id_rebl, schedule_rebl


# execute the assignment from Rebalancer and build route for rebalancing vehicles (not used)
def exec_rebalancing(V_assigned, S_assigned, reqs, T):
    for veh, schedule in zip(V_assigned, S_assigned):
        assert veh.idle
        assert veh.t_to_nid == 0
        veh.build_route(schedule, reqs, T)
        assert schedule[0][0] == -1



