"""Delivery faults applied between event generation and the transport:
loss (drop), duplication, extra delay and reordering. Every drop and duplicate is logged."""
import copy


class FaultInjector:
    def __init__(self, rngs: dict, drop=0.0, dup=0.0, delay_ms=(0, 0), reorder_window=0, log=None):
        self.rngs = rngs
        self.drop, self.dup = drop, dup
        self.delay_ms = delay_ms
        self.reorder_window = reorder_window
        self.log = log or (lambda record: None)
        self.pending = []          # (deliver_at, order, event)
        self.reorder_buf = []
        self.order = 0
        self.stats = {"dropped": 0, "duplicated": 0}

    def _delay(self):
        lo, hi = self.delay_ms
        return self.rngs["delay"].uniform(lo, hi) / 1000.0 if hi > 0 else 0.0

    def _schedule(self, ev, at):
        self.pending.append((at, self.order, ev))
        self.order += 1

    def submit(self, ev, now):
        if self.drop and self.rngs["drop"].random() < self.drop:
            self.stats["dropped"] += 1
            self.log({"fault": "drop", "event_id": ev["event_id"], "source_id": ev["source_id"], "seq": ev["seq"]})
            return
        self._schedule(ev, now + self._delay())
        if self.dup and self.rngs["dup"].random() < self.dup:
            self.stats["duplicated"] += 1
            self.log({"fault": "dup", "event_id": ev["event_id"], "source_id": ev["source_id"], "seq": ev["seq"]})
            self._schedule(copy.deepcopy(ev), now + self._delay() + self.rngs["dup"].uniform(0.0, 0.5))

    def due(self, now):
        ready = sorted(p for p in self.pending if p[0] <= now)
        self.pending = [p for p in self.pending if p[0] > now]
        events = [p[2] for p in ready]
        if self.reorder_window > 1:
            self.reorder_buf.extend(events)
            out = []
            while len(self.reorder_buf) >= self.reorder_window:
                chunk = self.reorder_buf[:self.reorder_window]
                self.reorder_buf = self.reorder_buf[self.reorder_window:]
                self.rngs["reorder"].shuffle(chunk)
                out.extend(chunk)
            return out
        return events

    def flush(self):
        rest = [p[2] for p in sorted(self.pending)] + self.reorder_buf
        self.pending, self.reorder_buf = [], []
        return rest
