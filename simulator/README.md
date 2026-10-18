# V2X simulator

Synthetic traffic for the V2X system: every vehicle's On-Board Unit plus the two RSUs' density reports.
Vehicles follow the Intelligent Driver Model (IDM) on a 12-segment ring road split into two RSU zones
(`S00`-`S05` -> `rsu-1`, `S06`-`S11` -> `rsu-2`). All data is synthetic.

## Install

    pip install -r simulator/requirements.txt

## Run (from the repository root)

    # dry run, events printed to the terminal, no AWS needed
    python -m simulator --scenario simulator/scenarios/accident.yaml --transport stdout --time-scale 10

    # D1: real time, to SQS v2x-events (needs the lab session credentials in ~/.aws/credentials)
    python -m simulator --scenario simulator/scenarios/accident.yaml --transport sqs

## Options

| Option | Meaning |
| --- | --- |
| `--scenario` | YAML file in `simulator/scenarios/` |
| `--seed` | Random seed (default 42); same seed, same events |
| `--vehicles N` | Override the number of vehicles (default 5) |
| `--duration S` | Override the scenario duration in seconds |
| `--rate-scale F` | Multiply every publish rate (configurable event rate) |
| `--time-scale F` | Run model time F times faster than wall time |
| `--fast` | No waiting at all (offline tests) |
| `--drop P`, `--dup P` | Loss and duplication probability |
| `--delay-ms A:B` | Extra delay per event, uniform between A and B ms |
| `--reorder-window N` | Shuffle every N events |
| `--burst S:E:F` | Multiply rates by F between second S and E |
| `--transport` | `sqs`, `stdout` (`mqtt` arrives in Deliverable 2) |

## Output

Each run writes `runs/<run_id>/`: `config.json` (resolved settings, seed, git SHA), `groundtruth.jsonl`
(what really happened: crashes, hard brakes, hazards, emergency vehicles), `faults.jsonl` (every injected
drop and duplicate) and `summary.json` (event counts).

## Event types

`position` (1 Hz per vehicle), `brake` (deceleration of at least 4 m/s^2), `crash`, `hazard`, `emergency`
(2 Hz from the emergency vehicle) and `density` (each RSU, every 5 s, one per segment of its zone).
All of them validate against `schema/v2x-event.schema.json`.
