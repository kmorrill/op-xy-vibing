from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Optional, Deque, List, Tuple


TickHandler = Callable[[int], None]


class InternalClock:
    def __init__(self, bpm: float, tick_handler: TickHandler, send_midi_clock: Optional[Callable[[], None]] = None):
        self.bpm = float(bpm)
        self.tick_handler = tick_handler
        self.send_midi_clock = send_midi_clock
        self._t: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._tick = 0
        self._jitter_ms: Deque[float] = deque(maxlen=512)
        self._lock = threading.Lock()
        self._interval = 60.0 / (self.bpm * 24.0)

    def start(self):
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=1.0)

    def _run(self):
        # interval between MIDI clock pulses at 24 PPQN (updated via set_bpm)
        next_call = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_call:
                # Record jitter relative to scheduled time
                jitter_ms = max(0.0, (now - next_call) * 1000.0)
                with self._lock:
                    self._jitter_ms.append(jitter_ms)
                with self._lock:
                    interval = self._interval
                next_call += interval
                # Send MIDI clock pulse if requested
                if self.send_midi_clock:
                    try:
                        self.send_midi_clock()
                    except Exception:
                        pass
                # Convert to engine ticks via adapter outside
                self.tick_handler(1)
            else:
                time.sleep(min(0.002, max(0.0, next_call - now)))

    def _percentile(self, values: List[float], pct: float) -> float:
        if not values:
            return 0.0
        xs = sorted(values)
        k = (len(xs) - 1) * pct
        f = int(k)
        c = min(f + 1, len(xs) - 1)
        if f == c:
            return xs[f]
        d0 = xs[f] * (c - k)
        d1 = xs[c] * (k - f)
        return d0 + d1

    def get_metrics(self) -> dict:
        # Return jitter p95/p99 over recent window
        with self._lock:
            samples = list(self._jitter_ms)
        return {
            "jitterMsP95": round(self._percentile(samples, 0.95), 3),
            "jitterMsP99": round(self._percentile(samples, 0.99), 3),
        }

    def set_bpm(self, bpm: float) -> None:
        with self._lock:
            self.bpm = float(bpm)
            self._interval = 60.0 / (self.bpm * 24.0)


class ExternalClock:
    def __init__(self, tick_from_external: Callable[[int], None]):
        # tick_from_external(pulses) called on every incoming MIDI clock
        self.on_pulse = tick_from_external

    # Wiring of callback is handled by MIDI input (see play_local)
