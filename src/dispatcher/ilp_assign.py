"""
compute an assignment plan from all possible matches
"""

from src.dispatcher.scheduling import *
import gurobipy as gp
from gurobipy import GRB


def ilp_assignment(veh_trip_pairs: list[[Veh, list[Req], list[[int, int, int, float, float]], float]],
                   considered_rids: list[int],
                   reqs: list[Req],
                   vehs: list[Veh],
                   ensure_assigning_orders_that_are_picking: bool = True) -> list[int]:
    t = timer_start()
    if DEBUG_PRINT:
        print(f"                *ILP assignment with {len(veh_trip_pairs)} pairs...", end=" ")

    selected_veh_trip_pair_indices = []
    if len(veh_trip_pairs) == 0:
        return selected_veh_trip_pair_indices
    # The order in which the vt-pairs are arranged can slightly affect the results. Reordering aims to eliminate it.
    veh_trip_pairs.sort(key=lambda e: e[0].id)

    try:
        # 1. Create a new model
        model = gp.Model("ilp")
        model.setParam("LogToConsole", 0)

        # 2. Create variables
        var_vt_pair = []  # var_vt_pair[i] = 1 indicates selecting the i_th vehicle_trip_pair.
        for i in range(len(veh_trip_pairs)):
            var_vt_pair.append(model.addVar(vtype=GRB.BINARY))
        var_order = []  # var_order[j] = 0 indicates assigning the i_th order in the list.
        for j in range(len(considered_rids)):
            var_order.append(model.addVar(vtype=GRB.BINARY))

        # 3. Set objective: maximize Σ var_vt_pair[i] * score(vt_pair).
        obj_expr = 0.0
        for i in range(len(veh_trip_pairs)):
            obj_expr += var_vt_pair[i] * veh_trip_pairs[i][4]
        model.setObjective(obj_expr, GRB.MAXIMIZE)

        # 4. Add constraints.
        #   (0) Get the pairs' indices for each vehicle and request
        vt_idx = [[] for v in range(len(vehs))]
        rt_idx = [[] for j in range(len(considered_rids))]
        for idx, [veh, trip, sche, cost, score] in enumerate(veh_trip_pairs):
            vt_idx[veh.id].append(idx)
            for req in trip:
                rt_idx[considered_rids.index(req.id)].append(idx)
        #   (1) Add constraint 1: each vehicle (v) can only be assigned at most one schedule (trip).
        #     Σ var_vt_pair[i] * Θ_vt(v) = 1, ∀ v ∈ V (Θ_vt(v) = 1 if v is in vt).
        for indices in vt_idx:
            con_this_veh = 0.0
            for i in indices:
                con_this_veh += var_vt_pair[i]
            model.addConstr(con_this_veh == 1)
        #   (2) Add constraint 2: each order/request (r) can only be assigned to at most one vehicle.
        #     Σ var_vt_pair[i] * Θ_vt(r) + var_order[j] = 1, ∀ r ∈ R. (Θ_vt(order) = 1 if r is in vt).
        for j, indices in enumerate(rt_idx):
            con_this_req = 0.0
            for i in indices:
                con_this_req += var_vt_pair[i]
            con_this_req += var_order[j]
            model.addConstr(con_this_req == 1)
        #   (3) Add constraint 3: no currently picking order is ignored.
        #     var_order[j] = 0, ∀ r ∈ R_picking
        if ensure_assigning_orders_that_are_picking:
            for j in range(len(considered_rids)):
                if reqs[considered_rids[j]].status == OrderStatus.PICKING:
                    model.addConstr(var_order[j] == 0)

        # 5. Optimize model.
        model.optimize()

        # 6. Get the result.
        for i, var_vt in enumerate(var_vt_pair):
            if var_vt.getAttr(GRB.Attr.X) == 1:
                selected_veh_trip_pair_indices.append(i)

    except gp.GurobiError as e:
        print(f"\n[GUROBI] Error code = {str(e.message)} ({str(e)}).")
    except AttributeError:
        print("Encountered an attribute error")

    if DEBUG_PRINT:
        print(f"({timer_end(t)})")

    return selected_veh_trip_pair_indices


def greedy_assignment(veh_trip_pairs: list[[Veh, list[Req], list[[int, int, int, float, float]], float]]) -> list[int]:
    t = timer_start()
    if DEBUG_PRINT:
        print(f"                *Greedy assignment with {len(veh_trip_pairs)} pairs...", end=" ")

    selected_veh_trip_pair_indices = []
    if len(veh_trip_pairs) == 0:
        return selected_veh_trip_pair_indices
    veh_trip_pairs.sort(key=lambda e: -e[4])

    selected_vids = []
    selected_rids = []

    for idx, [veh, trip, sche, cost, score] in enumerate(veh_trip_pairs):
        # Check if the vehicle has been selected.
        if veh.id in selected_vids:
            continue
        # Check if any request in the trip has been selected.
        T_id = [r.id for r in trip]
        if np.any([rid in selected_rids for rid in T_id]):
            continue
        # The current vehicle_trip_pair is selected.
        selected_vids.append(veh.id)
        selected_rids.extend(T_id)
        selected_veh_trip_pair_indices.append(idx)

    if DEBUG_PRINT:
        print(f"({timer_end(t)})")

    return selected_veh_trip_pair_indices
