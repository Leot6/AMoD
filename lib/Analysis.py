"""
utility functions are found here
"""

import csv
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import animation

from lib.Configure import T_WARM_UP, T_STUDY, DMD_VOL, DMD_STR, DMD_SST, FLEET_SIZE, MAX_WAIT, MAX_DELAY, \
    RIDESHARING_SIZE, MET_REBL, INT_ASSIGN, Olng, Olat, Dlng, Dlat, MAP_WIDTH, MAP_HEIGHT, MODEE, \
    IS_STOCHASTIC, IS_STOCHASTIC_CONSIDERED


# print and save results
def print_results(model, runtime, mean_runtime, end_time):
    count_reqs = 0
    count_served = 0
    count_serving = 0
    count_wait_viol = 0
    count_arri_viol = 0
    wait_time = 0.0
    in_veh_time = 0.0
    in_veh_delay = 0.0
    detour_factor = 0.0
    wait_viol_time = 0.0
    arri_viol_time = 0.0

    # analyze requests whose earliest pickup time is within the period of study
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            count_reqs += 1
            if not np.isclose(req.Tp, -1.0):
                count_serving += 1
                if req.Tp > req.Clp_backup:
                    count_wait_viol += 1
                    wait_viol_time += req.Tp - req.Clp_backup
                # count as 'served' only when the request is complete, i.e. the dropoff time is not -1
                if not np.isclose(req.Td, -1.0):
                    count_serving -= 1
                    count_served += 1
                    wait_time += req.Tp - req.Cep
                    in_veh_time += req.Td - req.Tp
                    in_veh_delay += req.Td - req.Tp - req.Ts
                    detour_factor += req.D
                    if req.Td > req.Cld:
                        count_arri_viol += 1
                        arri_viol_time += req.Td - req.Cld
    if not count_served == 0:
        wait_time /= count_served
        in_veh_time /= count_served
        in_veh_delay /= count_served
        detour_factor /= count_served
    if not count_wait_viol == 0:
        wait_viol_time /= count_wait_viol
    if not count_arri_viol == 0:
        arri_viol_time /= count_arri_viol

    # service rate
    served_rate = 0.0
    serving_rate = 0.0
    total_service_rate = 0.0
    wait_viol_rate = 0.0
    arri_viol_rate = 0.0
    if not count_reqs == 0:
        served_rate = round(100.0 * count_served / count_reqs, 2)
        serving_rate = round(100.0 * count_serving / count_reqs, 2)
        count_service = count_served + count_serving + len(model.reqs_picking)
        total_service_rate = round(100 * count_service / count_reqs, 2)
        wait_viol_rate = round(100 * count_wait_viol / (count_served + count_serving), 2)
        arri_viol_rate = round(100 * count_arri_viol / count_served, 2)

    # vehicle performance
    veh_service_dist = 0.0
    veh_service_time = 0.0
    veh_rebl_dist = 0.0
    veh_rebl_time = 0.0
    veh_load_by_dist = 0.0
    veh_load_by_time = 0.0
    for veh in model.vehs:
        veh_service_dist += veh.Ds
        veh_service_time += veh.Ts
        veh_rebl_dist += veh.Dr
        veh_rebl_time += veh.Tr
        if not veh.Ds + veh.Dr == 0:
            veh_load_by_dist += veh.Ld / (veh.Ds + veh.Dr)
        veh_load_by_time += veh.Lt / T_STUDY
    veh_service_dist /= model.V
    veh_service_time /= model.V
    veh_service_time_percent = 100.0 * veh_service_time / T_STUDY
    veh_rebl_dist /= model.V
    veh_rebl_time /= model.V
    veh_rebl_time_percent = 100.0 * veh_rebl_time / T_STUDY
    veh_load_by_dist /= model.V
    veh_load_by_time /= model.V

    print('*' * 80)
    print('scenario: %s' % (DMD_STR))
    print('simulation ends at %s, runtime time: %s, average: %d' % (end_time, runtime, mean_runtime))
    print('system settings:')
    print('  - from %s to %s, with %d intervals'
          % (DMD_SST, DMD_SST+datetime.timedelta(seconds=model.T), model.T/INT_ASSIGN))
    print('  - fleet size: %d; capacity: %d; ride-sharing computational size: %d'
          % (model.V, model.K, RIDESHARING_SIZE))
    print('  - demand value:%.02f, max waiting time: %d; max delay: %d' % (DMD_VOL, MAX_WAIT, MAX_DELAY))
    print('  - assignment mode: %s, ebalancing method: %s, interval: %.1f s' % (MODEE, MET_REBL, INT_ASSIGN))
    print('  - stochastic travel time: %s, stochastic planning: %s' % (IS_STOCHASTIC, IS_STOCHASTIC_CONSIDERED))
    print('simulation results:')
    print('  - requests (%d):' % count_reqs)
    print('    + served rate: %.2f%% (%d), serving rate: %.2f%% (%d), total service rate: %.2f%% (%d)'
          % (served_rate, count_served, serving_rate, count_serving, total_service_rate, count_service))
    print('    + waiting time: %.2f s, in-vehicle travel delay: %.2f s' % (wait_time, in_veh_delay))
    print('    + in-vehicle travel time: %.2f s, detour factor: %.2f' % (in_veh_time, detour_factor))
    print('    + waiting time violation rate: %.2f%% (%d/%d), average exceeding: %.2f s'
          % (wait_viol_rate, count_wait_viol, (count_served + count_serving), wait_viol_time))
    print('    + travel delay violation rate: %.2f%% (%d/%d), average exceeding: %.2f s'
          % (arri_viol_rate, count_arri_viol, count_served, arri_viol_time))
    print('  - vehicles:')
    print('    + vehicle average load: %.2f (distance weighted), %.2f (time weighted)'
          % (veh_load_by_dist, veh_load_by_time))
    print('    + vehicle service distance travelled: %.1f m' % veh_service_dist)
    print('    + vehicle service time travelled: %.1f s' % veh_service_time)
    print('    + vehicle service time percentage: %.1f%%' % veh_service_time_percent)
    print('    + vehicle rebalancing distance travelled: %.1f m' % veh_rebl_dist)
    print('    + vehicle rebalancing time travelled: %.1f s' % veh_rebl_time)
    print('    + vehicle rebalancing time percentage: %.1f%%' % veh_rebl_time_percent)
    print('*' * 80)

    # write and save the result analysis
    f = open('output/results.csv', 'a')
    writer = csv.writer(f)
    # writer.writerow(['scenario', 'demand starts', 'demand ends', 'demand number',
    #                  'fleet size', 'capacity',  'max wait (s)', 'max wait (s)', 'method', 'rebalancing', 'interval (s)',
    #                  'total service rate', 'served rate (finished)', 'serving rate (in-car)',
    #                  'mean waiting', 'mean in-car delay', 'mean detour', 'mean car load (dist)', 'mean car load (time)',
    #                  'simulation starts', 'simulation ends', 'run time', 'mean run time', 'remarks'])
    row = [DMD_STR, DMD_SST, DMD_SST+datetime.timedelta(seconds=model.T), str(count_reqs)+' ('+str(DMD_VOL*100)+'%)',
           model.V, str(model.K)+' ('+str(RIDESHARING_SIZE)+')', MAX_WAIT, MAX_DELAY, MODEE, MET_REBL, INT_ASSIGN,
           str(total_service_rate)+'% ('+str(count_service)+')', str(served_rate)+'% (' + str(count_served)+')',
           str(serving_rate) + '% (' + str(count_serving) + ')', round(wait_time, 2),
           round(in_veh_delay, 2), round(detour_factor, 2), round(veh_load_by_dist, 2), round(veh_load_by_time, 2),
           model.start_time, end_time, runtime, mean_runtime, None]
    writer.writerow(row)
    f.close()

    # # write and save data of all requests
    # f = open('output/requests.csv', 'w')
    # writer = csv.writer(f)
    # writer.writerow(['id', 'olng', 'olat', 'dlng', 'dlat', 'Ts', 'OnD', 'Tr', 'Cep', 'Tp', 'Td', 'WT', 'VT', 'D'])
    # for req in model.reqs:
    #     if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
    #         row = [req.id, req.olng, req.olat, req.dlng, req.dlat, req.Ts, req.Tr, req.Cep, req.Tp, req.Td,
    #                req.Tp - req.Cep if req.Tp >= 0 else -1, req.Td - req.Tp if req.Td >= 0 else -1, req.D]
    #         writer.writerow(row)
    # f.close()


