"""
defination of vehicles for the AMoD system
"""

import copy
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

from lib.Configure import T_WARM_UP, T_STUDY, COEF_WAIT, COEF_INVEH, RIDESHARING_SIZE, MODEE
from lib.Route import Step, Leg, get_routing_from_networkx, find_nearest_node


class Veh(object):
    """
    Veh is a class for vehicles
    Attributes:
        id: sequential unique id
        idle: is idle
        rebl: is rebalancing
        T: system time at current state
        lat: current lngitude
        lng: current longtitude
        nid: current nearest node id in network
        step_to_nid: step from current location to the nearest node in network
        t_to_nid = 0: travel time from current location to the nearest node in network
        tlat: target (end of route) lngitude
        tlng: target (end of route) longtitude
        K: capacity
        n: number of passengers on board
        route: a list of legs
        t: total duration of the route
        d: total distance of the route
        c: total cost (generalized time) of the passegners
        Ds: accumulated service distance traveled
        Ts: accumulated service time traveled
        Dr: accumulated rebalancing distance traveled
        Tr: accumulated rebalancing time traveled
        Lt: accumulated load, weighed by service time
        Ld: accumulated load, weighed by service distance
        VTtable = stored feasible trips from last interval plan
        onboard_reqs = requests currently on board
        onboard_rid = id of requests currently on board
        new_pick_rid = id of requests picked up in this interval
        new_drop_rid = id of requests dropped off in this interval
    """

    def __init__(self, id, lng, lat, K=4, T=0.0):
        self.id = id
        self.idle = True
        self.rebl = False
        self.T = T
        self.lng = lng
        self.lat = lat
        self.nid = find_nearest_node(lng, lat)
        self.step_to_nid = None
        self.t_to_nid = 0
        self.tlng = self.lng
        self.tlat = self.lat
        self.tnid = self.nid
        self.K = K
        self.n = 0
        self.route = deque([])
        self.t = 0.0
        self.d = 0.0
        self.c = 0.0
        self.Ds = 0.0
        self.Ts = 0.0
        self.Dr = 0.0
        self.Tr = 0.0
        self.Lt = 0.0
        self.Ld = 0.0
        self.VTtable = [[] for i in range(RIDESHARING_SIZE*2)]
        self.onboard_reqs = set()
        self.onboard_rid = []
        self.new_pick_rid = []
        self.new_drop_rid = []

        # debug code starts
        self.route_record = []
        # debug code ends

    # update the vehicle location as well as the route after moving to time T
    def move_to_time(self, T):
        dT = T - self.T
        if dT <= 0:
            return []
        self.step_to_nid = None
        self.t_to_nid = 0

        # # debug
        # print('total  time', round(self.Ts + self.t, 2))
        # print('remain time', round(self.t, 2))
        # print('t2nid before move', round(self.t_to_nid, 2))

        # # debug
        # if self.id == 91:
        #     move_d = 0
        #     print(' move 111', move_d)

        # done is a list of finished legs
        done = []
        while dT > 0 and len(self.route) > 0:

            # # debug
            # if self.id == 91:
            #     print(' move 222')

            leg = self.route[0]
            # if the first leg could be finished by then
            if leg.t < dT:

                # # debug
                # if self.id == 91:
                #     move_d -= leg.d
                #     print(' move 333', move_d)

                dT -= leg.t
                self.T += leg.t
                if T_WARM_UP <= self.T <= T_WARM_UP + T_STUDY:
                    self.Ts += leg.t if leg.rid != -1 else 0
                    self.Ds += leg.d if leg.rid != -1 else 0
                    self.Tr += leg.t if leg.rid == -1 else 0
                    self.Dr += leg.d if leg.rid == -1 else 0
                    self.Lt += leg.t * self.n if leg.rid != -1 else 0
                    self.Ld += leg.d * self.n if leg.rid != -1 else 0
                self.jump_to_location(leg.tlng, leg.tlat, leg.tnid)
                self.n += leg.pod
                if leg.rid != -2:
                    done.append((leg.rid, leg.pod, self.T))
                    # debug code starts
                    self.route_record.append((leg.rid, leg.pod))
                    # debug code ends

                self.pop_leg()
            else:

                # # debug
                # if self.id == 91:
                #     print(' move 444')

                while dT > 0 and len(leg.steps) > 0:
                    step = leg.steps[0]
                    # if the first leg could not be finished, but the first step of the leg could be finished by then
                    if step.t < dT:

                        # # debug
                        # if self.id == 91:
                        #     move_d -= step.d
                        #     print(' move 555', move_d, step.d)

                        dT -= step.t
                        self.T += step.t
                        if T_WARM_UP <= self.T <= T_WARM_UP + T_STUDY:
                            self.Ts += step.t if leg.rid != -1 else 0
                            self.Ds += step.d if leg.rid != -1 else 0
                            self.Tr += step.t if leg.rid == -1 else 0
                            self.Dr += step.d if leg.rid == -1 else 0
                            self.Lt += step.t * self.n if leg.rid != -1 else 0
                            self.Ld += step.d * self.n if leg.rid != -1 else 0
                        self.jump_to_location(step.geo[1][0], step.geo[1][1], step.nid[1])
                        self.pop_step()

                        if len(leg.steps) == 0:

                            # # debug
                            # if self.id == 91:
                            #     moove_d -= leg.d
                            #     print(' move 666', move_d, step.d)

                            # corner case: leg.t extremely small, but still larger than dT
                            # this is due to the limited precision of the floating point numbers
                            self.jump_to_location(leg.tlng, leg.tlat, leg.tnid)
                            self.n += leg.pod
                            if leg.rid != -2:
                                done.append((leg.rid, leg.pod, self.T))
                                # debug code starts
                                self.route_record.append((leg.rid, leg.pod))
                                # debug code ends

                            self.pop_leg()
                            break
                    # the vehicle has to stop somewhere within the step
                    else:

                        # # debug
                        # if self.id == 91:
                        #     move_d -= dT / step.t * step.d
                        #     print(' move 777', move_d, step.d)

                        pct = dT / step.t
                        if T_WARM_UP <= self.T <= T_WARM_UP + T_STUDY:
                            self.Ts += dT if leg.rid != -1 else 0
                            self.Ds += step.d * pct if leg.rid != -1 else 0
                            self.Tr += dT if leg.rid == -1 else 0
                            self.Dr += step.d * pct if leg.rid == -1 else 0
                            self.Lt += dT * self.n if leg.rid != -1 else 0
                            self.Ld += step.d * pct * self.n if leg.rid != -1 else 0
                        # find the exact location the vehicle stops and update the step
                        self.cut_step(pct)
                        self.jump_to_location(step.geo[0][0], step.geo[0][1], step.nid[0])
                        self.T = T

                        # # debug
                        # print('total  time', round(self.Ts + self.t, 2))
                        # print('remain time', round(self.t, 2))
                        # print('t2nid after cut', round(self.t_to_nid, 2))

                        return done
        assert dT > 0 or np.isclose(dT, 0.0)
        assert self.T < T or np.isclose(self.T, T)
        assert len(self.route) == 0
        assert self.n == 0
        assert np.isclose(self.d, 0.0)
        assert np.isclose(self.t, 0.0)
        self.T = T
        self.d = 0.0
        self.t = 0.0
        self.idle = True
        return done

    # pop the first leg from the route list
    def pop_leg(self):
        leg = self.route.popleft()
        self.d -= leg.d
        self.t -= leg.t

    # pop the first step from the first leg
    def pop_step(self):
        step = self.route[0].steps.popleft()
        self.t -= step.t
        self.d -= step.d
        self.route[0].t -= step.t
        self.route[0].d -= step.d

    # find the exact location the vehicle stops and update the step
    def cut_step(self, pct):
        step = self.route[0].steps[0]
        step.geo[0][0] += pct * (step.geo[1][0] - step.geo[0][0])
        step.geo[0][1] += pct * (step.geo[1][1] - step.geo[0][1])
        step.nid[0] = step.nid[1]
        self.t_to_nid = step.t * (1 - pct)
        self.t -= step.t * pct
        self.d -= step.d * pct
        self.route[0].t -= step.t * pct
        self.route[0].d -= step.d * pct
        self.route[0].steps[0].t -= step.t * pct
        self.route[0].steps[0].d -= step.d * pct
        assert self.route[0].steps[0].nid[0] == self.route[0].steps[0].nid[1]
        self.step_to_nid = copy.deepcopy(self.route[0].steps[0])

    def jump_to_location(self, lng, lat, nid):
        self.lng = lng
        self.lat = lat
        self.nid = nid

    # build the route of the vehicle based on a series of quadruples (rid, pod, tlng, tlat)
    # update t, d, c, idle, rebl accordingly
    # rid, pod, tlng, tlat are defined as in class Leg
    def build_route(self, schedule, reqs=None, T=None):
        self.clear_route()
        # if the route is null, vehicle is idle
        if len(schedule) == 0:
            self.idle = True
            self.rebl = False
            self.t = 0.0
            self.d = 0.0
            self.c = 0.0
            self.step_to_nid = None
            self.t_to_nid = 0
            return
        else:
            if self.step_to_nid:
                rid = -2
                pod = 0
                tlng = self.step_to_nid.geo[1][0]
                tlat = self.step_to_nid.geo[1][1]
                tnid = self.step_to_nid.nid[1]
                ddl = self.T + self.step_to_nid.t
                duration = self.step_to_nid.t
                distance = self.step_to_nid.d
                steps = [copy.deepcopy(self.step_to_nid), Step(0, 0, [[tlng, tlat], [tlng, tlat]], [tnid, tnid])]
                leg = Leg(rid, pod, tlng, tlat, tnid, ddl, duration, distance, steps)
                # the last step of a leg is always of length 2,
                # consisting of 2 identical points as a flag of the end of the leg
                assert len(leg.steps[-1].geo) == 2
                assert leg.steps[-1].geo[0] == leg.steps[-1].geo[1]
                self.route.append(leg)
                self.tlng = leg.steps[-1].geo[1][0]
                self.tlat = leg.steps[-1].geo[1][1]
                self.tnid = leg.steps[-1].nid[1]
                self.d += leg.d
                self.t += leg.t
            for (rid, pod, tlng, tlat, tnid, ddl) in schedule:
                self.add_leg_from_networkx(rid, pod, tlng, tlat, tnid, ddl, reqs, T)
            # if self.step_to_nid:
            #     self.d += self.step_to_nid.d
            #     self.t += self.step_to_nid.t
        # if rid is -1, vehicle is rebalancing
        if self.route[0].rid == -1:
            self.idle = True
            self.rebl = True
            self.c = 0.0
        # else, the vehicle is in service to pick-up or drop-off
        else:
            # verify the route with capacity constraint and get the cost of the route
            c = 0.0
            self.idle = False
            self.rebl = False
            t = 0.0
            n = self.n
            for leg in self.route:
                t += leg.t
                c += n * leg.t * COEF_INVEH
                n += leg.pod
                c += t * COEF_WAIT if leg.pod == 1 else 0

            # debug code starts
            if n != 0:
                schedule = [(leg.rid, leg.pod) for leg in self.route]
                print('')
                print('error n!=0, veh', self.id, ', passengers', self.n)
                print('route record', self.route_record)
                print('schedule', schedule)
                print('rid on board', self.onboard_rid, ', new pick', self.new_pick_rid, ', new drop', self.new_drop_rid)
                print('')
            # debug code ends

            assert n == 0
            self.c = c
        return

    # add a leg based on (rid, pod, tlng, tlat, tnid, ddl)
    def add_leg_from_networkx(self, rid, pod, tlng, tlat, tnid, ddl, reqs, T):
        duration, distance, segments = get_routing_from_networkx(self.tnid, tnid)
        steps = [Step(s[0], s[1], s[2], s[3]) for s in segments]
        leg = Leg(rid, pod, tlng, tlat, tnid, ddl, duration, distance, steps)
        # the last step of a leg is always of length 2,
        # consisting of 2 identical points as a flag of the end of the leg
        assert len(leg.steps[-1].geo) == 2
        assert leg.steps[-1].geo[0] == leg.steps[-1].geo[1]
        # if pickup and the vehicle arrives in advance, add an extra wait
        if pod == 1:
            if T + self.t + leg.t < reqs[rid].Cep:
                wait = reqs[rid].Cep - (T + self.t + leg.t)
                leg.steps[-1].t += wait
                leg.t += wait
        self.route.append(leg)
        self.tlng = leg.steps[-1].geo[1][0]
        self.tlat = leg.steps[-1].geo[1][1]
        self.tnid = leg.steps[-1].nid[1]
        self.d += leg.d
        self.t += leg.t

    # remove the current route
    def clear_route(self):
        self.route.clear()
        self.d = 0.0
        self.t = 0.0
        self.c = 0.0
        self.tlng = self.lng
        self.tlat = self.lat
        self.tnid = self.nid

    # visualize
    def draw(self):
        color = '0.50'
        if self.id == 0:
            color = 'red'
        elif self.id == 1:
            color = 'orange'
        elif self.id == 2:
            color = 'yellow'
        elif self.id == 3:
            color = 'green'
        elif self.id == 4:
            color = 'blue'
        plt.plot(self.lng, self.lat, color=color, marker='o', markersize=4, alpha=0.5)
        count = 0
        for leg in self.route:
            count += 1
            plt.plot(leg.tlng, leg.tlat, color=color,
                     marker='s' if leg.pod == 1 else 'x' if leg.pod == -1 else None, markersize=3, alpha=0.5)
            for step in leg.steps:
                geo = np.transpose(step.geo)
                plt.plot(geo[0], geo[1], color=color, linestyle='-' if count <= 1 else '--', alpha=0.5)

    def __str__(self):
        str = 'veh %d at (%.7f, %.7f) when t = %.3f; %s; occupancy = %d/%d' % (
            self.id, self.lng, self.lat, self.T, 'rebalancing' if self.rebl else 'idle' if self.idle else 'in service',
            self.n, self.K)
        str += '\n  service dist/time: %.1f, %.1f; rebalancing dist/time: %.1f, %.1f' % (
            self.Ds, self.Ts, self.Dr, self.Tr)
        str += '\n  has %d leg(s), dist = %.1f, dura = %.1f，cost = %.1f' % (
            len(self.route), self.d, self.t, self.c)
        for leg in self.route:
            str += '\n    %s req %d at (%.7f, %.7f), dist = %.1f, dura = %.1f' % (
                'pickup' if leg.pod == 1 else 'dropoff' if leg.pod == -1 else 'rebalancing',
                leg.rid, leg.tlng, leg.tlat, leg.d, leg.t)
        return str

