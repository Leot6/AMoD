import mosek
import time


def ILP_assign(veh_trip_edges, reqs_pool):
    numedges = len(veh_trip_edges)
    if numedges > 0:
        numreqs = len(reqs_pool)
        cost_ignore = 100
        inf = 0.0  # Since the actual value of Infinity is ignores, we define it solely for symbolic purposes

        # for matrix A of coefficients of constraints
        V_id = []
        V_T_idx = []
        R_id = []
        R_T_idx = []
        V_id.append(veh_trip_edges[0][0])  # need modification (veh_trip_edges[0][0].id)
        V_T_idx.append([])
        for req in reqs_pool:
            R_id.append(req)  # need modification  (req.id)
            R_T_idx.append([])
        idx = -1
        for (veh, trip, schedule, cost) in veh_trip_edges:
            idx += 1
            veh_id = veh  # need modification  (veh.id)
            trip_id = trip  # need modification  (trip_id = tuple([r.id for r in trip]))
            if veh_id != V_id[-1]:
                V_id.append(veh_id)
                V_T_idx.append([])
            V_T_idx[-1].append(idx)
            for req_id in trip_id:
                R_T_idx[R_id.index(req_id)].append(idx)
        for i in range(numreqs):
            R_T_idx[i].append(numedges+i)
        numvehs = len(V_id)

        with mosek.Env() as env:
            with env.Task(0, 0) as task:

                # Objective coefficients
                c = []
                for (veh, trip, schedule, cost) in veh_trip_edges:
                    c.append(cost)
                c.extend([cost_ignore] * numreqs)

                numvar = numedges + numreqs
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
                numcon = numvehs + numreqs
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
                task.putdouparam(mosek.dparam.mio_max_time, 60.0)

                # Optimize the task
                task.optimize()

                prosta = task.getprosta(mosek.soltype.itg)
                solsta = task.getsolsta(mosek.soltype.itg)

                # Output a solution
                xx = [0.] * numvar
                task.getxx(mosek.soltype.itg, xx)

                if solsta in [mosek.solsta.integer_optimal, mosek.solsta.near_integer_optimal]:
                    print("Optimal solution: %s" % xx)
                    # for i in range(numvar):
                    #     print("x[" + str(i) + "]=" + str(xx[i]))
                elif solsta == mosek.solsta.dual_infeas_cer:
                    print("Primal or dual infeasibility.\n")
                elif solsta == mosek.solsta.prim_infeas_cer:
                    print("Primal or dual infeasibility.\n")
                elif solsta == mosek.solsta.near_dual_infeas_cer:
                    print("Primal or dual infeasibility.\n")
                elif solsta == mosek.solsta.near_prim_infeas_cer:
                    print("Primal or dual infeasibility.\n")
                elif mosek.solsta.unknown:
                    if prosta == mosek.prosta.prim_infeas_or_unbounded:
                        print("Problem status Infeasible or unbounded.\n")
                    elif prosta == mosek.prosta.prim_infeas:
                        print("Problem status Infeasible.\n")
                    elif prosta == mosek.prosta.unkown:
                        print("Problem status unkown.\n")
                    else:
                        print("Other problem status.\n")
                else:
                    print("Other solution status")




if __name__ == "__main__":
    # (veh, trip, schedule, cost) in edges
    edges = []
    edge0 = [0, tuple([2]), ['s0'], 16]
    edge1 = [0, tuple([3]), ['s1'], 15]
    edge2 = [0, tuple([2, 3]), ['s2'], 36]
    edge3 = [1, tuple([2]), ['s3'], 49]
    edge4 = [1, tuple([3]), ['s4'], 47]
    edges.append(edge0)
    edges.append(edge1)
    edges.append(edge2)
    edges.append(edge3)
    edges.append(edge4)

    reqs_pool = [2, 3, 4]

    # call the main function
    try:
        ILP_assign(edges, reqs_pool)
    except mosek.Error as e:
        print("ERROR: %s" % str(e.errno))
        if e.msg is not None:
            print("\t%s" % e.msg)
            sys.exit(1)
    except:
        import traceback
        traceback.print_exc()
        sys.exit(1)
