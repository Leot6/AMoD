"""
Create the report based on the statistical analysis using the simulated data.
"""

import csv
import datetime
import shutil
import numpy as np
import pandas as pd
from src.simulator.config import *
from src.simulator.types import *


def print_system_report(platform):
    # Get the width of the current console window.
    window_width = shutil.get_terminal_size().columns
    if window_width == 0 or window_width > 90:
        window_width = 90
    dividing_line = "-" * window_width

    print(dividing_line)
    print(platform)

    if len(platform.reqs) == 0:
        print(dividing_line)
        return

    # Report order status.
    req_count = 0
    walkaway_req_count = 0
    complete_req_count = 0
    onboard_req_count = 0
    picking_req_count = 0
    pending_req_count = 0
    total_wait_time_sec = 0
    total_delay_time_sec = 0
    total_req_time_sec = 0

    for req in platform.reqs:
        if req.Tr <= platform.main_sim_start_time_sec:
            continue
        if req.Tr > platform.main_sim_end_time_sec:
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
    assert (service_req_count + picking_req_count + pending_req_count == req_count - walkaway_req_count)
    print(f"# Orders ({req_count - walkaway_req_count}/{req_count})")
    print(f"  - complete = {complete_req_count} ({100.0 * complete_req_count / req_count:.2f}%), "
          f"onboard = {onboard_req_count} ({100.0 * onboard_req_count / req_count:.2f}%), "
          f"total_service = {service_req_count} ({100.0 * service_req_count / req_count:.2f}%).")
    if picking_req_count + pending_req_count > 0:
        print(f"  - picking = {picking_req_count} ({100.0 * picking_req_count / req_count:.2f}%), "
              f"pending = {pending_req_count} ({100.0 * pending_req_count / req_count:.2f}%).")
    if complete_req_count > 0:
        print(f"  - avg_shortest_travel = {total_req_time_sec / 1000.0 / complete_req_count:.2f} s, "
              f"avg_wait = {total_wait_time_sec / complete_req_count:.2f} s, "
              f"avg_delay = {total_delay_time_sec / complete_req_count:.2f} s.")
    else:
        print("  [PLEASE USE LONGER SIMULATION DURATION TO BE ABLE TO COMPLETE ORDERS!]")

    # Report veh status.
    total_dist_traveled = 0
    total_loaded_dist_traveled = 0
    total_empty_dist_traveled = 0
    total_rebl_dist_traveled = 0
    total_time_traveled_sec = 0
    total_loaded_time_traveled_sec = 0
    total_empty_time_traveled_sec = 0
    total_rebl_time_traveled_sec = 0

    for veh in platform.vehs:
        total_dist_traveled += veh.Ds
        total_loaded_dist_traveled += veh.Ld
        total_empty_dist_traveled += veh.Ds_empty
        total_rebl_dist_traveled += veh.Dr
        total_time_traveled_sec += veh.Ts
        total_loaded_time_traveled_sec += veh.Lt
        total_empty_time_traveled_sec += veh.Ts_empty
        total_rebl_time_traveled_sec += veh.Tr

    avg_dist_traveled_km = total_dist_traveled / 1000.0 / len(platform.vehs)
    avg_empty_dist_traveled_km = total_empty_dist_traveled / 1000.0 / len(platform.vehs)
    avg_rebl_dist_traveled_km = total_rebl_dist_traveled / 1000.0 / len(platform.vehs)
    avg_time_traveled_s = total_time_traveled_sec / len(platform.vehs)
    avg_empty_time_traveled_s = total_empty_time_traveled_sec / len(platform.vehs)
    avg_rebl_time_traveled_s = total_rebl_time_traveled_sec / len(platform.vehs)
    print(f"# Vehicles ({len(platform.vehs)})")
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

    print(dividing_line)



