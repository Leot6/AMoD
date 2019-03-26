"""
utility functions are found here
"""

import csv
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import animation

from lib.Configure import T_WARM_UP, T_STUDY, T_COOL_DOWN, DMD_STR, FLEET_SIZE, \
    MET_ASSIGN, MET_REBL, INT_ASSIGN, INT_REBL, Olng, Olat, Dlng, Dlat, MAP_WIDTH, MAP_HEIGHT


# print and save results
def print_results(model, runtime):
    count_reqs = 0
    count_served = 0
    wait_time = 0.0
    in_veh_time = 0.0
    detour_factor = 0.0

    # analyze requests whose earliest pickup time is within the period of study
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            count_reqs += 1
            # count as 'served' only when the request is complete, i.e. the dropoff time is not -1
            if not np.isclose(req.Td, -1.0):
                count_served += 1
                wait_time += (req.Tp - req.Cep)
                in_veh_time += (req.Td - req.Tp)
                detour_factor += req.D
    if not count_served == 0:
        in_veh_time /= count_served
        detour_factor /= count_served
        wait_time /= count_served

    # service rate
    service_rate = 0.0
    if not count_reqs == 0:
        service_rate = 100.0 * count_served / count_reqs

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
    print('simulation starts at %s, runtime time: %d s' % (datetime.datetime.now().strftime('%Y-%m-%d_%H:%M'), runtime))
    print('system settings:')
    print('  - period of study: %d s, with warm-up %d s, cool-down %d s' % (T_STUDY, T_WARM_UP, T_COOL_DOWN))
    print('  - fleet size: %d; capacity: %d' % (model.V, model.K))
    print('  - demand Rate: %.1f trips/h' % (model.D))
    print('  - assignment method: %s, interval: %.1f s' % (MET_ASSIGN, INT_ASSIGN))
    print('  - rebalancing method: %s, interval: %.1f s' % (MET_REBL, INT_REBL))
    print('simulation results:')
    print('  - requests:')
    print(
        '    + service rate: %.1f%% (%d/%d), , wait time: %.1f s' % (service_rate, count_served, count_reqs, wait_time))
    print('    + in-vehicle travel time: %.1f s' % (in_veh_time))
    print('    + detour factor: %.2f' % (detour_factor))
    print('  - vehicles:')
    print('    + vehicle service distance travelled: %.1f m' % (veh_service_dist))
    print('    + vehicle service time travelled: %.1f s' % (veh_service_time))
    print('    + vehicle service time percentage: %.1f%%' % (veh_service_time_percent))
    print('    + vehicle rebalancing distance travelled: %.1f m' % (veh_rebl_dist))
    print('    + vehicle rebalancing time travelled: %.1f s' % (veh_rebl_time))
    print('    + vehicle rebalancing time percentage: %.1f%%' % (veh_rebl_time_percent))
    print(
        '    + vehicle average load: %.2f (distance weighted), %.2f (time weighted)' % (
            veh_load_by_dist, veh_load_by_time))
    print('*' * 80)

    # write and save the result analysis
    f = open('output/results.csv', 'a')
    writer = csv.writer(f)
    row = [DMD_STR, MET_ASSIGN, MET_REBL, T_STUDY, model.V, model.K, model.D,
           service_rate, count_served, count_reqs, wait_time,
           in_veh_time, detour_factor, veh_service_dist, veh_service_time, veh_service_time_percent,
           veh_rebl_dist, veh_rebl_time, veh_rebl_time_percent, veh_load_by_dist, veh_load_by_time, None]
    writer.writerow(row)
    f.close()

    # write and save data of all requests
    f = open('output/requests.csv', 'w')
    writer = csv.writer(f)
    writer.writerow(['id', 'olng', 'olat', 'dlng', 'dlat', 'Ts', 'OnD', 'Tr', 'Cep', 'Tp', 'Td', 'WT', 'VT', 'D'])
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            row = [req.id, req.olng, req.olat, req.dlng, req.dlat, req.Ts, req.Tr, req.Cep, req.Tp, req.Td,
                   req.Tp - req.Cep if req.Tp >= 0 else -1, req.Td - req.Tp if req.Td >= 0 else -1, req.D]
            writer.writerow(row)
    f.close()


