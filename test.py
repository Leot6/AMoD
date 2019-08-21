import time
import math
import requests
import pickle
import mosek
import re
import copy
import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from heapq import heappush, heappop
from itertools import count, islice
from tqdm import tqdm
from collections import deque
from scipy.stats import lognorm

CUTOFF_ILP = 10


def ILP_assign(veh_trip_edges, reqs_pool, rid_assigned_last):
    # debug code
    assert len(reqs_pool) == len(set(reqs_pool))
    R_id_assigned = []
    V_id_assigned = []
    schedule_assigned = []

    # debug
    V_T_assigned = []

    # debug
    cost_a = 0

    numedges = len(veh_trip_edges)
    if numedges > 0:
        numreqs = len(reqs_pool)
        cost_ignore_normal = 10 ** (len(str(int(veh_trip_edges[0][3])))+3)
        cost_ignore_high = 100 * cost_ignore_normal

        inf = 0.0  # Since the actual value of Infinity is ignores, we define it solely for symbolic purposes

        # for matrix A of coefficients of constraints
        R_id = [req.id for req in reqs_pool]
        R_T_idx = [[numedges+i] for i in range(numreqs)]

        V_id = [veh_trip_edges[0][0].id]
        V_T_idx = [[]]
        idx = -1
        for (veh, trip, schedule, cost) in veh_trip_edges:
            idx += 1
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

                # Optimize the task
                task.optimize()
                # Output a solution
                assign_idx = [0.] * numvar
                task.getxx(mosek.soltype.itg, assign_idx)

        # print("Optimal solution: %s" % assign_idx)
        for yes, (veh, trip, schedule, cost) in zip(assign_idx, veh_trip_edges):
            if round(yes) == 1:
                R_id_assigned.extend([req.id for req in trip])
                V_id_assigned.append(veh.id)
                schedule_assigned.append(schedule)
                # print('     *trip %s is assigned to veh %d with cost %.2f' % ([req.id for req in trip], veh.id, cost))

                # debug
                cost_a += round(cost)
                V_T_assigned.append((veh.id, {req.id for req in trip}))

        # debug code starts
        assert len(R_id_assigned) == len(set(R_id_assigned))

        rid_assigned_last_not_assigned_this_time = \
            rid_assigned_last - set(R_id_assigned) - (rid_assigned_last - set(R_id))
        assert len(rid_assigned_last_not_assigned_this_time) == 0
    return R_id_assigned, V_id_assigned, schedule_assigned


def test(a, b, c):
    if a > b:
        c.append(2)


if __name__ == "__main__":
    # print(' -reading file...')
    # aa = time.time()
    # with open('vehs.pickle', 'rb') as f:
    #     vehs = pickle.load(f)
    # with open('veh_trip_edges.pickle', 'rb') as f:
    #     veh_trip_edges = pickle.load(f)
    # with open('reqs_pool.pickle', 'rb') as f:
    #     reqs_pool = pickle.load(f)
    # with open('rid_assigned_last.pickle', 'rb') as f:
    #     rid_assigned_last = pickle.load(f)
    # print('    reading file running time:', round((time.time() - aa), 2))
    #
    # print(' -start ILP assign with %d edges...' % len(veh_trip_edges))
    # bb = time.time()
    # R_id_assigned, V_id_assigned, schedule_assigned = ILP_assign(veh_trip_edges, reqs_pool, rid_assigned_last)
    # print('    ILP running time:', round((time.time() - bb), 2))

    # print(' -start CBS assign with %d edges...' % len(veh_trip_edges))
    # cc = time.time()
    # assign_group = []
    # VTtables = [[] for i in range(len(vehs))]
    # for idx, veh in zip(range(len(vehs)), vehs):
    #     for VTtable_k in veh.VTtable:
    #         for (trip, best_schedule, cost, all_schedules) in VTtable_k:
    #             VTtables[idx].append((veh, trip, best_schedule, cost))
    # for VTtable in VTtables:
    #     VTtable.sort(key=lambda e: (-len(e[1]), e[3]))
    #     if len(VTtable) != 0:
    #         veh = VTtable[0][0]
    #         trip = VTtable[0][1]
    #         assign_group.append((veh.id, [req.id for req in trip]))
    # for assign in assign_group:
    #     assert len([req.id for req in trip]) != 0
    #
    # print('    CBS running time:', round((time.time() - cc), 2))
    # print('assign_group', len(assign_group))
    #
    # print('len(rid_assigned_last', len(rid_assigned_last))

    a = 1
    b = 2
    c = []
    test(a, b, c)
    print(c)
















