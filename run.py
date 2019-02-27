
from lib.OsrmEngine import *
from lib.Analysis import *


if __name__ == "__main__":
    # path of the routing server
    exe_loc = './osrm-backend-5.21.0/build/osrm-routed'
    # path of the road network file that the routing server uses
    map_loc = './osrm-backend-5.21.0/greater-london-latest.osrm'

    # if road network is enabled, initialize the routing server
    # otherwise, use Euclidean distance
    osrm = OsrmEngine(exe_loc, map_loc)
    # osrm.start_server()

    for i in range(1):
        for ii in range(1):
            # frames record the states of the AMoD model for animation purpose
            frames = []
            frames_reqs = []
            # initialize the AMoD model
            model = Model(DMD_MAT, DMD_VOL, V=FLEET_SIZE, K=VEH_CAPACITY, assign=MET_ASSIGN, rebl=MET_REBL)
            # start time
            stime = time.time()
            # dispatch the system for T_TOTAL seconds, at the interval of INT_ASSIGN
            for T in range(0, T_TOTAL, INT_ASSIGN):
                model.dispatch_at_time(osrm, T)
                if IS_ANIMATION and T >= 30:
                    frames.append(copy.deepcopy(model.vehs))
                    frames_reqs.append(copy.deepcopy(model.queue_))
                    print("System situation: %d reqs have been received, %d have been served (%.02f%%), "
                          "%d are on board (%.02f%%), %d are being picked-up (%.02f%%), %d are rejected (%.02f%%)."
                          % (model.N, len(model.reqs_served), (len(model.reqs_served)/model.N*100),
                             len(model.reqs_serving), (len(model.reqs_serving)/model.N*100),
                             len(model.reqs_picking), (len(model.reqs_picking)/model.N*100),
                             len(model.rejs), (len(model.rejs)/model.N*100)))
                    print("")

            print("End of this simulation.")

            # end time
            etime = time.time()
            # run time of this simulation
            runtime = etime - stime

            print("...running time of assign: %.05f seconds" % runtime)

            # generate, show and save the animation of this simulation
            if IS_ANIMATION:
                print("...Outputing simulation video...")
                anime = anim(frames, frames_reqs)
                anime.save('output/anim.mp4', dpi=300, fps=None, extra_args=['-vcodec', 'libx264'])
                plt.show()

            # output the simulation results and save data
            # print_results(model, runtime)
