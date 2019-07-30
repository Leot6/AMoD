"""
rebalancing algorithm for the AMoD system
"""

import copy
import time
import mosek
import numpy as np
from lib.Route import get_duration
from lib.AssignPlanner import ILP_assign, greedy_assign
from lib.Configure import IS_DEBUG


def naive_rebalance(vehs, reqs_unassigned):
    # debug code
    ss = time.time()

    # # debug code starts
    # if IS_DEBUG:
    #     noi = 0  # number of idle vehicles
    #     for veh in vehs:
    #         if veh.idle:
    #             noi += 1
    #     print('        idle vehs:', noi)
    # # debug code ends

    # reqs_unassigned = sorted(reqs_unassigned, key=lambda r: r.id)
    rebl_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = []
                dt = get_duration(veh.nid, req.onid)
                schedule.append((req.id, 1, req.onid, req.Clp, None))
                schedule.append((req.id, -1, req.dnid, req.Cld, None))
                rebl_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))
    R_id_rebl, V_id_rebl, schedule_rebl = greedy_assign(rebl_veh_req)
    assert len(R_id_rebl) == len(V_id_rebl)
    for rid, schedule in zip(R_id_rebl, schedule_rebl):
        assert rid == schedule[0][0]
    # print(R_id_rebl1)
    # print(V_id_rebl1)
    # print([(sch[0][0], sch[0][1], sch[1][0], sch[1][1]) for sch in schedule_rebl1])

    # if IS_DEBUG:
    #     print('        Rebalancing running time:', (time.time() - ss))
    return R_id_rebl, V_id_rebl, schedule_rebl
