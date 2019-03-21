"""
compute a assignment plan from edges in RTV
"""

import mosek
import numpy as np


def greedy_assign(model, veh_trip_edges, T):
    print('    -start greedy assign with %d edges:' % len(veh_trip_edges))
    R_id_assigned = []
    T_id_assigned = []
    V_id_assigned = []
    schedule_assigned = []

    # # debug code starts
    # for (veh, trip, schedule, cost) in veh_trip_edges:
    #     print('veh %d, trip %s, cost %.02f' % (veh.id, [r.id for r in trip], cost))
    # # debug code ends

    edges = sorted(veh_trip_edges, key=lambda e: (-len(e[1]), e[3]))
    for (veh, trip, schedule, cost) in edges:
        veh_id = veh.id
        trip_id = tuple([r.id for r in trip])
        if trip_id in T_id_assigned:
            continue
        if veh_id in V_id_assigned:
            continue
        if np.any([r_id in R_id_assigned for r_id in trip_id]):
            continue
        for rid in trip_id:
            R_id_assigned.append(rid)
        T_id_assigned.append(trip_id)
        V_id_assigned.append(veh_id)
        schedule_assigned.append(schedule)
        print('     *trip %s is assigned to veh %d' % ([req.id for req in trip], veh_id))

    # return R_id_assigned, V_id_assigned, schedule_assigned
    R_assigned = set()
    for req_id in R_id_assigned:
        R_assigned.add(model.reqs[req_id])
    model.reqs_picking.update(R_assigned)
    R_unassigned = set(model.queue) - R_assigned
    model.reqs_unassigned.update(R_unassigned)
    model.queue.clear()
    for veh_id, schedule in zip(V_id_assigned, schedule_assigned):
        model.vehs[veh_id].build_route(schedule, model.reqs, T)


def ILP_assign(model, veh_trip_edges, reqs_pool, T):
    print('    -start ILP assign with %d edges:' % len(veh_trip_edges))
    R_id_assigned = []
    V_id_assigned = []
    schedule_assigned = []

    # # debug code starts
    # for (veh, trip, schedule, cost) in veh_trip_edges:
    #     print('veh %d, trip %s, cost %.02f' % (veh.id, [r.id for r in trip], cost))
    # # debug code ends

    numedges = len(veh_trip_edges)
    if numedges > 0:
        numreqs = len(reqs_pool)
        cost_ignore = 1000000
        inf = 0.0  # Since the actual value of Infinity is ignores, we define it solely for symbolic purposes

        # for matrix A of coefficients of constraints
        V_id = []
        V_T_idx = []
        R_id = []
        R_T_idx = []
        V_id.append(veh_trip_edges[0][0].id)
        V_T_idx.append([])
        for req in reqs_pool:
            R_id.append(req.id)
            R_T_idx.append([])
        idx = -1
        for (veh, trip, schedule, cost) in veh_trip_edges:
            idx += 1
            veh_id = veh.id
            if veh_id != V_id[-1]:
                V_id.append(veh_id)
                V_T_idx.append([])
            V_T_idx[-1].append(idx)
            for req in trip:
                R_T_idx[R_id.index(req.id)].append(idx)
        for i in range(numreqs):
            R_T_idx[i].append(numedges+i)
        numvehs = len(V_id)
        numvar = numedges + numreqs
        numcon = numvehs + numreqs
        assign_idx = [0.] * numvar

        with mosek.Env() as env:
            with env.Task(0, 0) as task:

                # Objective coefficients
                c = []
                for (veh, trip, schedule, cost) in veh_trip_edges:
                    c.append(cost)
                c.extend([cost_ignore] * numreqs)

                # Bound keys for variables
                bkx = [mosek.boundkey.ra] * numvar
                # Bound values for variables
                blx = [0.0] * numvar
                bux = [1.0] * numvar
                # Append 'numvar' variables. The variables will initially be fixed at zero (x=0).
                task.appendvars(numvar)
                for j in range(numvar):
                    # Set the linear term c_j in the objective.
                    task.putcj(j, c[j])
                    # Set the bounds on variable j, blx[j] <= x_j <= bux[j]
                    task.putbound(mosek.accmode.var, j, bkx[j], blx[j], bux[j])

                # input the A matrix column-wise
                # asub contains row indexes
                asub = V_T_idx + R_T_idx
                # acof contains coefficients
                aval = [[1.0 for i in range(len(j))] for j in asub]
                # Bound keys for constraints
                bkc = [mosek.boundkey.up] * numvehs + [mosek.boundkey.fx] * numreqs
                # Bound values for constraints
                blc = [-inf] * numvehs + [1.0] * numreqs
                buc = [1.0] * numcon
                # Append 'numcon' empty constraints.
                # The constraints will initially have no bounds.
                task.appendcons(numcon)
                for i in range(numcon):
                    task.putbound(mosek.accmode.con, i, bkc[i], blc[i], buc[i])
                    # Input row i of A
                    task.putarow(i,                     # Row index.
                                 # Column indexes of non-zeros in row i.
                                 asub[i],
                                 aval[i])              # Non-zero Values of row i.

                # Input the objective sense (minimize/maximize)
                task.putobjsense(mosek.objsense.minimize)
                # Define variables to be integers
                task.putvartypelist(list(range(numvar)),
                                    [mosek.variabletype.type_int] * numvar)
                # Set max solution time
                task.putdouparam(mosek.dparam.mio_max_time, 20.0)
                # Optimize the task
                task.optimize()
                # Output a solution
                task.getxx(mosek.soltype.itg, assign_idx)
        # print("Optimal solution: %s" % assign_idx)
        for yes, (veh, trip, schedule, cost) in zip(assign_idx, veh_trip_edges):
            if yes == 1.0:
                for req in trip:
                    R_id_assigned.append(req.id)
                V_id_assigned.append(veh.id)
                schedule_assigned.append(schedule)
                print('     *trip %s is assigned to veh %d' % ([req.id for req in trip], veh.id))
    # return R_id_assigned, V_id_assigned, schedule_assigned
    R_assigned = set()
    for req_id in R_id_assigned:
        R_assigned.add(model.reqs[req_id])
    model.reqs_picking.update(R_assigned)
    R_unassigned = set(model.queue) - R_assigned
    model.reqs_unassigned.update(R_unassigned)
    model.queue.clear()
    for veh_id, schedule in zip(V_id_assigned, schedule_assigned):
        model.vehs[veh_id].build_route(schedule, model.reqs, T)
