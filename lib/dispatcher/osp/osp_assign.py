"""
compute an assignment plan from all possible matches
"""

import time
import mosek
import numpy as np

CUTOFF_ILP = 20
ignore_a_bug_temporary = True


def ILP_assign(veh_trip_edges, reqs_pool, reqs_picking=[]):
    aa = time.time()
    veh_trip_edges = sorted(veh_trip_edges, key=lambda e: (e[0].id, -len(e[1]), e[3]))
    rids_picking = [r.id for r in reqs_picking]
    assert len(reqs_pool) == len(set(reqs_pool))
    rids_assigned = []
    vids_assigned = []
    sches_assigned = []
    assign_cost = 0

    numedges = len(veh_trip_edges)
    if numedges > 0:
        numreqs = len(reqs_pool)
        cost_ignore_normal = 10 ** (len(str(int(veh_trip_edges[0][3])))+3)
        if rids_picking:
            cost_ignore_high = 100 * cost_ignore_normal
        else:
            cost_ignore_high = cost_ignore_normal

        inf = 0.0  # Since the actual value of Infinity is ignores, we define it solely for symbolic purposes

        # for matrix A of coefficients of constraints
        rids_pool = [req.id for req in reqs_pool]
        R_T_idx = [[numedges+i] for i in range(numreqs)]

        vids_pool = [veh_trip_edges[0][0].id]
        V_T_idx = [[]]
        for idx, (veh, trip, sche, cost) in zip(range(numedges), veh_trip_edges):
            vid = veh.id
            if vid != vids_pool[-1]:
                vids_pool.append(vid)
                V_T_idx.append([])
            V_T_idx[-1].append(idx)
            for req in trip:
                R_T_idx[rids_pool.index(req.id)].append(idx)

        numvar = numedges + numreqs
        numvehs = len(vids_pool)
        numcon = numvehs + numreqs

        # Bound keys for variables
        bkx = [mosek.boundkey.ra] * numvar
        # Bound values for variables
        blx = [0.0] * numvar
        bux = [1.0] * numvar

        # Objective coefficients
        c = [round(cost) for (veh, trip, sche, cost) in veh_trip_edges]
        for rid in rids_pool:
            if rid in rids_picking:
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
                # Allow multiple threads if more threads is available (seems not working)
                task.putintparam(mosek.iparam.intpnt_multi_thread, mosek.onoffkey.on)

                # # add init solution
                # a=[]
                # b=[]
                # init_assign_idx = [0.] * numedges + [1.0] * numreqs
                # rids_init_assigned, vids_init_assigned, sche_init_assigned = greedy_assign(veh_trip_edges)
                # for i, (veh, trip, sche, cost) in zip(range(numedges), veh_trip_edges):
                #     if veh.id in vids_init_assigned \
                #             and sche == sche_init_assigned[vids_init_assigned.index(veh.id)]:
                #         init_assign_idx[i] = 1.0
                #         a.append(veh.id)
                # for i, rid in zip(range(numreqs), rids):
                #     if rid in rids_init_assigned:
                #         init_assign_idx[numedges + i] = 0.
                #         b.append(rid)
                # # print('veh', len(a), len(vids_init_assigned), len(sche_init_assigned), ', req', len(b))
                # assert set(a) == set(vids_init_assigned)
                # assert set(b) == set(rids_init_assigned)
                # task.putxxslice(mosek.soltype.itg, 0, numvar, init_assign_idx)

                # Optimize the task
                task.optimize()
                # Output a solution
                assign_idx = [0.] * numvar
                task.getxx(mosek.soltype.itg, assign_idx)

        # print("Optimal solution: %s" % assign_idx)
        for yes, (veh, trip, sche, cost) in zip(assign_idx, veh_trip_edges):
            if round(yes) == 1:
                rids_assigned.extend([req.id for req in trip])
                vids_assigned.append(veh.id)
                sches_assigned.append(sche)
                assign_cost += cost
                # print('     *trip %s is assigned to veh %d with cost %.2f' % ([req.id for req in trip], veh.id, cost))

        assert len(rids_assigned) == len(set(rids_assigned))
        if rids_picking:
            # if not set(rids_picking) <= set(rids_assigned):
                # rids_removed_ILP = list(set(rids_picking) - set(rids_assigned))
                # print('rids_picking not assigned this time', rids_removed_ILP)
                # print('        ILP running time:', round((time.time() - aa), 2))
            if not ignore_a_bug_temporary:
                assert set(rids_picking) <= set(rids_assigned)

    return rids_assigned, vids_assigned, sches_assigned


def greedy_assign(veh_trip_edges):
    rids_assigned = []
    T_id_assigned = []
    vids_assigned = []
    sches_assigned = []

    edges = sorted(veh_trip_edges, key=lambda e: (-len(e[1]), e[3]))
    for (veh, trip, sche, cost) in edges:
        vid = veh.id
        T_id = tuple([r.id for r in trip])
        if T_id in T_id_assigned:
            continue
        if vid in vids_assigned:
            continue
        if np.any([rid in rids_assigned for rid in T_id]):
            continue
        rids_assigned.extend([rid for rid in T_id])
        T_id_assigned.append(T_id)
        vids_assigned.append(vid)
        sches_assigned.append(sche)
        # print('     *trip %s is assigned to veh %d with cost %.2f' % ([req.id for req in trip], veh_id, cost))
        assert len(rids_assigned) == len(set(rids_assigned))

    return rids_assigned, vids_assigned, sches_assigned


#
# def greedy_assign(veh_trip_edges):
#     R_id_assigned = []
#     T_id_assigned = []
#     V_id_assigned = []
#     S_assigned = []
#
#     edges = sorted(veh_trip_edges, key=lambda e: (-len(e[1]), e[3]))
#     for (veh, trip, sche, cost) in edges:
#         veh_id = veh.id
#         trip_id = tuple([r.id for r in trip])
#         if trip_id in T_id_assigned:
#             continue
#         if veh_id in V_id_assigned:
#             continue
#         if np.any([r_id in R_id_assigned for r_id in trip_id]):
#             continue
#         R_id_assigned.extend([rid for rid in trip_id])
#         T_id_assigned.append(trip_id)
#         V_id_assigned.append(veh_id)
#         S_assigned.append(sche)
#         # print('     *trip %s is assigned to veh %d with cost %.2f' % ([req.id for req in trip], veh_id, cost))
#
#     return R_id_assigned, V_id_assigned, S_assigned
