"""
compute an assignment plan from edges in RTV
"""

import time
import mosek
import numpy as np
from lib.Configure import MODEE, CUTOFF_ILP, IS_DEBUG


def greedy_assign(veh_trip_edges):
    R_assigned = []
    T_assigned = []
    V_assigned = []
    S_assigned = []

    edges = sorted(veh_trip_edges, key=lambda e: (-len(e[1]), e[3]))
    for (veh, trip, schedule, cost) in edges:
        if trip in T_assigned:
            continue
        if veh in V_assigned:
            continue
        if np.any([r in R_assigned for r in trip]):
            continue
        R_assigned.extend(list(trip))
        T_assigned.append(trip)
        V_assigned.append(veh)
        S_assigned.append(schedule)
        # print('     *trip %s is assigned to veh %d with cost %.2f' % ([req.id for req in trip], veh_id, cost))

    return R_assigned, V_assigned, S_assigned


def ILP_assign(veh_trip_edges, reqs_pool, rid_assigned_last):

    # debug code
    ss = time.time()

    R_assigned = []
    V_assigned = []
    S_assigned = []

    # debug
    V_T_assigned = []

    # debug
    cost_a = 0

    numedges = len(veh_trip_edges)
    if numedges > 0:
        numreqs = len(reqs_pool)
        cost_ignore_normal = 10 ** (len(str(int(veh_trip_edges[0][3])))+3)
        if MODEE == 'VT_replan':
            cost_ignore_high = 100 * cost_ignore_normal
        else:
            cost_ignore_high = cost_ignore_normal

        inf = 0.0  # Since the actual value of Infinity is ignores, we define it solely for symbolic purposes

        # for matrix A of coefficients of constraints
        R_id = [req.id for req in reqs_pool]
        R_T_idx = [[numedges+i] for i in range(numreqs)]

        V_id = [veh_trip_edges[0][0].id]
        V_T_idx = [[]]
        for idx, (veh, trip, schedule, cost) in zip(range(numedges), veh_trip_edges):
            vid = veh.id
            if vid != V_id[-1]:
                V_id.append(vid)
                V_T_idx.append([])
            V_T_idx[-1].append(idx)
            for req in trip:
                R_T_idx[R_id.index(req.id)].append(idx)

        numvar = numedges + numreqs
        numvehs = len(V_id)
        numcon = numvehs + numreqs

        # Bound keys for variables
        bkx = [mosek.boundkey.ra] * numvar
        # Bound values for variables
        blx = [0.0] * numvar
        bux = [1.0] * numvar

        # Objective coefficients
        c = [round(cost) for (veh, trip, schedule, cost) in veh_trip_edges]
        for rid in R_id:
            if rid in rid_assigned_last:
                c.append(cost_ignore_high)
            else:
                c.append(cost_ignore_normal)

        # Bound keys for constraints
        bkc = [mosek.boundkey.up] * numvehs + [mosek.boundkey.fx] * numreqs
        # Bound values for constraints
        blc = [-inf] * numvehs + [1.0] * numreqs
        buc = [1.0] * numcon

        # Column indexes of non-zeros in row i.
        aidx = V_T_idx + R_T_idx
        # Non-zero Values of row i.
        aval = [[1.0] * len(row) for row in aidx]

        with mosek.Env() as env:
            with env.Task(0, 0) as task:

                # Append 'numcon' empty constraints. The constraints will initially have no bounds.
                task.appendcons(numcon)
                # Append 'numvar' variables. The variables will initially be fixed at zero (x=0).
                task.appendvars(numvar)
                # Input objective
                task.putclist(list(range(numvar)), c)

                # Put constraint bounds
                task.putconboundslice(0, numcon, bkc, blc, buc)
                # Put variable bounds
                task.putvarboundslice(0, numvar, bkx, blx, bux)

                # Input A non-zeros by rows
                for i in range(numcon):
                    task.putarow(i, aidx[i], aval[i])

                # Input the objective sense (minimize/maximize)
                task.putobjsense(mosek.objsense.minimize)
                # Define variables to be integers
                task.putvartypelist(list(range(numvar)), [mosek.variabletype.type_int] * numvar)
                # Set max solution time
                task.putdouparam(mosek.dparam.mio_max_time, CUTOFF_ILP)

                # # add init solution
                # a=[]
                # b=[]
                # init_assign_idx = [0.] * numedges + [1.0] * numreqs
                # R_id_init_assigned, V_id_init_assigned, schedule_init_assigned = greedy_assign(veh_trip_edges)
                # for i, (veh, trip, schedule, cost) in zip(range(numedges), veh_trip_edges):
                #     if veh.id in V_id_init_assigned \
                #             and schedule == schedule_init_assigned[V_id_init_assigned.index(veh.id)]:
                #         init_assign_idx[i] = 1.0
                #         a.append(veh.id)
                # for i, rid in zip(range(numreqs), R_id):
                #     if rid in R_id_init_assigned:
                #         init_assign_idx[numedges + i] = 0.
                #         b.append(rid)
                # # print('veh', len(a), len(V_id_init_assigned), len(schedule_init_assigned), ', req', len(b))
                # assert set(a) == set(V_id_init_assigned)
                # assert set(b) == set(R_id_init_assigned)
                # task.putxxslice(mosek.soltype.itg, 0, numvar, init_assign_idx)

                # Optimize the task
                task.optimize()
                # Output a solution
                assign_idx = [0.] * numvar
                task.getxx(mosek.soltype.itg, assign_idx)

        # print("Optimal solution: %s" % assign_idx)
        for yes, (veh, trip, schedule, cost) in zip(assign_idx, veh_trip_edges):
            if round(yes) == 1:
                R_assigned.extend(list(trip))
                V_assigned.append(veh)
                S_assigned.append(schedule)
                # print('     *trip %s is assigned to veh %d with cost %.2f' % ([req.id for req in trip], veh.id, cost))

                # debug
                cost_a += round(cost)
                V_T_assigned.append((veh.id, {req.id for req in trip}))
                # debug

        # debug code starts
        R_id_assigned = [req.id for req in R_assigned]
        assert len(R_id_assigned) == len(set(R_id_assigned))

        if MODEE == 'VT_replan':
            rid_assigned_last_not_assigned_this_time = \
                rid_assigned_last - set(R_id_assigned) - (rid_assigned_last-set(R_id))
            # print('rid_assigned_last_not_assigned_this_time', rid_assigned_last_not_assigned_this_time)
            if len(rid_assigned_last_not_assigned_this_time) != 0:
                print('rid_assigned_last_not_assigned_this_time', rid_assigned_last_not_assigned_this_time)
                print('cost_a', cost_a)
            assert len(rid_assigned_last_not_assigned_this_time) == 0

    return R_assigned, V_assigned, S_assigned

