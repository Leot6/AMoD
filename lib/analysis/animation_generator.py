"""
utility functions are found here
"""

import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import animation

from lib.simulator.config import *
from lib.routing.routing_server import get_path_from_origin_to_dest, get_node_geo

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

veh_showing_route_step = 2
amin_frame_interval = 125


# animation
def anim(frames_vehs, frames_reqs=None, frames_edges=None, dispatcher=DISPATCHER):
    def init():
        for i in range(len(vehs)):
            if i % veh_showing_route_step == 0:
                vehs[i].set_data([frames_vehs[0][i].lng], [frames_vehs[0][i].lat])
            r1x = []
            r1y = []
            for leg in frames_vehs[0][i].route:
                for step in leg.steps:
                    geo = np.transpose(step.geo)
                    r1x.extend(geo[0])
                    r1y.extend(geo[1])
            r2x = []
            r2y = []
            for sche in frames_vehs[0][i].candidate_sches:
                geo_path = build_geo_path_from_sche(frames_vehs[0][i], sche)
                for geo in geo_path:
                    geo = np.transpose(geo)
                    r2x.extend(geo[0])
                    r2y.extend(geo[1])

            if i % veh_showing_route_step == 0:
                routes1[i].set_data(r1x, r1y)
                # routes2[i].set_data(r2x, r2y)
        text.set_text('')
        return vehs, routes1, routes2, text

    def animate(n):
        for i in range(len(vehs)):
            if i % veh_showing_route_step == 0:
                vehs[i].set_data([frames_vehs[n][i].lng], [frames_vehs[n][i].lat])
            r1x = []
            r1y = []
            for leg in frames_vehs[n][i].route:
                for step in leg.steps:
                    geo = np.transpose(step.geo)
                    r1x.extend(geo[0])
                    r1y.extend(geo[1])
            r2x = []
            r2y = []
            for sche in frames_vehs[n][i].candidate_sches:
                geo_path = build_geo_path_from_sche(frames_vehs[n][i], sche)
                for geo in geo_path:
                    geo = np.transpose(geo)
                    r2x.extend(geo[0])
                    r2y.extend(geo[1])

            if i % veh_showing_route_step == 0:
                routes1[i].set_data(r1x, r1y)
                # routes2[i].set_data(r2x, r2y)

        time_in_sec = 68430 + n * 30
        m, s = divmod(time_in_sec, 60)
        h, m = divmod(m, 60)
        time = "%02d:%02d:%02d" % (h, m, s)
        numreqs_numedges = ''
        if frames_reqs is not None:
            numreqs_numedges = f'Requests Submitted: {frames_reqs[n][0]} \n' \
                f'Schedules Found:    {frames_edges[n][1]} \n' \
                f'Requests Matched:   {frames_reqs[n][1]} '
        # text.set_text(f'Instance: |R|=800k, |V|=3200\n'
        #               f'Time: {time}\n'
        #               f'{numreqs_numedges}')
        return vehs, routes1, routes2, text

    fig = plt.figure(figsize=(MAP_WIDTH, MAP_HEIGHT))
    plt.xlim((Olng, Dlng))
    plt.ylim((Olat, Dlat))
    img = mpimg.imread(f'{root_path}/map.png')
    plt.imshow(img, extent=[Olng, Dlng, Olat, Dlat], aspect=(Dlng - Olng) / (Dlat - Olat) * MAP_HEIGHT / MAP_WIDTH)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    vehs = []
    routes1 = []  # veh current route
    routes2 = []  # candidate schedule route

    text = plt.text(-74.017, 40.852, '', size=30, weight='light', color='#FFFFFF', alpha=0.7)

    veh_route_color = '#FFFFFF'
    if dispatcher == 'OSP':
        veh_route_color = '#F6BB36'
    # elif dispatcher == 'RTV':
    #     veh_route_color = '#25A1FA'
    # elif dispatcher == 'SBA':
    #     veh_route_color = '#8FE37C'
    # elif dispatcher == 'GI':
    #     veh_route_color = '#FB6454'

    for v in frames_vehs[0]:
        color = veh_route_color
        size = 3
        if v.id % veh_showing_route_step == 0:
            color = veh_route_color
            size = 6
        vehs.append(plt.plot([], [], color=color, marker='o', markersize=size, alpha=1)[0])
        # routes1.append(plt.plot([], [], linestyle='-', color='#FFFFFF', alpha=0.4)[0])
        routes1.append(plt.plot([], [], linestyle='-', color=color, alpha=0.7)[0])
        routes2.append(plt.plot([], [], linestyle=':', color=color, alpha=0.8)[0])
    anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(frames_vehs), interval=amin_frame_interval)
    print('Dispatcher', dispatcher, 'num of frames', len(frames_vehs))
    print('saving animation....')
    start_time = time.time()
    anime.save(f'{root_path}/output/anim_{dispatcher}.mp4', dpi=200, fps=None, extra_args=['-vcodec', 'libx264'])
    print('...running time of encoding video : %.05f seconds' % (time.time() - start_time))
    return anime


