

import time
# start time of initialization
istime = time.time()
print('initializing the simulator ...')
import datetime
import copy
import matplotlib.pyplot as plt
from tqdm import tqdm
from lib.S_Main import Model
from lib.Configure import DMD_SST, T_TOTAL, INT_ASSIGN, IS_ANIMATION, IS_ANALYSIS, IS_DEBUG, MODEE, DMD_VOL, DMD_STR, \
    RIDESHARING_SIZE, MAX_WAIT, MAX_DELAY, MET_REBL, TRAVEL_TIME, IS_STOCHASTIC, IS_STOCHASTIC_CONSIDERED
from lib.S_Analysis import anim, print_results

if __name__ == '__main__':
    # frames record the states of the AMoD model for animation purpose
    frames = []
    # initialize the AMoD model
    model = Model()
    print('*' * 80)
    print('scenario: %s' % (DMD_STR))
    print('simulation starts at %s, initializing time: %.02f s' % (model.start_time, time.time() - istime))
    print('system settings:')
    print('  - from %s to %s, with %d intervals'
          % (DMD_SST, DMD_SST + datetime.timedelta(seconds=T_TOTAL), T_TOTAL / INT_ASSIGN))
    print('  - fleet size: %d; capacity: %d; ride-sharing computational size: %d'
          % (model.V, model.K, RIDESHARING_SIZE))
    print('  - demand value:%.02f, max waiting time: %d; max delay: %d' % (DMD_VOL, MAX_WAIT, MAX_DELAY))
    print('  - assignment mode: %s, travel time: %s, interval: %.1f s' % (MODEE, TRAVEL_TIME, INT_ASSIGN))
    print('  - stochastic travel time: %s, stochastic planning: %s' % (IS_STOCHASTIC, IS_STOCHASTIC_CONSIDERED))
    print('*' * 80)
    print('')

    # start time of simulation
    stime = time.time()
    # dispatch the system for T_TOTAL seconds, at the interval of INT_ASSIGN
    for T in tqdm(range(INT_ASSIGN, T_TOTAL+INT_ASSIGN, INT_ASSIGN), desc='AMoD simulation'):
        # start time of each episode
        estime = time.time()
        model.dispatch_at_time(T)
        if IS_ANIMATION:
            frames.append(copy.deepcopy(model.vehs))
        if IS_DEBUG:
            print('System situation at %s : %d reqs have been received, %d have been served (%.02f%%), %d are on board '
                  '(%.02f%%), %d are being picked-up (%.02f%%), %d are unassigned (%.02f%%), %d are rejected (%.02f%%).'
                  % (DMD_SST + datetime.timedelta(seconds=T),
                     model.N, len(model.reqs_served), (len(model.reqs_served) / model.N * 100),
                     len(model.reqs_serving), (len(model.reqs_serving) / model.N * 100),
                     len(model.reqs_picking), (len(model.reqs_picking) / model.N * 100),
                     len(model.reqs_unassigned), (len(model.reqs_unassigned) / model.N * 100),
                     len(model.rejs), (len(model.rejs) / model.N * 100)))
            print('...running time of simulation: %.02f seconds (last interval:%.02f)'
                  % ((time.time() - stime), (time.time() - estime)))
            print()

    print('End of this simulation.')
    # end time
    etime = time.time()
    end_time = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M')
    # run time of this simulation
    runtime = str(datetime.timedelta(seconds=int(etime - stime)))
    mean_runtime = round((etime - stime) / T_TOTAL * INT_ASSIGN, 2)

    # print('...running time of simulation: %s, average: %.02f'
    #       % (str(datetime.timedelta(seconds=int(runtime))), runtime / T_TOTAL * INT_ASSIGN))

    # generate, show and save the animation of this simulation
    if IS_ANIMATION:
        print('...Outputing simulation video...')
        anime = anim(frames)
        anime.save('output/anim.mp4', dpi=130, fps=None, extra_args=['-vcodec', 'libx264'])
        # plt.show()

    # output the simulation results and save data
    if IS_ANALYSIS:
        print_results(model, runtime, mean_runtime, end_time)
