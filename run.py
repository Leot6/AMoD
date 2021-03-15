

import time
# start time of initialization
init_time = time.time()
print('initializing the simulator ...')
import datetime
import copy
import matplotlib.pyplot as plt
from tqdm import tqdm
from lib.simulator.model import Model
from lib.simulator.config import *
from lib.analysis.result_printer import print_results
from lib.analysis.animation_generator import anim, anim_objective

if __name__ == '__main__':
    # frames record the states of the AMoD model for animation purpose
    frames_vehs = []
    # initialize the AMoD model
    model = Model(init_time)
    print('*' * 80)
    print(model)
    print('*' * 80)

    # start time of simulation
    stime = time.time()
    # dispatch the system for T_TOTAL seconds, at the interval of INT_ASSIGN
    for T in tqdm(range(INT_ASSIGN, T_TOTAL+INT_ASSIGN, INT_ASSIGN), desc=f'AMoD simulation (Δt={INT_ASSIGN}s)'):
        # start time of each episode
        estime = time.time()
        model.dispatch_at_time(T)
        if IS_ANIMATION and T_WARM_UP < T <= T_WARM_UP + T_STUDY:
            frames_vehs.append(copy.deepcopy(model.vehs))
        if IS_DEBUG:
            print('System situation at %s : %d reqs have been received, %d have been served (%.02f%%), %d are on board '
                  '(%.02f%%), %d are being picked-up (%.02f%%), %d are unassigned (%.02f%%), %d are rejected (%.02f%%).'
                  % (DMD_SST + datetime.timedelta(seconds=T),
                     model.N, len(model.reqs_served), (len(model.reqs_served) / model.N * 100),
                     len(model.reqs_onboard), (len(model.reqs_onboard) / model.N * 100),
                     len(model.reqs_picking), (len(model.reqs_picking) / model.N * 100),
                     len(model.reqs_unassigned), (len(model.reqs_unassigned) / model.N * 100),
                     len(model.rejs), (len(model.rejs) / model.N * 100)))
            print('...running time of simulation: %.02f seconds (last interval:%.02f)'
                  % ((time.time() - stime), (time.time() - estime)))
            print()

    print('End of this simulation.')
    # if IS_DEBUG:
    if True:
        if DISPATCHER == 'OSP':
            print('...Saving analysis animation data...')
            model.dispatcher.analysis.save_analysis_data()

    # end time
    etime = time.time()
    model.end_time = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M')
    # run time of this simulation
    model.time_of_run = str(datetime.timedelta(seconds=int(etime - stime)))
    model.avg_time_of_run = round((etime - stime) / T_TOTAL * INT_ASSIGN, 2)

    # generate, show and save the animation of this simulation
    if IS_ANIMATION:
        print('...Outputing simulation video...')
        anime = anim(frames_vehs)
        # plt.show()

    # output the simulation results and save data
    if IS_ANALYSIS:
        print('...Outputing analysis results...')
        print_results(model)
