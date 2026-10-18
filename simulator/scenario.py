"""Scenario files (YAML) with defaults."""
import yaml

DEFAULTS = {
    "name": "unnamed",
    "duration_s": 300,
    "vehicles": 5,
    "segment_length_m": 100,
    "rate_hz": {"position": 1.0, "rsu_density": 0.2, "emergency": 2.0},
    "injections": [],
}


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    cfg = {**DEFAULTS, **data}
    cfg["rate_hz"] = {**DEFAULTS["rate_hz"], **(data.get("rate_hz") or {})}
    cfg["injections"] = sorted(cfg["injections"] or [], key=lambda i: i["t"])
    return cfg
