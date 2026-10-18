"""Intelligent Driver Model (IDM) car-following on the ring road, no lane changes."""
import math
from dataclasses import dataclass, field

MAX_DECEL = 9.0


@dataclass
class Vehicle:
    vid: str
    lane: int
    s: float                      # position along the ring (m)
    v: float                      # speed (m/s)
    v0: float = 30.0              # desired speed (m/s)
    a: float = 1.0                # max acceleration (m/s^2)
    b: float = 2.0                # comfortable deceleration (m/s^2)
    T: float = 1.5                # time headway (s)
    s0: float = 2.0               # minimum gap (m)
    length: float = 4.5
    source_type: str = "vehicle"
    accel: float = 0.0
    stopped: bool = False         # crashed: stays at v = 0
    active: bool = True
    extra: dict = field(default_factory=dict)


def idm_accel(veh: Vehicle, gap: float, dv: float, v0: float) -> float:
    s_star = veh.s0 + max(0.0, veh.v * veh.T + veh.v * dv / (2 * math.sqrt(veh.a * veh.b)))
    # Free-road term limited to the comfortable deceleration: a lower desired speed (hazard zone)
    # makes the driver ease off, it is not an emergency. Only the interaction term can brake hard.
    free = max(veh.a * (1 - (veh.v / v0) ** 4), -veh.b)
    acc = free - veh.a * (s_star / max(gap, 0.1)) ** 2
    return max(-MAX_DECEL, min(veh.a, acc))


def step(vehicles, road, dt: float, v0_of):
    """Advance all active vehicles by dt. v0_of(vehicle) returns the desired speed now."""
    active = [v for v in vehicles if v.active]
    for lane in {v.lane for v in active}:
        in_lane = sorted((v for v in active if v.lane == lane), key=lambda v: v.s)
        n = len(in_lane)
        for i, veh in enumerate(in_lane):
            if veh.stopped:
                veh.accel = 0.0
                continue
            leader = in_lane[(i + 1) % n]
            if leader is veh:
                gap, dv = road.length_m - veh.length, 0.0
            else:
                gap = road.wrap(leader.s - veh.s) - leader.length
                dv = veh.v - leader.v
            veh.accel = idm_accel(veh, gap, dv, max(v0_of(veh), 0.1))
    for veh in active:
        if veh.stopped:
            veh.v = 0.0
            continue
        veh.v = max(0.0, veh.v + veh.accel * dt)
        veh.s = road.wrap(veh.s + veh.v * dt)
