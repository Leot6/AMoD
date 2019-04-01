"""
rebalancing algorithm for the AMoD system
"""

import copy
import numpy as np
from lib.Route import get_duration


def rebalance(model, T):
    # debug code starts
    noi = 0  # number of idle vehicles
    for veh in model.vehs:
        if veh.idle:
            noi += 1
    print('        idle vehs:', noi)
    # debug code ends

    for veh in model.vehs:
        if veh.idle:
            schedule = []
            min_dt = np.inf
            req_re = None
            for req in model.reqs_unassigned:
                dt = get_duration(veh.lng, veh.lat, req.olng, req.olat, veh.nid, req.onid)
                if dt is None:  # no available route is found
                    continue
                if dt < min_dt:
                    min_dt = dt
                    req_re = req
            if min_dt != np.inf:
                schedule.insert(0, (req_re.id, 1, req_re.olng, req_re.olat, req_re.onid, req_re.Clp))
                schedule.insert(1, (req_re.id, -1, req_re.dlng, req_re.dlat, req_re.dnid, req_re.Cld))
                veh.build_route(copy.deepcopy(schedule), model.reqs, T)
                model.reqs_picking.add(req_re)
                model.reqs_unassigned.remove(req_re)
                # print('     *trip %s is assigned to veh %d (rebalancing, wait time %.02f)'
                #       % ([req_re.id], veh.id, min_dt))
            if len(model.reqs_unassigned) == 0:
                break
    if len(model.reqs_unassigned) != 0:
        model.rejs.extend(list(model.reqs_unassigned))
        model.reqs_unassigned.clear()