def build_geo_path_from_sche(veh, sche):
    geo_path = []
    if veh.step_to_nid:
        assert veh.lng == veh.step_to_nid.geo[0][0]
        # add the unfinished step from last move updating
        geo_path.append(veh.step_to_nid.geo)
    current_nid = veh.nid
    for (rid, pod, tnid, ept, ddl) in sche:
        sub_path = get_path_from_origin_to_dest(current_nid, tnid)
        for i in range(len(sub_path) - 1):
            u = sub_path[i]
            v = sub_path[i + 1]
            u_geo = get_node_geo(u)
            v_geo = get_node_geo(v)
            geo_path.append([u_geo, v_geo])
    return geo_path


def anim_compare_sches_found(frames_vehs, frames_reqs=None, frames_edges=None, dispatcher='RTV'):
    def init():
        for i in range(len(vehs)):
            vehs[i].set_data([frames_vehs[0][i].lng], [frames_vehs[0][i].lat])
            r1x = []
            r1y = []
            for leg in frames_vehs[0][i].route:
                for step in leg.steps:
                    geo = np.transpose(step.geo)
                    r1x.extend(geo[0])
                    r1y.extend(geo[1])
            r2x = []
            r2y = []
            for sche in frames_vehs[0][i].candidate_sches_rtv:
                geo_path = build_geo_path_from_sche(frames_vehs[0][i], sche)
                for geo in geo_path:
                    geo = np.transpose(geo)
                    r2x.extend(geo[0])
                    r2y.extend(geo[1])

            if i % veh_showing_route_step == 0:
                routes1[i].set_data(r1x, r1y)
                routes2[i].set_data(r2x, r2y)
        text.set_text('')
        return vehs, routes1, routes2, text

    def animate(n):
        for i in range(len(vehs)):
            vehs[i].set_data([frames_vehs[n][i].lng], [frames_vehs[n][i].lat])
            r1x = []
            r1y = []
            for leg in frames_vehs[n][i].route:
                for step in leg.steps:
                    geo = np.transpose(step.geo)
                    r1x.extend(geo[0])
                    r1y.extend(geo[1])
            r2x = []
            r2y = []
            for sche in frames_vehs[n][i].candidate_sches_rtv:
                geo_path = build_geo_path_from_sche(frames_vehs[n][i], sche)
                for geo in geo_path:
                    geo = np.transpose(geo)
                    r2x.extend(geo[0])
                    r2y.extend(geo[1])

            if i % veh_showing_route_step == 0:
                routes1[i].set_data(r1x, r1y)
                routes2[i].set_data(r2x, r2y)
        time_in_sec = 68430 + n * 30
        m, s = divmod(time_in_sec, 60)
        h, m = divmod(m, 60)
        time = "%02d:%02d:%02d" % (h, m, s)
        numreqs_numedges = ''
        if frames_reqs is not None:
            numreqs_numedges = f'Requests Submitted: {frames_reqs[n][0]} \n' \
                f'Schedules Found:    {frames_edges[n][2]} \n' \
                f'Requests Matched:   {frames_reqs[n][2]} '
        text.set_text(f'Instance: |R|=800k, |V|=3200\n'
                      f'Time: {time}\n'
                      f'{numreqs_numedges}')
        return vehs, routes1, routes2, text

    fig = plt.figure(figsize=(MAP_WIDTH, MAP_HEIGHT))
    plt.xlim((Olng, Dlng))
    plt.ylim((Olat, Dlat))
    img = mpimg.imread(f'{root_path}/map.png')
    plt.imshow(img, extent=[Olng, Dlng, Olat, Dlat], aspect=(Dlng - Olng) / (Dlat - Olat) * MAP_HEIGHT / MAP_WIDTH)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    vehs = []
    routes1 = []  # veh current route
    routes2 = []  # candidate schedule route

    text = plt.text(-74.017, 40.852, '', size=30, weight='light', color='#FFFFFF', alpha=0.7)

    if dispatcher == 'OSP':
        veh_route_color = '#F6BB36'
    elif dispatcher == 'RTV':
        veh_route_color = '#25A1FA'
    elif dispatcher == 'SBA':
        veh_route_color = '#8FE37C'
    elif dispatcher == 'GI':
        veh_route_color = '#FB6454'
    for v in frames_vehs[0]:
        color = '0.50'
        size = 3
        if v.id % veh_showing_route_step == 0:
            color = veh_route_color
            size = 6
        vehs.append(plt.plot([], [], color=color, marker='o', markersize=size, alpha=1)[0])
        routes1.append(plt.plot([], [], linestyle='-', color='#FFFFFF', alpha=0.3)[0])
        routes2.append(plt.plot([], [], linestyle=':', color=color, alpha=0.8)[0])
    anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(frames_vehs), interval=amin_frame_interval)
    print('Dispatcher', dispatcher, 'num of frames', len(frames_vehs))
    print('saving animation....')
    start_time = time.time()
    anime.save(f'{root_path}/output/anim_{dispatcher}.mp4', dpi=200, fps=None, extra_args=['-vcodec', 'libx264'])
    print('...running time of encoding video : %.05f seconds' % (time.time() - start_time))
    return anime


