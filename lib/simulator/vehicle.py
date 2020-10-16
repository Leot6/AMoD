"""
definition of vehicles for the AMoD system
"""

import copy
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

from lib.simulator.config import T_WARM_UP, T_STUDY, RIDESHARING_SIZE
from lib.simulator.route import Step, Leg
from lib.routing.routing_server import build_route_from_origin_to_dest, get_node_geo


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
        step_to_nid: step from current location (when veh is on an edge) to the sink node in network
        t_to_nid: travel time from current location (when veh is on an edge) to the sink node in network
        tnid: target (end of route) node id
        K: capacity
        n: number of passengers on board
        schedule: a list of pick-up and drop-off points
        route: a list of legs
        t: total duration of the route
        d: total distance of the route
        Ds: accumulated service distance traveled
        Ts: accumulated service time traveled
        Dr: accumulated rebalancing distance traveled
        Tr: accumulated rebalancing time traveled
        Lt: accumulated load, weighed by service time
        Ld: accumulated load, weighed by service distance
        onboard_rid: id of requests currently on board
        new_pick_rid: id of requests newly picked up in current interval
        new_drop_rid: id of requests newly dropped off in current interval

    """

    def __init__(self, id, nid, lng, lat, K=4, T=0.0):
        self.id = id
        self.idle = True
        self.rebl = False
        self.T = T
        self.lng = lng
        self.lat = lat
        self.nid = nid
        self.step_to_nid = None
        self.t_to_nid = 0
        self.tnid = self.nid
        self.K = K
        self.n = 0
        self.sche = []
        self.feasible_sches = []
        self.route = deque([])
        self.t = 0.0
        self.d = 0.0
        self.Ds = 0.0
        self.Ts = 0.0
        self.Dr = 0.0
        self.Tr = 0.0
        self.Lt = 0.0
        self.Ld = 0.0
        self.picking_rids = []
        self.onboard_rids = []
        self.served_rids = []
        self.new_picked_rids = []
        self.new_droped_rids = []

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
        # done is a list of finished legs
        done = []
        self.new_picked_rids.clear()
        self.new_droped_rids.clear()
        while dT > 0 and len(self.route) > 0:
            leg = self.route[0]
            # if the first leg could be finished by then
            if leg.t < dT:
                dT -= leg.t
                self.T += leg.t
                if T_WARM_UP <= self.T <= T_WARM_UP + T_STUDY:
                    self.Ts += leg.t if leg.rid != -1 else 0
                    self.Ds += leg.d if leg.rid != -1 else 0
                    self.Tr += leg.t if leg.rid == -1 else 0
                    self.Dr += leg.d if leg.rid == -1 else 0
                    self.Lt += leg.t * self.n if leg.rid != -1 else 0
                    self.Ld += leg.d * self.n if leg.rid != -1 else 0
                self.update_service_status_after_veh_finish_a_leg(done, leg)
            else:
                while dT > 0 and len(leg.steps) > 0:
                    step = leg.steps[0]
                    # if the first leg could not be finished, but the first step of the leg could be finished by then
                    if step.t < dT:
                        dT -= step.t
                        self.T += step.t
                        if T_WARM_UP <= self.T <= T_WARM_UP + T_STUDY:
                            self.Ts += step.t if leg.rid != -1 else 0
                            self.Ds += step.d if leg.rid != -1 else 0
                            self.Tr += step.t if leg.rid == -1 else 0
                            self.Dr += step.d if leg.rid == -1 else 0
                            self.Lt += step.t * self.n if leg.rid != -1 else 0
                            self.Ld += step.d * self.n if leg.rid != -1 else 0
                        self.jump_to_location(step.nid[1], step.geo[1][0], step.geo[1][1])
                        self.pop_step()

                        if len(leg.steps) == 0:
                            # corner case: leg.t extremely small, but still larger than dT
                            # this is due to the limited precision of the floating point numbers
                            self.update_service_status_after_veh_finish_a_leg(done, leg)
                            break
                    # the vehicle has to stop somewhere within the step
                    else:

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
                        self.jump_to_location(step.nid[0], step.geo[0][0], step.geo[0][1])
                        self.T = T
                        return done
        assert dT > 0 or np.isclose(dT, 0.0)
        assert self.T < T or np.isclose(self.T, T)
        assert len(self.route) == len(self.sche) == 0
        assert self.n == len(self.onboard_rids) == len(self.picking_rids) == 0
        assert np.isclose(self.d, 0.0)
        assert np.isclose(self.t, 0.0)
        self.T = T
        self.d = 0.0
        self.t = 0.0
        self.idle = True
        self.rebl = False
        return done

    def update_service_status_after_veh_finish_a_leg(self, done, leg):
        self.jump_to_location(leg.tnid)
        self.n += leg.pod
        if leg.rid != -2:
            done.append((leg.rid, leg.pod, self.T))
            self.route_record.append((leg.rid, leg.pod))
            finished_sche_step = self.sche.pop(0)
            assert finished_sche_step[0] == leg.rid
            if leg.pod == 1:
                self.picking_rids.remove(leg.rid)
                self.new_picked_rids.append(leg.rid)
                self.onboard_rids.append(leg.rid)
            elif leg.pod == -1:
                self.new_droped_rids.append(leg.rid)
                self.onboard_rids.remove(leg.rid)
                self.served_rids.append(leg.rid)
        assert {sche_step[0] for sche_step in self.sche} == set(self.picking_rids + self.onboard_rids)
        assert self.n == len(self.onboard_rids)
        assert set(self.new_picked_rids) & set(self.new_droped_rids) == set()
        self.pop_leg()

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
        step.nid[0] = step.nid[1]
        step.geo[0][0] += pct * (step.geo[1][0] - step.geo[0][0])
        step.geo[0][1] += pct * (step.geo[1][1] - step.geo[0][1])
        self.t_to_nid = step.t * (1 - pct)
        self.t -= step.t * pct
        self.d -= step.d * pct
        self.route[0].t -= step.t * pct
        self.route[0].d -= step.d * pct
        self.route[0].steps[0].t -= step.t * pct
        self.route[0].steps[0].d -= step.d * pct
        assert self.route[0].steps[0].nid[0] == self.route[0].steps[0].nid[1]
        self.step_to_nid = copy.deepcopy(self.route[0].steps[0])
        assert np.isclose(self.step_to_nid.t, self.t_to_nid)

    def jump_to_location(self, nid, lng=None, lat=None):
        self.nid = nid
        if lng is None:
            [lng, lat] = get_node_geo(nid)
        self.lng = lng
        self.lat = lat

    # build the route of the vehicle based on a series of schedule tasks (rid, pod, tnid, ept, ddl)
    # update t, d, idle, rebl accordingly
    # rid, pod, tlng, tlat are defined as in class Leg
    def build_route(self, sche, reqs=None, T=None):
        # if self.id == 142:
        #     print('route', [(leg.rid, leg.pod) for leg in self.route])
        #     print('sche', [(step[0], step[1]) for step in self.sche])
        self.clear_route()
        self.sche = copy.deepcopy(sche)
        if self.step_to_nid:
            assert self.lng == self.step_to_nid.geo[0][0]
            # add the unfinished step from last move updating
            rid = -2
            pod = 0
            tnid = self.step_to_nid.nid[1]
            tlng = self.step_to_nid.geo[1][0]
            tlat = self.step_to_nid.geo[1][1]
            ept = self.T + self.step_to_nid.t
            ddl = self.T + self.step_to_nid.t
            duration = self.step_to_nid.t
            distance = self.step_to_nid.d
            steps = [copy.deepcopy(self.step_to_nid), Step(0, 0, [tnid, tnid], [[tlng, tlat], [tlng, tlat]])]
            leg = Leg(rid, pod, tnid, ept, ddl, duration, distance, steps)
            # the last step of a leg is always of length 2,
            # consisting of 2 identical points as a flag of the end of the leg
            assert len(leg.steps[-1].geo) == 2
            assert leg.steps[-1].geo[0] == leg.steps[-1].geo[1]
            self.route.append(leg)
            self.tnid = leg.steps[-1].nid[1]
            self.d += leg.d
            self.t += leg.t

        for (rid, pod, tnid, ept, ddl) in sche:
            self.add_leg(rid, pod, tnid, ept, ddl, reqs, T)
            if pod == 1:
                self.picking_rids.append(rid)

        if len(self.route) != 0:
            if self.route[0].rid == -1:
                assert len(self.route) == 1
                self.idle = True
                self.rebl = True
            else:
                self.idle = False
                self.rebl = False
                # verify the route with capacity constraint
                n = self.n
                for leg in self.route:
                    n += leg.pod
                assert n == 0

    # add a leg based on (rid, pod, tnid, ept, ddl)
    def add_leg(self, rid, pod, tnid, ept, ddl, reqs, T):
        duration, distance, segments = build_route_from_origin_to_dest(self.tnid, tnid)
        steps = [Step(s[0], s[1], s[2], s[3]) for s in segments]
        leg = Leg(rid, pod, tnid, ept, ddl, duration, distance, steps)
        # the last step of a leg is always of length 2,
        # consisting of 2 identical points as a flag of the end of the leg
        # (this check is due to using OSRM, might not necessary now)
        assert len(leg.steps[-1].geo) == 2
        assert leg.steps[-1].geo[0] == leg.steps[-1].geo[1]
        if pod == 1:
            # # if pickup and the vehicle arrives in advance, add an extra wait
            # (designed for advance booking demand, not used when all trips are real time)
            # if T + self.t + leg.t < reqs[rid].Cep:
            #     wait = reqs[rid].Cep - (T + self.t + leg.t)
            #     leg.steps[-1].t += wait
            #     leg.t += wait

            # latest pick-up time is reduced to the expected pick-up time
            # (currently, this change is not updated to parameters in schedule, so debug is needed)
            buffer = 30
            if T + self.t + leg.t + buffer < reqs[rid].Clp:
                reqs[rid].Clp = round(T + self.t + leg.t + buffer, 2)

        self.route.append(leg)
        self.tnid = leg.steps[-1].nid[1]
        self.d += leg.d
        self.t += leg.t
        if pod == 1:
            reqs[rid].Etp = T + self.t
        else:
            assert pod == -1
            reqs[rid].Etd = T + self.t

    # remove the current route
    def clear_route(self):
        self.picking_rids.clear()
        self.route.clear()
        self.sche.clear()
        self.feasible_sches.clear()
        self.d = 0.0
        self.t = 0.0
        self.tnid = self.nid
        self.idle = True
        self.rebl = False

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
            [leg_tlng, leg_tlat] = get_node_geo(leg.tnid)
            plt.plot(leg_tlng, leg_tlat, color=color,
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
        str += '\n  has %d leg(s), dist = %.1f, dura = %.1f' % (
            len(self.route), self.d, self.t)
        for leg in self.route:
            str += '\n    %s req %d at (%d), dist = %.1f, dura = %.1f' % (
                'pickup' if leg.pod == 1 else 'dropoff' if leg.pod == -1 else 'rebalancing',
                leg.rid, leg.tnid, leg.d, leg.t)
        return str
