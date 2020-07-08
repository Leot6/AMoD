"""
utility functions are found here
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import animation

from lib.simulator.config import *


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
        elif v.id == int(FLEET_SIZE * 2 / 10):
            color = '#A89BFA'
        elif v.id == int(FLEET_SIZE * 3 / 10):
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
