
# start time of initialization
from src.utility.utility_functions import *
s_time = get_time_stamp_datetime()
print(f"[INFO] Initializing the simulator (fleet_size = {FLEET_SIZE[0]}, capacity = {VEH_CAPACITY[0]}, "
      f"req_density {REQUEST_DENSITY})...")
from src.simulator.platform import Platform
from src.value_function.value_function import ValueFunction


def run_sim(net_file_path=None):
    # 1. Initialize the value_func.
    value_func = ValueFunction()
    value_func.load_eval_net_from_pickle_file(net_file_path)
    main_sim_results = []

    # 2. Run simulations on SIMULATION_DAYs
    for idx, day in enumerate(SIMULATION_DAYs):
        # 2.1. Initialize the AMoD model and print its configuration.
        print(f"\n[INFO] ({idx + 1}/{len(TAXI_DATA_FILEs)}) "
              f"Running simulation on day {day} "
              f"using {DISPATCHER, FLEET_SIZE[0], VEH_CAPACITY[0], MAX_PICKUP_WAIT_TIME_MIN[0]}... ")
        print(f"      (COLLECT_DATA = {COLLECT_DATA}, ENABLE_VALUE_FUNCTION = {ENABLE_VALUE_FUNCTION}, "
              f"ONLINE_TRAINING = {ONLINE_TRAINING})")
        print(f"      (Value_Func = {EVAL_NET_FILE_NAME})")
        platform = Platform(TAXI_DATA_FILEs[idx], value_func, s_time)
        platform.create_report(show=(len(SIMULATION_DAYs) <= 1))
        # 2.2. Run simulation. ("frames_system_states" is only recorded If RENDER_VIDEO is enabled, or it is None.)
        frames_system_states = platform.run_simulation()
        # 2.3. Output the simulation results.
        platform.create_report(show=(len(SIMULATION_DAYs) <= 1))
        main_sim_results.append(platform.main_sim_result)
        print(f"[INFO] Result on {day}: total_service = {platform.main_sim_result[0]}/{platform.main_sim_result[1]} "
              f"({platform.main_sim_result[2]}%)")

    # 3. Output the summary of simulation results. (Mainly used for running simulation on multiple days.)
    print(f"\n[INFO] Simulations were done on {len(TAXI_DATA_FILEs)} days ({SIMULATION_DAYs}), "
          f"using {DISPATCHER, FLEET_SIZE[0], VEH_CAPACITY[0], MAX_PICKUP_WAIT_TIME_MIN[0]}. "
          f"(runtime = {str(timedelta(seconds=(datetime.now() - s_time).seconds))})")
    print(f"      (COLLECT_DATA = {COLLECT_DATA}, ENABLE_VALUE_FUNCTION = {ENABLE_VALUE_FUNCTION}, "
          f"ONLINE_TRAINING = {ONLINE_TRAINING})")
    print(f"      (Value_Func = {EVAL_NET_FILE_NAME})")
    for day, result in zip(SIMULATION_DAYs, main_sim_results):
        print(f"[INFO] Result on {day}: total_service = {result[0]}/{result[1]} ({result[2]}%)")

    # 4. Save the value_func's replay buffer to pickle file for offline learning (if COLLECT_DATA is enabled).
    if COLLECT_DATA:
        value_func.save_replay_buffer_to_pickle_file()

    # _. Generate, show and save the animation of this simulation. (If RENDER_VIDEO is enabled.)
    #  Note: the following anim function has not been updated in a while, so debugs may need to get it run.
    # if RENDER_VIDEO:
    #     print('...Outputing simulation video...')
    #     anime = anim(frames_system_states)
    #     # plt.show()


if __name__ == '__main__':
    run_sim()

    # VC = [2, 4, 6, 8]
    # for vc in VC:
    #     config_change_vc(vc)
    #     run_sim()
    #
    # FS = [1200, 1800]
    # for fs in FS:
    #     config_change_fs(fs)
    #     run_sim()

    # WT = [3, 7]
    # for wt in WT:
    #     config_change_wt(wt)
    #     run_sim()

    # BP = [10, 60, 120]
    # for bp in BP:
    #     config_change_bp(bp)
    #     run_sim()

    # G = [90, 97, 99]
    # for gamma in G:
    #     score_net_file_path = f"{PARTIAL_PATH_TO_REPLAY_BUFFER_DATA}NET-LR1-GAMA{gamma}-FS1500-VC6-9D.pickle"
    #     run_sim(score_net_file_path)