# animation
def anim(frames, frames_reqs):
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
            routes1[i].set_data(r1x, r1y)
            routes2[i].set_data(r2x, r2y)
            routes3[i].set_data(r3x, r3y)
        # for i in range(len(frames_reqs[0])):
        #     olng = frames_reqs[0][i].olng
        #     olat = frames_reqs[0][i].olat
        #     dlng = frames_reqs[0][i].dlng
        #     dlat = frames_reqs[0][i].dlat
        #     reqs_o[i].set_data([olng], [olat])
        #     reqs_d[i].set_data([dlng], [dlat])
        #     reqs[i].set_data([olng, dlng], [olat, dlat])
        return vehs, routes1, routes2, routes3, reqs_o, reqs_d

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
                    assert len(frames[n][i].route) == 1
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
            routes1[i].set_data(r1x, r1y)
            routes2[i].set_data(r2x, r2y)
            routes3[i].set_data(r3x, r3y)
        # reqs_o = []
        # reqs_d = []
        # for i in range(len(frames_reqs[n])):
        #     color = '0.50'
        #     if not frames_reqs[n][i].served:
        #         color = '#FF0000'
        #     reqs_o.append(plt.plot([], [], color=color, marker='+', markersize=8, alpha=2)[0])
        #     reqs_d.append(plt.plot([], [], color=color, marker='x', markersize=8, alpha=2)[0])
        #     reqs_o[i].set_data([frames_reqs[n][i].olng], [frames_reqs[n][i].olat])
        #     reqs_d[i].set_data([frames_reqs[n][i].dlng], [frames_reqs[n][i].dlat])
        return vehs, routes1, routes2, routes3, reqs_o, reqs_d

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
    reqs_o = []
    reqs_d = []
    reqs = []
    for v in frames[0]:
        color = '0.50'
        size = 7
        if v.id == 1:
            color = '#FF5733'
        elif v.id == int(FLEET_SIZE*2/10):
            color = '#FAD91E'
        elif v.id == int(FLEET_SIZE*3/10):
            color = '#1EFA35'
        elif v.id == int(FLEET_SIZE*4/10):
            color = '#6DDCFD'
        elif v.id == int(FLEET_SIZE*5/10):
            color = '#A89BFA'
        elif v.id == int(FLEET_SIZE*6/10):
            color = '#EE9BFA'
        elif v.id == int(FLEET_SIZE*7/10):
            color = '#F3FFCA'
        elif v.id == int(FLEET_SIZE*8/10):
            color = '#9BFAC6'
        elif v.id == int(FLEET_SIZE*9/10):
            color = '#FACC9B'
        elif v.id == FLEET_SIZE - 1:
            color = '#9BFAF3'
        else:
            size = 3
        vehs.append(plt.plot([], [], color=color, marker='o', markersize=size, alpha=1)[0])
        routes1.append(plt.plot([], [], linestyle='--', color=color, alpha=0.3)[0])
        routes2.append(plt.plot([], [], linestyle='-', color=color, alpha=0.3)[0])
        routes3.append(plt.plot([], [], linestyle=':', color=color, alpha=0.2)[0])
    # for req in frames_reqs[0]:
    #     color = '0.50'
    #     if not req.served:
    #         color = '#FF0000'
    #     reqs_o.append(plt.plot([], [], color=color, marker='+', markersize=8, alpha=2)[0])
    #     reqs_d.append(plt.plot([], [], color=color, marker='x', markersize=8, alpha=2)[0])
    #     reqs.append(plt.plot([], [], linestyle=':', color=color, alpha=0.4)[0])
    anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(frames), interval=100)
    return anime
