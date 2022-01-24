"""
definition of vehicles for the AMoD system
"""

from src.simulator.route_functions import *


class Veh(object):
    """
    Veh is a class for vehicles
    Attributes:
        id: sequential unique id
        status: idle, working and rebalancing
        state_time: system time at current state
        lat: current lngitude
        lng: current longtitude
        nid: current nearest node id in network
        step_to_nid: step from current location (when veh is on an edge) to the sink node in network
        t_to_nid: travel time from current location (when veh is on an edge) to the sink node in network
        d_to_nid: travel distance from current location (when veh is on an edge) to the sink node in network
        tnid: target (end of route) node id
        K: capacity
        load: number of passengers on board
        sche: (schedule) a list of pick-up and drop-off points
        route: a list of legs
        t: total duration of the route
        d: total distance of the route
        Ds: accumulated service distance traveled
        Ts: accumulated service time traveled
        Dr: accumulated rebalancing distance traveled
        Tr: accumulated rebalancing time traveled
        Lt: accumulated load, weighed by service time
        Ld: accumulated load, weighed by service distance
        picking_rids: ids of requests currently waiting for this vehicle to pick
        onboard_rid: id of requests currently on board
        new_pick_rid: id of requests newly picked up in current interval
        new_drop_rid: id of requests newly dropped off in current interval

    """

    def __init__(self, id: int, nid: int, lng: float, lat: float, capacity: int, system_time_sec: float):
        self.id = id
        self.status = VehicleStatus.IDLE
        self.state_time = system_time_sec
        self.lng = lng
        self.lat = lat
        self.nid = nid
        self.K = capacity
        self.step_to_nid = None
        self.t_to_nid = 0.0
        self.d_to_nid = 0.0
        self.tnid = self.nid
        self.load = 0
        self.sche = []
        self.route = deque([])
        self.t = 0.0
        self.d = 0.0
        self.Ds = 0.0
        self.Ts = 0.0
        self.Ds_empty = 0.0
        self.Ts_empty = 0.0
        self.Dr = 0.0
        self.Tr = 0.0
        self.Lt = 0.0
        self.Ld = 0.0
        self.picking_rids = []
        self.onboard_rids = []
        self.new_picked_rids = []
        self.new_dropped_rids = []
        self.sche_has_been_updated_at_current_epoch = False

    # update the vehicle location as well as the route after moving to time T
    def move_to_time(self, system_time_sec: int, update_vehicle_statistics: bool) -> list:
        dT = system_time_sec - self.state_time
        if dT <= 0:
            return []
        self.step_to_nid = None
        self.t_to_nid = 0.0
        self.d_to_nid = 0.0
        # done is a list of finished legs
        done = []
        self.new_picked_rids.clear()
        self.new_dropped_rids.clear()
        while dT > 0 and len(self.route) > 0:
            leg = self.route[0]
            # if the first leg could be finished by then
            if leg.t < dT:
                dT -= leg.t
                self.state_time += leg.t
                if update_vehicle_statistics:
                    self.Ts += leg.t
                    self.Ds += leg.d
                    self.Lt += leg.t * self.load
                    self.Ld += leg.d * self.load
                    if self.status == VehicleStatus.WORKING and self.load == 0:
                        self.Ts_empty += leg.t
                        self.Ds_empty += leg.d
                    if self.status == VehicleStatus.REBALANCING:
                        self.Tr += leg.t
                        self.Dr += leg.d

                self.update_service_status_after_veh_finish_a_leg(done, leg)
            else:
                while dT > 0 and len(leg.steps) > 0:
                    step = leg.steps[0]
                    # if the first leg could not be finished, but the first step of the leg could be finished by then
                    if step.t < dT:
                        dT -= step.t
                        self.state_time += step.t
                        if update_vehicle_statistics:
                            self.Ts += step.t
                            self.Ds += step.d
                            self.Lt += step.t * self.load
                            self.Ld += step.d * self.load
                            if self.status == VehicleStatus.WORKING and self.load == 0:
                                self.Ts_empty += step.t
                                self.Ds_empty += step.d
                            if self.status == VehicleStatus.REBALANCING:
                                self.Tr += step.t
                                self.Dr += step.d

                        self.jump_to_location(step.nid_pair[1], step.geo_pair[1][0], step.geo_pair[1][1])
                        self.pop_step()

                        if len(leg.steps) == 0:
                            # corner case: leg.t extremely small, but still larger than dT
                            # this is due to the limited precision of the floating point numbers
                            self.update_service_status_after_veh_finish_a_leg(done, leg)
                            break
                    # the vehicle has to stop somewhere within the step
                    else:
                        pct = dT / step.t
                        if update_vehicle_statistics:
                            self.Ts += dT
                            self.Ds += step.d * pct
                            self.Lt += dT * self.load
                            self.Ld += step.d * pct * self.load
                            if self.status == VehicleStatus.WORKING and self.load == 0:
                                self.Ts_empty += dT
                                self.Ds_empty += step.d * pct
                            if self.status == VehicleStatus.REBALANCING:
                                self.Tr += dT
                                self.Dr += step.d * pct

                        # find the exact location the vehicle stops and update the step
                        self.cut_step(pct)
                        self.jump_to_location(step.nid_pair[0], step.geo_pair[0][0], step.geo_pair[0][1])
                        self.state_time = system_time_sec
                        return done

        # We've finished the whole schedule.
        assert dT > 0 or np.isclose(dT, 0.0)
        assert self.state_time < system_time_sec or np.isclose(self.state_time, system_time_sec)
        assert len(self.route) == len(self.sche) == 0
        assert self.load == len(self.onboard_rids) == len(self.picking_rids) == 0
        assert np.isclose(self.d, 0.0)
        assert np.isclose(self.t, 0.0)
        self.state_time = system_time_sec
        self.d = 0.0
        self.t = 0.0
        self.status = VehicleStatus.IDLE
        return done

    def update_service_status_after_veh_finish_a_leg(self, done: list[(int, int, int)], leg: Leg):
        self.jump_to_location(leg.tnid)
        self.load += leg.pod
        if leg.rid != -2:
            done.append((leg.rid, leg.pod, self.state_time))
            finished_sche_step = self.sche.pop(0)
            assert finished_sche_step[0] == leg.rid
            if leg.pod == 1:
                self.picking_rids.remove(leg.rid)
                self.new_picked_rids.append(leg.rid)
                self.onboard_rids.append(leg.rid)
                # if DEBUG_PRINT:
                #     print(f"            +vehicle #{self.id} picked up req #{leg.rid} at {self.state_time}s")
            elif leg.pod == -1:
                self.new_dropped_rids.append(leg.rid)
                self.onboard_rids.remove(leg.rid)
                # if DEBUG_PRINT:
                #     print(f"            +vehicle #{self.id} dropped up req #{leg.rid} at {self.state_time}s")
        assert self.load == len(self.onboard_rids)
        # if set(self.new_picked_rids) & set(self.new_dropped_rids) != set():
        #     print('[INFO]', self.new_picked_rids, self.new_dropped_rids)
        # assert set(self.new_picked_rids) & set(self.new_dropped_rids) == set()
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
    def cut_step(self, pct: float):
        step = self.route[0].steps[0]
        step.nid_pair[0] = step.nid_pair[1]
        step.geo_pair[0][0] += pct * (step.geo_pair[1][0] - step.geo_pair[0][0])
        step.geo_pair[0][1] += pct * (step.geo_pair[1][1] - step.geo_pair[0][1])
        self.t_to_nid = step.t * (1 - pct)
        self.d_to_nid = step.d * (1 - pct)
        self.t -= step.t * pct
        self.d -= step.d * pct
        self.route[0].t -= step.t * pct
        self.route[0].d -= step.d * pct
        self.route[0].steps[0].t -= step.t * pct
        self.route[0].steps[0].d -= step.d * pct
        self.step_to_nid = copy.deepcopy(self.route[0].steps[0])
        assert self.route[0].steps[0].nid_pair[0] == self.route[0].steps[0].nid_pair[1]
        assert np.isclose(self.step_to_nid.t, self.t_to_nid)
        assert np.isclose(self.step_to_nid.d, self.d_to_nid)

    def jump_to_location(self, nid: int, lng=None, lat=None):
        self.nid = nid
        if lng is None:
            [lng, lat] = get_node_geo(nid)
        self.lng = lng
        self.lat = lat

    # build the route of the vehicle based on a series of schedule tasks (rid, pod, tnid, ddl)
    # update t, d, status accordingly
    # rid, pod, tlng, tlat are defined as in class Leg
    def build_route(self, sche: list[(int, int, int, float)]):
        # if a vehicle is assigned a trip while ensuring it visits the rebalancing node,
        # its rebalancing task can be cancelled
        if self.status == VehicleStatus.REBALANCING and len(sche) > 1:
            assert (len(self.sche) == 1)
            idx = -1
            for (rid, pod, tnid, ddl) in sche:
                idx += 1
                if rid == -1:
                    sche.pop(idx)
                    break

        # 1. Update vehicle's schedule with detailed route.
        self.clear_route()
        self.sche = copy.copy(sche)
        if self.step_to_nid:
            assert self.lng == self.step_to_nid.geo_pair[0][0]
            # add the unfinished step from last move updating
            rid = -2
            pod = 0
            tnid = self.step_to_nid.nid_pair[1]
            tlng = self.step_to_nid.geo_pair[1][0]
            tlat = self.step_to_nid.geo_pair[1][1]
            ddl = self.state_time + self.step_to_nid.t
            duration = self.step_to_nid.t
            distance = self.step_to_nid.d
            steps = [copy.deepcopy(self.step_to_nid), Step(0, 0, [tnid, tnid], [[tlng, tlat], [tlng, tlat]])]
            leg = Leg(rid, pod, tnid, ddl, duration, distance, steps)
            # the last step of a leg is always of length 2,
            # consisting of 2 identical points as a flag of the end of the leg
            assert len(leg.steps[-1].geo_pair) == 2
            assert leg.steps[-1].geo_pair[0] == leg.steps[-1].geo_pair[1]
            self.route.append(leg)
            self.tnid = leg.steps[-1].nid_pair[1]
            self.d += leg.d
            self.t += leg.t
        if self.sche:
            for (rid, pod, tnid, ddl) in self.sche:
                self.add_leg(rid, pod, tnid, ddl)
                if pod == 1:
                    self.picking_rids.append(rid)

        # 2. Update vehicle's status.
        self.sche_has_been_updated_at_current_epoch = True
        if self.sche:
            if self.sche[0][1] == 1 or self.sche[0][1] == -1:
                self.status = VehicleStatus.WORKING
                # verify the route with capacity constraint
                n = self.load
                for leg in self.route:
                    n += leg.pod
                assert n == 0
            else:
                self.status = VehicleStatus.REBALANCING
                assert (self.sche[0][0] == -1 and len(self.sche) == 1)
        else:
            self.status = VehicleStatus.IDLE

    # add a leg based on (rid, pod, tnid, ddl)
    def add_leg(self, rid: int, pod: int, tnid: int, ddl: float):
        duration, distance, segments = build_route_from_origin_to_dest(self.tnid, tnid)
        steps = [Step(s[0], s[1], s[2], s[3]) for s in segments]
        leg = Leg(rid, pod, tnid, ddl, duration, distance, steps)
        # the last step of a leg is always of length 2,
        # consisting of 2 identical points as a flag of the end of the leg
        # (this check is due to using OSRM, might not necessary now)
        assert len(leg.steps[-1].geo_pair) == 2
        assert leg.steps[-1].geo_pair[0] == leg.steps[-1].geo_pair[1]
        self.route.append(leg)
        self.tnid = leg.steps[-1].nid_pair[1]
        self.d += leg.d
        self.t += leg.t

    # remove the current route
    def clear_route(self):
        self.picking_rids.clear()
        self.route.clear()
        self.sche.clear()
        self.d = 0.0
        self.t = 0.0
        self.tnid = self.nid


