"""
rebalancing algorithm for the AMoD system
"""

import copy
import time
import mosek
import numpy as np
from tqdm import tqdm
from lib.Route import get_duration
from lib.AssignPlanner import ILP_assign, greedy_assign
from lib.Configure import IS_DEBUG


def naive_rebalance(vehs, reqs_unassigned):
    # debug code
    ss = time.time()

    # debug code starts
    if IS_DEBUG:
        noi = 0  # number of idle vehicles
        for veh in vehs:
            if veh.idle:
                noi += 1
        print('        idle vehs:', noi)
    # debug code ends

    # reqs_unassigned = sorted(reqs_unassigned, key=lambda r: r.id)
    rebl_veh_req = []
    for veh in vehs:
        if veh.idle:
            for req in reqs_unassigned:
                schedule = []
                dt = get_duration(veh.lng, veh.lat, req.olng, req.olat, veh.nid, req.onid)
                schedule.append((req.id, 1, req.olng, req.olat, req.onid, req.Clp))
                schedule.append((req.id, -1, req.dlng, req.dlat, req.dnid, req.Cld))
                rebl_veh_req.append((veh, tuple([req]), copy.deepcopy(schedule), dt))
    R_id_rebl, V_id_rebl, schedule_rebl = greedy_assign(rebl_veh_req)
    assert len(R_id_rebl) == len(V_id_rebl)
    for rid, schedule in zip(R_id_rebl, schedule_rebl):
        assert rid == schedule[0][0]
    # print(R_id_rebl1)
    # print(V_id_rebl1)
    # print([(sch[0][0], sch[0][1], sch[1][0], sch[1][1]) for sch in schedule_rebl1])

    if IS_DEBUG:
        print('        Rebalancing running time:', (time.time() - ss))
    return R_id_rebl, V_id_rebl, schedule_rebl

    # for veh in model.vehs:
    #     if veh.idle:
    #         schedule = []
    #         min_dt = np.inf
    #         req_re = None
    #         for req in model.reqs_unassigned:
    #             dt = get_duration(veh.lng, veh.lat, req.olng, req.olat, veh.nid, req.onid)
    #             if dt is None:  # no available route is found
    #                 continue
    #             if dt < min_dt:
    #                 min_dt = dt
    #                 req_re = req
    #         if min_dt != np.inf:
    #             schedule.insert(0, (req_re.id, 1, req_re.olng, req_re.olat, req_re.onid, req_re.Clp))
    #             schedule.insert(1, (req_re.id, -1, req_re.dlng, req_re.dlat, req_re.dnid, req_re.Cld))
    #             veh.build_route(copy.deepcopy(schedule), model.reqs, T)
    #             model.reqs_picking.add(req_re)
    #             model.reqs_unassigned.remove(req_re)
    #             # print('     *trip %s is assigned to veh %d (rebalancing, wait time %.02f)'
    #             #       % ([req_re.id], veh.id, min_dt))
    #         if len(model.reqs_unassigned) == 0:
    #             break
    # if len(model.reqs_unassigned) != 0:
    #     reqs_rejected = set()
    #     for req in model.reqs_unassigned:
    #         if req.Clp >= T:
    #             model.rejs.append(req)
    #             reqs_rejected.add(req)
    #     model.reqs_unassigned.difference_update(reqs_rejected)
