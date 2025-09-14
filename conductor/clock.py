from __future__ import annotations

import threading
import time
from typing import Callable, Optional


TickHandler = Callable[[int], None]


class InternalClock:
    def __init__(self, bpm: float, tick_handler: TickHandler, send_midi_clock: Optional[Callable[[], None]] = None):
        self.bpm = float(bpm)
        self.tick_handler = tick_handler
        self.send_midi_clock = send_midi_clock
        self._t: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._tick = 0

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
        # interval between MIDI clock pulses at 24 PPQN
        interval = 60.0 / (self.bpm * 24.0)
        next_call = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_call:
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


class ExternalClock:
    def __init__(self, tick_from_external: Callable[[int], None]):
        # tick_from_external(pulses) called on every incoming MIDI clock
        self.on_pulse = tick_from_external

    # Wiring of callback is handled by MIDI input (see play_local)