def anim_sche(veh, trip, sches, best_sche, dispatcher=''):
    def init():
        r1x = []
        r1y = []
        for leg in veh.route:
            for step in leg.steps:
                geo = np.transpose(step.geo)
                r1x.extend(geo[0])
                r1y.extend(geo[1])
        route.set_data(r1x, r1y)
        text.set_text('')
        return route, text

    def animate(n):
        veh.build_route(sches[n])
        r1x = []
        r1y = []
        for leg in veh.route:
            for step in leg.steps:
                geo = np.transpose(step.geo)
                r1x.extend(geo[0])
                r1y.extend(geo[1])
        route.set_data(r1x, r1y)
        numsche = n + 1
        if n == len(sches) - 1:
            route_best.set_data(r1x, r1y)
            numsche = n
        text.set_text(f'Schedules \nSearched: {numsche}')

        return route, text, route_best

    sches.append(best_sche)
    fig = plt.figure(figsize=(MAP_WIDTH, MAP_HEIGHT))
    plt.xlim((Olng, Dlng))
    plt.ylim((Olat, Dlat))

    img = mpimg.imread(f'{root_path}/map.png')
    plt.imshow(img, extent=[Olng, Dlng, Olat, Dlat], aspect=(Dlng - Olng) / (Dlat - Olat) * MAP_HEIGHT / MAP_WIDTH)
    fig.subplots_adjust(left=0.00, bottom=0.00, right=1.00, top=1.00)
    [veh_lng, veh_lat] = get_node_geo(veh.nid)
    veh_plot = plt.plot(veh_lng, veh_lat, color='#FFFFFF', marker='o', markersize=7, alpha=0.7)[0]
    for req in trip:
        [olng, olat] = get_node_geo(req.onid)
        [dlng, dlat] = get_node_geo(req.dnid)
        plt.plot(olng, olat, color='#FFFFFF', marker='^', markersize=7, alpha=0.7)
        plt.plot(dlng, dlat, color='#FFFFFF', marker='v', markersize=7, alpha=0.7)
    if not veh.onboard_rids == []:
        for (rid, pod, tnid, ept, ddl) in veh.sche:
            if rid in veh.onboard_rids:
                assert pod == -1
                [dlng, dlat] = get_node_geo(tnid)
                plt.plot(dlng, dlat, color='#FFFFFF', marker='^', markersize=7, alpha=0.7)

    text = plt.text(-74.020, 40.785, '', size=25, weight='light', color='#FFFFFF', alpha=0.7)
    if dispatcher == 'OSP':
        route_color = '#F6BB36'
        interval_length = 125
        alpha_l = 0.7
    else:
        route_color = '0.5'
        interval_length = 12.5
        alpha_l = 1
    route = plt.plot([], [], linestyle='--', color=route_color, alpha=alpha_l)[0]
    route_best = plt.plot([], [], linestyle='-', color='#F6BB36', alpha=1)[0]

    anime = animation.FuncAnimation(fig, animate, init_func=init, frames=len(sches), interval=interval_length)
    print('saving animation....')
    start_time = time.time()
    # plt.show()
    anime.save(f'{root_path}/output/anim_sche{veh.id}_{dispatcher}.mp4', dpi=200, fps=None, extra_args=['-vcodec', 'libx264'])
    print('...running time of encoding video : %.05f seconds' % (time.time() - start_time))
    return anime
