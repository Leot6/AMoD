"""
main structure for the AMoD simulator
"""

from src.simulator.request import Req
from src.simulator.vehicle import Veh
from src.simulator.route_functions import *

from src.dispatcher.dispatch_sba import assign_orders_through_sba
from src.dispatcher.dispatch_osp import assign_orders_through_osp
from src.rebalancer.rebalancing_npo import reposition_idle_vehicles_to_nearest_pending_orders
from src.value_function.value_function import ValueFunction


class Platform(object):
    """
    Model is the initial class for the AMoD system
    Attributes:
        system_time_sec: system time at current state
        vehs: the list of vehicles
        reqs: the list of all received requests
        reqs_data: the list of collected real taxi requests data
        req_init_idx: init index to read reqs_data
        dispatcher: the algorithm used to do the dispatching
        rebalancer: the algorithm used to do the rebalancing

    """

    def __init__(self, taxi_data_file: str,
                 value_func: ValueFunction,
                 simulation_start_time_stamp: datetime):
        t = timer_start()
        self.taxi_data_file = taxi_data_file
        self.value_func = value_func

        # Initialize the simulation times.
        self.system_time_sec = 0
        self.main_sim_start_time_sec = self.system_time_sec + WARMUP_DURATION_MIN * 60
        self.main_sim_end_time_sec = self.main_sim_start_time_sec + SIMULATION_DURATION_MIN * 60
        self.system_shutdown_time_sec = self.main_sim_end_time_sec + WINDDOWN_DURATION_MIN * 60
        simulation_start_time = SIMULATION_START_TIME
        simulatuon_max_end_time = simulation_start_time[:10] + " 23:59:59"
        remaining_time_of_the_day_ms = compute_the_accumulated_seconds_from_0_clock(simulatuon_max_end_time) - \
                                       compute_the_accumulated_seconds_from_0_clock(simulation_start_time)
        assert (remaining_time_of_the_day_ms >= self.system_shutdown_time_sec
                and "[ERROR] WRONG TIME SETTING! Please check the simulation start time or duration in config!")

        # Initialize the fleet.
        self.vehs = []
        num_of_stations = get_num_of_vehicle_stations()
        for i in range(FLEET_SIZE[0]):
            station_idx = int(i * num_of_stations / FLEET_SIZE[0])
            nid = get_vehicle_station_id(station_idx)
            [lng, lat] = get_node_geo(nid)
            self.vehs.append(Veh(i, nid, lng, lat, VEH_CAPACITY[0], self.system_time_sec))

        # Initialize the demand generator.
        self.reqs = []
        t = timer_start()
        with open(f"{PARTIAL_PATH_TO_TAXI_DATA}{self.taxi_data_file}.pickle", "rb") as f:
            self.reqs_data = pickle.load(f)
        self.req_init_time_sec = compute_the_accumulated_seconds_from_0_clock(SIMULATION_START_TIME)
        self.req_init_idx = 0
        while self.reqs_data[self.req_init_idx].request_time_sec < self.req_init_time_sec:
            self.req_init_idx += 1
        print(f"[INFO] Demand Generator is ready. ({timer_end(t)})")

        # Initialize the dispatcher and the rebalancer.
        if DISPATCHER == "SBA":
            self.dispatcher = DispatcherMethod.SBA
        elif DISPATCHER == "OSP-NR":
            self.dispatcher = DispatcherMethod.OSP_NR
        elif DISPATCHER == "OSP":
            self.dispatcher = DispatcherMethod.OSP
        else:
            assert (False and "[ERROR] WRONG DISPATCHER SETTING! Please check the name of dispatcher in config!")
        if REBALANCER == "NONE":
            self.rebalancer = RebalancerMethod.NONE
        elif REBALANCER == "NPO":
            self.rebalancer = RebalancerMethod.NPO
        else:
            assert (False and "[ERROR] WRONG REBALANCER SETTING! Please check the name of rebalancer in config!")

        # System report about running time.
        self.time_of_init = get_runtime_sec_from_t_to_now(simulation_start_time_stamp)
        self.start_time_stamp = get_time_stamp_datetime()
        self.end_time_stamp = get_time_stamp_datetime()
        self.main_sim_start_time_stamp = get_time_stamp_datetime()
        self.main_sim_end_time_stamp = get_time_stamp_datetime()
        self.main_sim_result = [0, 0, 0.0]  # [service_req_count, total_req_count, service_rate]
        print(f"[INFO] Platform is ready. ({timer_end(t)})")

    def test_get_num_reqs(self):
        num_reqs_at_each_epochs = []
        for epoch_start_time_sec in range(0, self.system_shutdown_time_sec, CYCLE_S[0]):
            self.system_time_sec = epoch_start_time_sec + CYCLE_S[0]
            new_received_rids = self.gen_reqs_to_time()
            num_reqs_at_each_epochs.append(len(new_received_rids))
        dataframe = pd.DataFrame({"num req": num_reqs_at_each_epochs})
        dataframe.to_csv(f"{ROOT_PATH}/datalog-gitignore/num-req-{self.taxi_data_file}.csv")

    def run_simulation(self) -> list:
        # Frames record the states of the AMoD model for animation purpose
        frames_system_states = []

        if DEBUG_PRINT:
            for epoch_start_time_sec in range(0, self.system_shutdown_time_sec, CYCLE_S[0]):
                self.run_cycle(epoch_start_time_sec)
                if RENDER_VIDEO and self.main_sim_start_time_sec <= epoch_start_time_sec < self.main_sim_end_time_sec:
                    frames_system_states.append(copy.deepcopy(self.vehs))
        else:
            for epoch_start_time_sec in tqdm(range(0, self.system_shutdown_time_sec, CYCLE_S[0]), desc=f'AMoD'):
                self.run_cycle(epoch_start_time_sec)
                if RENDER_VIDEO and self.main_sim_start_time_sec <= epoch_start_time_sec < self.main_sim_end_time_sec:
                    frames_system_states.append(copy.deepcopy(self.vehs))

        self.end_time_stamp = get_time_stamp_datetime()
        return frames_system_states

    # dispatch the AMoD system: move vehicles, generate requests, assign and rebalance
    def run_cycle(self, epoch_start_time_sec):
        t = timer_start()
        assert (epoch_start_time_sec == self.system_time_sec)
        if epoch_start_time_sec == self.main_sim_start_time_sec:
            self.main_sim_start_time_stamp = get_time_stamp_datetime()

        if DEBUG_PRINT:
            if epoch_start_time_sec < self.main_sim_start_time_sec:
                progress_phase = "Warm Up"
            elif self.main_sim_start_time_sec <= epoch_start_time_sec < self.main_sim_end_time_sec:
                progress_phase = "Main Study"
            else:
                progress_phase = "Cool Down"
            print(f"[DEBUG] T = {round(self.system_time_sec)}s: Epoch {round(self.system_time_sec / CYCLE_S[0]) + 1}"
                  f"/{round(self.system_shutdown_time_sec / CYCLE_S[0])} is running. [{progress_phase}]")

        # 0. Update the system time to the end of the epoch.
        epoch_end_time_sec = epoch_start_time_sec + CYCLE_S[0]
        self.system_time_sec = epoch_end_time_sec

        # 1. Update the vehicles' positions and the orders' statuses.
        self.upd_vehs_and_reqs_stat_to_time()

        # 2. Generate new reqs.
        new_received_rids = self.gen_reqs_to_time()

        # 3. Assign pending orders to vehicles.
        for veh in self.vehs:
            veh.sche_has_been_updated_at_current_epoch = False
        if verify_the_current_epoch_is_in_the_main_study_horizon(epoch_end_time_sec):
            if self.dispatcher == DispatcherMethod.SBA:
                assign_orders_through_sba(new_received_rids, self.reqs, self.vehs, self.system_time_sec,
                                          self.value_func)
            elif self.dispatcher == DispatcherMethod.OSP_NR:
                assign_orders_through_osp(new_received_rids, self.reqs, self.vehs, self.system_time_sec,
                                          self.value_func, is_reoptimization=False)
            elif self.dispatcher == DispatcherMethod.OSP:
                assign_orders_through_osp(new_received_rids, self.reqs, self.vehs, self.system_time_sec,
                                          self.value_func)
        else:
            assign_orders_through_sba(new_received_rids, self.reqs, self.vehs, self.system_time_sec, self.value_func)

        # 4. Reposition idle vehicles to high demand areas.
        if self.rebalancer == RebalancerMethod.NPO:
            reposition_idle_vehicles_to_nearest_pending_orders(self.reqs, self.vehs, self.system_time_sec,
                                                               len(new_received_rids), self.value_func)

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

            print(f"        T = {self.system_time_sec}s: "
                  f"Epoch {round(self.system_time_sec / CYCLE_S[0])}/{round(self.system_shutdown_time_sec / CYCLE_S[0])} "
                  f"has finished. "
                  f"Total orders received = {num_of_total_orders}, of which {num_of_completed_orders} complete "
                  f"+ {num_of_onboard_orders} onboard + {num_of_picking_orders} picking "
                  f"+ {num_of_pending_orders} pending + {num_of_walkaway_orders} walkaway ({timer_end(t)})")
            print()

        if self.system_time_sec == self.main_sim_end_time_sec:
            self.main_sim_end_time_stamp = get_time_stamp_datetime()

    # update vehs and reqs status to their planned positions at time self.system_time_sec
    def upd_vehs_and_reqs_stat_to_time(self):
        t = timer_start()
        if DEBUG_PRINT:
            print(f"        -Updating vehicles positions and orders status by {CYCLE_S[0]}s...")

        # Advance the vehicles by the whole cycle.
        for veh in self.vehs:
            done = veh.move_to_time(self.system_time_sec,
                                    verify_the_current_epoch_is_in_the_main_study_horizon(self.system_time_sec))
            for (rid, pod, time_of_arrival) in done:
                if pod == 1:
                    self.reqs[rid].update_pick_info(time_of_arrival)
                elif pod == -1:
                    self.reqs[rid].update_drop_info(time_of_arrival)

        # Reject the long waited orders.
        for req in self.reqs:
            if req.status != OrderStatus.PENDING:
                continue
            if self.system_time_sec >= req.Tr + 150 or self.system_time_sec >= req.Clp:
                req.status = OrderStatus.WALKAWAY

        if DEBUG_PRINT:
            noi = 0  # number of idle vehicles at the end of the current epoch
            nor = 0  # number of rebalancing vehicles at the end of the current epoch
            nop = 0  # number of picked requests during the current epoch
            nod = 0  # number of dropped requests during the current epoch
            for veh in self.vehs:
                nop += len(veh.new_picked_rids)
                nod += len(veh.new_dropped_rids)
                if veh.status == VehicleStatus.IDLE:
                    noi += 1
                elif veh.status == VehicleStatus.REBALANCING:
                    nor += 1
            print(f"            +Picked orders: {nop}, Dropped orders: {nod}")
            print(f"            +Idle vehicles: {noi}/{FLEET_SIZE[0]}, "
                  f"Rebalancing vehicles: {nor}/{FLEET_SIZE[0]} ({timer_end(t)})")

    # generate requests up to time T, loading from reqs data file
    def gen_reqs_to_time(self) -> list[int]:
        t = timer_start()
        if DEBUG_PRINT:
            print(f"        -Loading new orders submitted during "
                  f"{self.system_time_sec - CYCLE_S[0]}s ≤ T < {self.system_time_sec}s...")

        new_received_rids = []
        current_request_count = len(self.reqs)
        new_raw_req_idx = self.req_init_idx + int(current_request_count / REQUEST_DENSITY)
        while self.reqs_data[new_raw_req_idx].request_time_sec < self.system_time_sec + self.req_init_time_sec:
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

            # if DEBUG_PRINT:
            #     print(f"            Received req #{req_id} at T = {req_Tr}s, from {req_onid} to {req_dnid}")

        if DEBUG_PRINT:
            print(f"            +Orders new received: {len(new_received_rids)} ({timer_end(t)})")
            print(f"        T = {self.system_time_sec}s: Dispatcher is running.")
        return new_received_rids

    def create_report(self, show: bool = True):
        # 1. Get the width of the current console window.
        window_width = shutil.get_terminal_size().columns
        if window_width == 0 or window_width > 90:
            window_width = 90
        dividing_line = "-" * window_width

        # 2. Report the simulation config.
        if show:
            print(dividing_line)
            self.report_simulation_config()

        if len(self.reqs) == 0:
            if show:
                print(dividing_line)
            return

        # 3. Report the simulation result / performance.
        self.report_simulation_result(show)
        if show:
            print(dividing_line)

    def report_simulation_config(self):
        # Get the real world time when the simulation starts and ends.
        simulation_start_time_real_world_date = self.start_time_stamp.strftime('%Y-%m-%d %H:%M:%S')
        if len(self.reqs) == 0:
            simulation_end_time_real_world_date = "0000-00-00 00:00:00"
        else:
            simulation_end_time_real_world_date = self.end_time_stamp.strftime('%Y-%m-%d %H:%M:%S')

        # Get the simulation running times and convert them to format h:m:s.
        total_sim_runtime_s = (self.end_time_stamp - self.start_time_stamp).seconds
        main_sim_runtime_s = (self.main_sim_end_time_stamp - self.main_sim_start_time_stamp).seconds
        total_sim_runtime_formatted = str(timedelta(seconds=int(total_sim_runtime_s)))
        main_sim_runtime_formatted = str(timedelta(seconds=int(main_sim_runtime_s)))

        # Get some system configurations
        sim_start_time_date = SIMULATION_START_TIME
        main_sim_start_date = str(parse(SIMULATION_START_TIME) + timedelta(seconds=self.main_sim_start_time_sec))
        main_sim_end_date = str(parse(SIMULATION_START_TIME) + timedelta(seconds=self.main_sim_end_time_sec))
        sim_end_time_date = str(parse(SIMULATION_START_TIME) + timedelta(seconds=self.system_shutdown_time_sec))
        num_of_epochs = int(self.system_shutdown_time_sec / CYCLE_S[0])
        num_of_main_epochs = int(SIMULATION_DURATION_MIN * 60 / CYCLE_S[0])

        # Print the simulation runtime.
        print("# Simulation Runtime")
        print(f"  - Start: {simulation_start_time_real_world_date}, End: {simulation_end_time_real_world_date}, "
              f"Time: {total_sim_runtime_formatted}.")
        print(f"  - Main Simulation: init_time = {self.time_of_init:.2f} s, runtime = {main_sim_runtime_formatted}, "
              f"avg_time = {main_sim_runtime_s / num_of_main_epochs:.2f} s.")

        # Print the platform configurations.
        print("# System Configurations")
        print(f"  - From {sim_start_time_date[11:]} to {sim_end_time_date[11:]}. "
              f"(main simulation between {main_sim_start_date[11:]} and {main_sim_end_date[11:]}).")
        print(f"  - Fleet Config: size = {FLEET_SIZE[0]}, capacity = {VEH_CAPACITY[0]}. "
              f"({int(WARMUP_DURATION_MIN * 60 / CYCLE_S[0])} + {num_of_main_epochs} + "
              f"{int(WINDDOWN_DURATION_MIN * 60 / CYCLE_S[0])} = {num_of_epochs} epochs).")
        print(f"  - Order Config: density = {REQUEST_DENSITY} ({self.taxi_data_file}), "
              f"max_wait = {MAX_PICKUP_WAIT_TIME_MIN[0] * 60} s. (Δt = {CYCLE_S[0]} s).")
        print(f"  - Dispatch Config: dispatcher = {DISPATCHER}, rebalancer = {REBALANCER}.")

    def report_simulation_result(self, show: bool = True):
        # 1. Report order status.
        req_count = 0
        walkaway_req_count = 0
        complete_req_count = 0
        onboard_req_count = 0
        picking_req_count = 0
        pending_req_count = 0
        total_wait_time_sec = 0
        total_delay_time_sec = 0
        total_req_time_sec = 0

        for req in self.reqs:
            if req.Tr <= self.main_sim_start_time_sec:
                continue
            if req.Tr > self.main_sim_end_time_sec:
                break
            req_count += 1
            if req.status == OrderStatus.WALKAWAY:
                walkaway_req_count += 1
            elif req.status == OrderStatus.COMPLETE:
                complete_req_count += 1
                total_wait_time_sec += req.Tp - req.Tr
                total_delay_time_sec += req.Td - (req.Tr + req.Ts)
                total_req_time_sec += req.Ts
            elif req.status == OrderStatus.ONBOARD:
                onboard_req_count += 1
            elif req.status == OrderStatus.PICKING:
                picking_req_count += 1
            elif req.status == OrderStatus.PENDING:
                pending_req_count += 1

        service_req_count = complete_req_count + onboard_req_count
        self.main_sim_result = [service_req_count, req_count, round(100.0 * service_req_count / req_count, 2)]
        assert (service_req_count + picking_req_count + pending_req_count == req_count - walkaway_req_count)
        if not show:
            return

        print(f"# Orders ({req_count - walkaway_req_count}/{req_count})")
        print(f"  - complete = {complete_req_count} ({100.0 * complete_req_count / req_count:.2f}%), "
              f"onboard = {onboard_req_count} ({100.0 * onboard_req_count / req_count:.2f}%), "
              f"total_service = {service_req_count} ({100.0 * service_req_count / req_count:.2f}%).")
        if picking_req_count + pending_req_count > 0:
            print(f"  - picking = {picking_req_count} ({100.0 * picking_req_count / req_count:.2f}%), "
                  f"pending = {pending_req_count} ({100.0 * pending_req_count / req_count:.2f}%).")
        if complete_req_count > 0:
            print(f"  - avg_shortest_travel = {total_req_time_sec / complete_req_count:.2f} s, "
                  f"avg_wait = {total_wait_time_sec / complete_req_count:.2f} s, "
                  f"avg_delay = {total_delay_time_sec / complete_req_count:.2f} s.")
        else:
            print("  [PLEASE USE LONGER SIMULATION DURATION TO BE ABLE TO COMPLETE ORDERS!]")

        # 2. Report veh status.
        total_dist_traveled = 0
        total_loaded_dist_traveled = 0
        total_empty_dist_traveled = 0
        total_rebl_dist_traveled = 0
        total_time_traveled_sec = 0
        total_loaded_time_traveled_sec = 0
        total_empty_time_traveled_sec = 0
        total_rebl_time_traveled_sec = 0

        for veh in self.vehs:
            total_dist_traveled += veh.Ds
            total_loaded_dist_traveled += veh.Ld
            total_empty_dist_traveled += veh.Ds_empty
            total_rebl_dist_traveled += veh.Dr
            total_time_traveled_sec += veh.Ts
            total_loaded_time_traveled_sec += veh.Lt
            total_empty_time_traveled_sec += veh.Ts_empty
            total_rebl_time_traveled_sec += veh.Tr

        avg_dist_traveled_km = total_dist_traveled / 1000.0 / FLEET_SIZE[0]
        avg_empty_dist_traveled_km = total_empty_dist_traveled / 1000.0 / FLEET_SIZE[0]
        avg_rebl_dist_traveled_km = total_rebl_dist_traveled / 1000.0 / FLEET_SIZE[0]
        avg_time_traveled_s = total_time_traveled_sec / FLEET_SIZE[0]
        avg_empty_time_traveled_s = total_empty_time_traveled_sec / FLEET_SIZE[0]
        avg_rebl_time_traveled_s = total_rebl_time_traveled_sec / FLEET_SIZE[0]
        print(f"# Vehicles ({FLEET_SIZE[0]})")
        print(f"  - Travel Distance: total_dist = {total_dist_traveled / 1000.0:.2f} km, "
              f"avg_dist = {avg_dist_traveled_km:.2f} km.")
        print(f"  - Travel Duration: avg_time = {avg_time_traveled_s:.2f} s "
              f"({100.0 * avg_time_traveled_s / 60 / SIMULATION_DURATION_MIN:.2f}% of the main simulation time).")
        print(f"  - Empty Travel: avg_time = {avg_empty_time_traveled_s:.2f} s "
              f"({100.0 * avg_empty_time_traveled_s / avg_time_traveled_s:.2f}%), "
              f"avg_dist = {avg_empty_dist_traveled_km:.2f} km "
              f"({100.0 * avg_empty_dist_traveled_km / avg_dist_traveled_km:.2f}%).")
        print(f"  - Rebl Travel: avg_time = {avg_rebl_time_traveled_s:.2f} s "
              f"({100.0 * avg_rebl_time_traveled_s / avg_time_traveled_s:.2f}%), "
              f"avg_dist = {avg_rebl_dist_traveled_km:.2f} km "
              f"({100.0 * avg_rebl_dist_traveled_km / avg_dist_traveled_km:.2f}%).")
        print(f"  - Travel Load: average_load_dist = {total_loaded_dist_traveled / total_dist_traveled:.2f}, "
              f"average_load_time = {total_loaded_time_traveled_sec / total_time_traveled_sec:.2f}.")