# animation
def anim(frames):
    def init():
        for i in range(len(vehs)):
            vehs[i].set_data([frames[0][i].lng], [frames[0][i].lat])
            r1x = []
            r1y = []
            r2x = []
            r2y = []
            r3x = []
            r3y = []
            count = frames[0][i].n
            for leg in frames[0][i].route:
                if leg.pod == 0:
                    for step in leg.steps:
                        geo = np.transpose(step.geo)
                        r3x.extend(geo[0])
                        r3y.extend(geo[1])
                    assert len(frames[0][i].route) == 1
                    continue
                if count == 0:
                    for step in leg.steps:
                        geo = np.transpose(step.geo)
                        r1x.extend(geo[0])
                        r1y.extend(geo[1])
                else:
                    for step in leg.steps:
                        geo = np.transpose(step.geo)
                        r2x.extend(geo[0])
                        r2y.extend(geo[1])
                count += leg.pod
            if i == 1 or i == int(FLEET_SIZE * 2 / 10) or i == int(FLEET_SIZE * 3 / 10):
                routes1[i].set_data(r1x, r1y)
                routes2[i].set_data(r2x, r2y)
                routes3[i].set_data(r3x, r3y)
            # routes1[i].set_data(r1x, r1y)
            # routes2[i].set_data(r2x, r2y)
            # routes3[i].set_data(r3x, r3y)
        return vehs, routes1, routes2, routes3

    def animate(n):
        for i in range(len(vehs)):
            vehs[i].set_data([frames[n][i].lng], [frames[n][i].lat])
            r1x = []
            r1y = []
            r2x = []
            r2y = []
            r3x = []
            r3y = []
            count = frames[n][i].n
            for leg in frames[n][i].route:
                if leg.pod == 0:
                    for step in leg.steps:
                        geo = np.transpose(step.geo)
                        r3x.extend(geo[0])
                        r3y.extend(geo[1])
                    # if len(frames[n][i].route) != 1:
                    #     print(len(frames[n][i].route))
                    #     print((leg.rid, leg.pod, leg.tnid) for leg in frames[n][i].route)
                    # assert len(frames[n][i].route) == 1
                    continue
                if count == 0:
                    for step in leg.steps:
                        geo = np.transpose(step.geo)
                        r1x.extend(geo[0])
                        r1y.extend(geo[1])
                else:
                    for step in leg.steps:
                        geo = np.transpose(step.geo)
                        r2x.extend(geo[0])
                        r2y.extend(geo[1])
                # count += leg.pod
                count += 1

            if i == 1 or i == int(FLEET_SIZE * 2 / 10) or i == int(FLEET_SIZE * 3 / 10):
                routes1[i].set_data(r1x, r1y)
                routes2[i].set_data(r2x, r2y)
                routes3[i].set_data(r3x, r3y)
            # routes1[i].set_data(r1x, r1y)
            # routes2[i].set_data(r2x, r2y)
            # routes3[i].set_data(r3x, r3y)

        return vehs, routes1, routes2, routes3

    fig = plt.figure(figsize=(MAP_WIDTH, MAP_HEIGHT))
    plt.xlim((Olng, Dlng))
    plt.ylim((Olat, Dlat))
    img = mpimg.imread('map.png')
    plt.imshow(img, extent=[Olng, Dlng, Olat, Dlat], aspect=(Dlng - Olng) / (Dlat - Olat) * MAP_HEIGHT / MAP_WIDTH)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    vehs = []
    routes1 = []
    routes2 = []
    routes3 = []
    for v in frames[0]:
        color = '0.50'
        size = 7
        if v.id == 1:
            color = '#6DDCFD'
        elif v.id == int(FLEET_SIZE*2/10):
            color = '#A89BFA'
        elif v.id == int(FLEET_SIZE*3/10):
            color = '#1EFA35'
        # elif v.id == int(FLEET_SIZE*4/10):
        #     color = '#FF5733'
        # elif v.id == int(FLEET_SIZE*5/10):
        #     color = '#FAD91E'
        # elif v.id == int(FLEET_SIZE*6/10):
        #     color = '#EE9BFA'
        # elif v.id == int(FLEET_SIZE*7/10):
        #     color = '#F3FFCA'
        # elif v.id == int(FLEET_SIZE*8/10):
        #     color = '#9BFAC6'
        # elif v.id == int(FLEET_SIZE*9/10):
        #     color = '#FACC9B'
        # elif v.id == FLEET_SIZE - 1:
        #     color = '#9BFAF3'
        else:
            size = 3
        vehs.append(plt.plot([], [], color=color, marker='o', markersize=size, alpha=1)[0])
        routes1.append(plt.plot([], [], linestyle='--', color=color, alpha=0.3)[0])
        routes2.append(plt.plot([], [], linestyle='-', color=color, alpha=0.3)[0])
        routes3.append(plt.plot([], [], linestyle=':', color=color, alpha=0.2)[0])
    anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(frames), interval=100)
    return anime
