"""
main structure for the AMoD simulator
"""

from src.simulator.request import Req
from src.simulator.vehicle import Veh
from src.simulator.router_func import *

from src.dispatcher.dispatch_sba import assign_orders_through_sba
from src.dispatcher.dispatch_osp import assign_orders_through_osp
from src.rebalancer.rebalancing_npo import reposition_idle_vehicles_to_nearest_pending_orders


class Platform(object):
    """
    Model is the initial class for the AMoD system
    Attributes:
        T: system time at current state
        vehs: the list of vehicles
        reqs: the list of all received requests
        reqs_data: the list of collected real taxi requests data
        req_init_idx: init index to read reqs_data
        dispatcher: the algorithm used to do the dispatching
        rebalancer: the algorithm used to do the rebalancing

    """

    def __init__(self, simulation_start_time_stamp):
        # Initialize the simulation times.
        self.T = 0
        self.main_sim_start_time_sec = self.T + WARMUP_DURATION_MIN * 60
        self.main_sim_end_time_sec = self.main_sim_start_time_sec + SIMULATION_DURATION_MIN * 60
        self.system_shutdown_time_sec = self.main_sim_end_time_sec + WINDDOWN_DURATION_MIN * 60

        # Initialize the fleet.
        self.vehs = []
        num_of_stations = get_num_of_vehicle_stations()
        for i in range(FLEET_SIZE):
            station_idx = int(i * num_of_stations / FLEET_SIZE)
            nid = get_vehicle_station_id(station_idx)
            [lng, lat] = get_node_geo(nid)
            self.vehs.append(Veh(i, nid, lng, lat, VEH_CAPACITY, self.T))

        # Initialize the demand generator.
        self.reqs = []
        t = timer_start()
        with open(PATH_TO_TAXI_DATA, "rb") as f:
            self.reqs_data = pickle.load(f)
        self.req_init_time_sec = compute_the_accumulated_seconds_from_0_clock(SIMULATION_START_TIME)
        self.req_init_idx = 0
        while self.reqs_data[self.req_init_idx].request_time_sec < self.req_init_time_sec:
            self.req_init_idx += 1
        print(f"[INFO] Demand Generator is ready. ({timer_end(t)})")

        # Initialize the dispatcher and the rebalancer.
        if DISPATCHER == "SBA":
            self.dispatcher = DispatcherMethod.SBA
        elif DISPATCHER == "OSP":
            self.dispatcher = DispatcherMethod.OSP
        else:
            assert (False and "[DEBUG] WRONG DISPATCHER SETTING! Please check the name of dispatcher in config!")
        if REBALANCER == "NONE":
            self.rebalancer = RebalancerMethod.NONE
        elif REBALANCER == "NPO":
            self.rebalancer = RebalancerMethod.NPO
        else:
            assert (False and "[DEBUG] WRONG REBALANCER SETTING! Please check the name of rebalancer in config!")
        print("[INFO] Platform is ready.")

        # System report about running time.
        self.time_of_init = get_runtime_sec_from_t_to_now(simulation_start_time_stamp)
        self.start_time_stamp = get_time_stamp_datetime()
        self.end_time_stamp = None
        self.main_sim_start_time_stamp = get_time_stamp_datetime()
        self.main_sim_end_time_stamp = get_time_stamp_datetime()

    def run_simulation(self) -> list:
        # Frames record the states of the AMoD model for animation purpose
        frames_system_states = []

        if DEBUG_PRINT:
            for T in range(CYCLE_S, self.system_shutdown_time_sec + CYCLE_S, CYCLE_S):
                self.dispatch_at_time(T)
                if RENDER_VIDEO and self.main_sim_start_time_sec < T <= self.main_sim_end_time_sec:
                    frames_system_states.append(copy.deepcopy(self.vehs))
        else:
            for T in tqdm(range(CYCLE_S, self.system_shutdown_time_sec + CYCLE_S, CYCLE_S), desc=f'AMoD'):
                self.dispatch_at_time(T)
                if RENDER_VIDEO and self.main_sim_start_time_sec < T <= self.main_sim_end_time_sec:
                    frames_system_states.append(copy.deepcopy(self.vehs))
        return frames_system_states

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def dispatch_at_time(self, T):
        t = timer_start()
        assert (T == self.T + CYCLE_S)
        if self.T == self.main_sim_start_time_sec:
            self.main_sim_start_time_stamp = get_time_stamp_datetime()

        if DEBUG_PRINT:
            if self.T < self.main_sim_start_time_sec:
                progress_phase = "Warm Up"
            elif self.main_sim_start_time_sec <= self.T < self.main_sim_end_time_sec:
                progress_phase = "Main Study"
            else:
                progress_phase = "Cool Down"
            print(f"[DEBUG] T = {round(self.T)}s: Epoch {round(T / CYCLE_S)}"
                  f"/{round(self.system_shutdown_time_sec / CYCLE_S)} is running. [{progress_phase}]")

        self.T = T
        # 1. Update the vehicles' positions and the orders' statuses.
        self.upd_vehs_and_reqs_stat_to_time()

        # 2. Generate new reqs.
        new_received_rids = self.gen_reqs_to_time()

        # 3. Assign pending orders to vehicles.
        for veh in self.vehs:
            veh.sche_has_been_updated_at_current_epoch = False
        if self.main_sim_start_time_sec < self.T <= self.main_sim_end_time_sec:
            if self.dispatcher == DispatcherMethod.SBA:
                assign_orders_through_sba(new_received_rids, self.reqs, self.vehs, self.T)
            elif self.dispatcher == DispatcherMethod.OSP:
                assign_orders_through_osp(new_received_rids, self.reqs, self.vehs, self.T)
        else:
            assign_orders_through_sba(new_received_rids, self.reqs, self.vehs, self.T)

        # 4. Reposition idle vehicles to high demand areas.
        if self.rebalancer == RebalancerMethod.NPO:
            reposition_idle_vehicles_to_nearest_pending_orders(self.reqs, self.vehs)

        # 5. Check the statuses of orders, to make sure that no one is assigned to multiple vehicles.
        if DEBUG_PRINT:
            num_of_total_orders = len(self.reqs)
            num_of_completed_orders = num_of_onboard_orders = num_of_picking_orders \
                = num_of_pending_orders = num_of_walkaway_orders = 0
            for req in self.reqs:
                if req.status == OrderStatus.COMPLETE:
                    num_of_completed_orders += 1
                elif req.status == OrderStatus.ONBOARD:
                    num_of_onboard_orders += 1
                elif req.status == OrderStatus.PICKING:
                    num_of_picking_orders += 1
                elif req.status == OrderStatus.PENDING:
                    num_of_pending_orders += 1
                elif req.status == OrderStatus.WALKAWAY:
                    num_of_walkaway_orders += 1
            assert (num_of_total_orders == num_of_completed_orders + num_of_onboard_orders + num_of_picking_orders
                    + num_of_pending_orders + num_of_walkaway_orders)
            num_of_onboard_orders_from_vehicle_schedule = num_of_picking_orders_from_vehicle_schedule = \
                num_of_dropping_orders_from_vehicle_schedule = 0
            for veh in self.vehs:
                num_of_onboard_orders_from_vehicle_schedule += len(veh.onboard_rids)
                for (rid, pod, tnid, ddl) in veh.sche:
                    if pod == 1:
                        num_of_picking_orders_from_vehicle_schedule += 1
                    if pod == -1:
                        num_of_dropping_orders_from_vehicle_schedule += 1

            assert (num_of_onboard_orders_from_vehicle_schedule + num_of_picking_orders_from_vehicle_schedule
                    == num_of_dropping_orders_from_vehicle_schedule)
            assert (num_of_picking_orders == num_of_picking_orders_from_vehicle_schedule)
            assert (num_of_onboard_orders == num_of_onboard_orders_from_vehicle_schedule)

            print(f"        T = {self.T}s: "
                  f"Epoch {round(self.T / CYCLE_S)}/{round(self.system_shutdown_time_sec / CYCLE_S)} has finished. "
                  f"Total orders received = {num_of_total_orders}, of which {num_of_completed_orders} complete "
                  f"+ {num_of_onboard_orders} onboard + {num_of_picking_orders} picking "
                  f"+ {num_of_pending_orders} pending + {num_of_walkaway_orders} walkaway ({timer_end(t)})")
            print()

        if self.T == self.main_sim_end_time_sec:
            self.main_sim_end_time_stamp = get_time_stamp_datetime()

    # update vehs and reqs status to their planned positions at time self.T
    def upd_vehs_and_reqs_stat_to_time(self):
        t = timer_start()
        if DEBUG_PRINT:
            print(f"        -Updating vehicles positions and orders status by {CYCLE_S}s...")

        # Advance the vehicles by the whole cycle.
        for veh in self.vehs:
            done = veh.move_to_time(self.T, self.main_sim_start_time_sec < self.T <= self.main_sim_end_time_sec)
            for (rid, pod, time_of_arrival) in done:
                if pod == 1:
                    self.reqs[rid].update_pick_info(time_of_arrival)
                    # print('veh', veh.id, 'picked', rid)
                elif pod == -1:
                    self.reqs[rid].update_drop_info(time_of_arrival)
                    # print('veh', veh.id, 'dropped', rid)

        # Reject the long waited orders.
        for req in self.reqs:
            if not req.status == OrderStatus.PENDING:
                continue
            if req.Tr + 150 <= self.T or req.Clp <= self.T:
                req.status = OrderStatus.WALKAWAY

        if DEBUG_PRINT:
            noi = 0  # number of idle vehicles
            nor = 0  # number of rebalancing vehicles
            nop = 0  # number of picked requests
            nod = 0  # number of dropped requests
            for veh in self.vehs:
                nop += len(veh.new_picked_rids)
                nod += len(veh.new_dropped_rids)
                if veh.status == VehicleStatus.IDLE:
                    noi += 1
                elif veh.status == VehicleStatus.REBALANCING:
                    nor += 1
            print(f"            +Picked orders: {nop}, Dropped orders: {nod}")
            print(f"            +Idle vehicles: {noi}/{FLEET_SIZE}, "
                  f"Rebalancing vehicles: {nor}/{FLEET_SIZE} ({timer_end(t)})")

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self) -> list[int]:
        t = timer_start()
        if DEBUG_PRINT:
            print(f"        -Loading new orders... [T = {self.T}s]")

        new_received_rids = []
        current_request_count = len(self.reqs)
        new_raw_req_idx = self.req_init_idx + int(current_request_count / REQUEST_DENSITY)
        while self.reqs_data[new_raw_req_idx].request_time_sec < self.T + self.req_init_time_sec:
            new_raw_req = self.reqs_data[new_raw_req_idx]
            req_id = current_request_count
            req_Tr = new_raw_req.request_time_sec - self.req_init_time_sec
            req_onid = new_raw_req.origin_node_id
            req_dnid = new_raw_req.destination_node_id
            req = Req(req_id, req_Tr, req_onid, req_dnid)
            current_request_count += 1
            new_raw_req_idx = self.req_init_idx + int(current_request_count / REQUEST_DENSITY)
            new_received_rids.append(len(self.reqs))
            self.reqs.append(req)

        if DEBUG_PRINT:
            print(f"            +Orders new received: {len(new_received_rids)} ({timer_end(t)})")

        return new_received_rids

    def __str__(self):
        # Get the real world time when the simulation starts and ends.
        simulation_start_time_real_world_date = self.start_time_stamp.strftime('%Y-%m-%d %H:%M:%S')
        self.end_time_stamp = get_time_stamp_datetime()
        if len(self.reqs) == 0:
            simulation_end_time_real_world_date = "0000-00-00 00:00:00"
        else:
            simulation_end_time_real_world_date = self.end_time_stamp.strftime('%Y-%m-%d %H:%M:%S')
        total_sim_runtime_s = (self.end_time_stamp - self.start_time_stamp).seconds
        main_sim_runtime_s = (self.main_sim_end_time_stamp - self.main_sim_start_time_stamp).seconds

        # Convert the running time to format h:m:s.
        total_sim_runtime_formatted = str(timedelta(seconds=int(total_sim_runtime_s)))
        main_sim_runtime_formatted = str(timedelta(seconds=int(main_sim_runtime_s)))

        # Get some system configurations
        sim_start_time_date = SIMULATION_START_TIME
        main_sim_start_date = str(parse(SIMULATION_START_TIME) + timedelta(seconds=self.main_sim_start_time_sec))
        main_sim_end_date = str(parse(SIMULATION_START_TIME) + timedelta(seconds=self.main_sim_end_time_sec))
        sim_end_time_date = str(parse(SIMULATION_START_TIME) + timedelta(seconds=self.system_shutdown_time_sec))
        num_of_epochs = int(self.system_shutdown_time_sec / CYCLE_S)
        num_of_main_epochs = int(SIMULATION_DURATION_MIN * 60 / CYCLE_S)

        param = f"# Simulation Runtime" \
                f"\n  - Start: {simulation_start_time_real_world_date}, End: {simulation_end_time_real_world_date}, " \
                f"Time: {total_sim_runtime_formatted}." \
                f"\n  - Main Simulation: init_time = {self.time_of_init:.2f} s, runtime = {main_sim_runtime_formatted}, "\
                f"avg_time = {main_sim_runtime_s / num_of_main_epochs:.2f} s. "\
                f"\n# System Configurations"\
                f"\n  - From {sim_start_time_date[11:]} to {sim_end_time_date[11:]}. "\
                f"(main simulation between {main_sim_start_date[11:]} and {main_sim_end_date[11:]})."\
                f"\n  - Fleet Config: size = {FLEET_SIZE}, capacity = {VEH_CAPACITY}. "\
                f"({int(WARMUP_DURATION_MIN * 60 / CYCLE_S)} + {num_of_main_epochs} + "\
                f"{int(WINDDOWN_DURATION_MIN * 60 / CYCLE_S)} = {num_of_epochs} epochs)."\
                f"\n  - Order Config: density = {REQUEST_DENSITY} ({DATA_FILE}), "\
                f"max_wait = {MAX_PICKUP_WAIT_TIME_MIN * 60} s. (Δt = {CYCLE_S} s)."\
                f"\n  - Dispatch Config: dispatcher = {DISPATCHER}, rebalancer = {REBALANCER}."

        return param
