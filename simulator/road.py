"""Ring road: 12 segments, 2 lanes, two RSU zones (S00-S05 -> rsu-1, S06-S11 -> rsu-2)."""
import math

N_SEGMENTS = 12
LANES = 2


class Road:
    def __init__(self, segment_length_m: float = 100.0):
        self.segment_length_m = segment_length_m
        self.length_m = N_SEGMENTS * segment_length_m
        self.radius_m = self.length_m / (2 * math.pi)

    def wrap(self, s: float) -> float:
        return s % self.length_m

    def segment_index(self, s: float) -> int:
        return int(self.wrap(s) // self.segment_length_m) % N_SEGMENTS

    def segment_id(self, s: float) -> str:
        return f"S{self.segment_index(s):02d}"

    @staticmethod
    def rsu_of_index(idx: int) -> str:
        return "rsu-1" if idx < N_SEGMENTS // 2 else "rsu-2"

    def rsu_id(self, s: float) -> str:
        return self.rsu_of_index(self.segment_index(s))

    def segment_start(self, segment_id: str) -> float:
        return int(segment_id[1:]) * self.segment_length_m

    def xy(self, s: float):
        theta = 2 * math.pi * self.wrap(s) / self.length_m
        return round(self.radius_m * math.cos(theta), 1), round(self.radius_m * math.sin(theta), 1)

    def heading_deg(self, s: float) -> float:
        theta = 2 * math.pi * self.wrap(s) / self.length_m
        return round((math.degrees(theta) + 90.0) % 360.0, 1)
