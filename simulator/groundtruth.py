"""Records what really happened in the simulation, to compare with the alerts V2X-SERVICE raises."""
import json


class JsonlLog:
    def __init__(self, path=None):
        self.records = []
        self._f = open(path, "w", encoding="utf-8") if path else None

    def __call__(self, record: dict):
        self.records.append(record)
        if self._f:
            self._f.write(json.dumps(record, separators=(",", ":")) + "\n")

    def close(self):
        if self._f:
            self._f.close()
