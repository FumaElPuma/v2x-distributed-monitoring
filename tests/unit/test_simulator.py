import json
from pathlib import Path

import jsonschema
import pytest

from simulator import scenario
from simulator.engine import Simulator
from simulator.transport import ListTransport

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schema" / "v2x-event.schema.json").read_text())
ACCIDENT = str(ROOT / "simulator" / "scenarios" / "accident.yaml")


def run(seed=42, **kwargs):
    cfg = scenario.load(ACCIDENT)
    out, truth = ListTransport(), []
    stats = Simulator(cfg, out, seed=seed, realtime=False, start_wall=1_790_000_000.0,
                      groundtruth=truth.append, **kwargs).run()
    return out.events, truth, stats


@pytest.fixture(scope="module")
def accident():
    return run()


def test_every_event_matches_the_schema(accident):
    events, _, _ = accident
    for ev in events:
        jsonschema.validate(ev, SCHEMA)


def test_five_vehicles_and_at_least_three_event_types(accident):
    events, _, _ = accident
    vehicles = {e["source_id"] for e in events if e["source_type"] == "vehicle"}
    assert vehicles == {f"veh-{i:04d}" for i in range(1, 6)}
    assert {"position", "brake", "crash"} <= {e["event_type"] for e in events}


def test_crash_makes_the_follower_brake_hard(accident):
    events, truth, _ = accident
    brakes = [e for e in events if e["event_type"] == "brake"]
    assert any(e["source_id"] == "veh-0001" and e["payload"]["decel_mps2"] >= 4 for e in brakes)
    assert any(t["kind"] == "crash" and t["source_id"] == "veh-0002" for t in truth)


def test_event_ids_unique_and_seq_monotonic(accident):
    events, _, _ = accident
    assert len({e["event_id"] for e in events}) == len(events)
    last = {}
    for e in events:
        assert e["seq"] == last.get(e["source_id"], -1) + 1
        last[e["source_id"]] = e["seq"]


def test_same_seed_same_stream_different_seed_different_stream():
    a, _, _ = run(seed=7)
    b, _, _ = run(seed=7)
    c, _, _ = run(seed=8)
    assert a == b
    assert [e["event_id"] for e in a] != [e["event_id"] for e in c]


def test_duplicates_keep_the_event_id_and_drops_are_counted():
    events, _, stats = run(faults={"dup": 0.2, "drop": 0.1})
    ids = [e["event_id"] for e in events]
    assert len(ids) - len(set(ids)) == stats["duplicated"]
    assert len(set(ids)) == stats["generated"] - stats["dropped"]
    assert 0.05 < stats["dropped"] / stats["generated"] < 0.15


def test_rate_scale_multiplies_position_events():
    base, _, _ = run()
    fast, _, _ = run(rate_scale=2.0)
    n = lambda evs: sum(e["event_type"] == "position" for e in evs)
    assert 1.8 < n(fast) / n(base) < 2.2
