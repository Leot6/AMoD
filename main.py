
# start time of initialization
from src.utility.utility_functions import *
print("Initializing the simulator ...")
s_time = get_time_stamp_datetime()
from src.simulator.platform import Platform


if __name__ == '__main__':
    # Initialize the AMoD model
    platform = Platform(s_time)
    platform.create_report()

    # Run simulation
    frames_system_states = platform.run_simulation()

    # Output the simulation results and save data
    platform.create_report()

    # Generate, show and save the animation of this simulation
    if RENDER_VIDEO:
        print('...Outputing simulation video...')
        anime = anim(frames_system_states)
        # plt.show()
