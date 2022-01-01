
# start time of initialization
from src.utility.utility_functions import *
print("Initializing the simulator ...")
s_time = get_time_stamp_datetime()
from src.simulator.platform import Platform


if __name__ == '__main__':
    # Initialize the AMoD model
    platform = Platform(s_time)
    print_system_report(platform)

    # Run simulation
    frames_system_states = platform.run_simulation()

    # Get the end time
    platform.end_time = get_time_stamp_datetime()

    # Output the simulation results and save data
    print_system_report(platform)

    # Generate, show and save the animation of this simulation
    if RENDER_VIDEO:
        print('...Outputing simulation video...')
        anime = anim(frames_system_states)
        # plt.show()
