from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class NoteEvent:
    channel: int
    pitch: int
    velocity: int
    on_tick: int
    off_tick: int
    note_id: int


class VirtualSink:
    """A minimal sink capturing events for tests and demos.

    Records tuples like (type, args...). Types: 'on', 'off', 'panic'.
    """

    def __init__(self) -> None:
        self.events: List[Tuple[str, int, int, int]] = []

    def note_on(self, channel: int, pitch: int, velocity: int) -> None:
        self.events.append(("on", channel, pitch, velocity))

    def note_off(self, channel: int, pitch: int) -> None:
        self.events.append(("off", channel, pitch, 0))

    def panic(self) -> None:
        self.events.append(("panic", -1, -1, 0))


class Engine:
    """Real-time scheduling engine (no look-ahead).

    - Tick unit is meta.ppq ticks.
    - step_ticks = (ppq * 4) / stepsPerBar (assume 4/4)
    - On tick T: emit all due Note On/Off for T only.
    - Active notes ledger guarantees Note Off, even on doc replace.
    """

    def __init__(self, sink: VirtualSink) -> None:
        self.sink = sink
        self.doc: Dict[str, Any] | None = None
        self.meta: Dict[str, Any] | None = None
        self.step_ticks: int = 0
        self.tick: int = 0
        self.playing: bool = False
        # Active notes ledger: (ch,pitch) -> stack of NoteEvent
        self.active: Dict[Tuple[int, int], List[NoteEvent]] = {}
        self._next_note_id: int = 1

    # --- Public control ---
    def load(self, doc: Dict[str, Any]) -> None:
        self.doc = doc
        self.meta = doc.get("meta", {})
        ppq = int(self.meta.get("ppq", 96))
        spb = int(self.meta.get("stepsPerBar", 16))
        # assume 4/4: 4 quarter notes per bar
        self.step_ticks = int((ppq * 4) / spb) if spb > 0 else 0

    def replace_doc(self, doc: Dict[str, Any]) -> None:
        # Replace current document atomically; keep ledger intact
        self.load(doc)

    def start(self) -> None:
        self.playing = True

    def stop(self) -> None:
        # Emit All Notes Off across channels and clear ledger
        self._panic()
        self.playing = False

    # --- Tick loop integration ---
    def on_tick(self, tick: int) -> None:
        """Call on every meta.ppq tick in monotonically increasing order."""
        self.tick = tick
        # First: emit any due Note Offs
        self._emit_due_offs(tick)
        if not self.playing or not self.doc:
            return
        # Then: emit Note Ons due exactly at this tick
        self._emit_due_ons(tick)

    # --- Internals ---
    def _emit_due_ons(self, tick: int) -> None:
        if not self.doc or self.step_ticks <= 0:
            return
        tracks = self.doc.get("tracks", [])
        meta = self.doc.get("meta", {})
        spb = int(meta.get("stepsPerBar", 16))
        bar_ticks = self.step_ticks * spb
        dev = self.doc.get("deviceProfile", {})
        drum_map = {}
        if isinstance(dev, dict) and isinstance(dev.get("drumMap"), dict):
            drum_map = {k: int(v) for k, v in dev["drumMap"].items() if isinstance(k, str)}
        # GM-safe fallback
        if not drum_map:
            drum_map = {"kick": 36, "snare": 38, "clap": 39, "ch": 42, "oh": 46}
        for tr in tracks:
            ch = int(tr.get("midiChannel", 0))
            pat = tr.get("pattern", {})
            steps = pat.get("steps", [])
            length_bars = max(1, int(pat.get("lengthBars", 1)))
            for st in steps:
                idx = int(st.get("idx", -1))
                if idx < 0:
                    continue
                step_tick = (idx % (spb * length_bars))
                step_tick *= self.step_ticks
                # Emit only when exactly due at this tick (no look-ahead)
                if (tick % (bar_ticks * length_bars)) == step_tick:
                    events = st.get("events", [])
                    for e in events:
                        pitch = e.get("pitch")
                        if pitch is None:
                            # For MVP engine skeleton, only absolute pitch is supported in tests.
                            continue
                        vel = int(e.get("velocity", 100))
                        ls = int(e.get("lengthSteps", 1))
                        gate = float(e.get("gate", 1.0))
                        length_ticks = max(1, int(self.step_ticks * ls * gate))
                        on_tick = tick
                        off_tick = tick + length_ticks
                        note_id = self._next_note_id
                        self._next_note_id += 1
                        # Emit Note On
                        self.sink.note_on(ch, int(pitch), vel)
                        # Push to active ledger (stack semantics for overlaps)
                        key = (ch, int(pitch))
                        self.active.setdefault(key, []).append(
                            NoteEvent(channel=ch, pitch=int(pitch), velocity=vel, on_tick=on_tick, off_tick=off_tick, note_id=note_id)
                        )

            # drumKit runtime scheduling
            dk = tr.get("drumKit")
            if isinstance(dk, dict) and isinstance(dk.get("patterns"), list):
                patterns = dk.get("patterns", [])
                repeat_bars = max(1, int(dk.get("repeatBars", 1)))
                default_len = max(1, int(dk.get("lengthSteps", 1)))
                # Current bar within loop (1-based per spec)
                bar_in_loop = ((tick // bar_ticks) % length_bars) + 1
                # Step within current bar
                if self.step_ticks > 0:
                    step_in_bar = (tick % bar_ticks) // self.step_ticks
                else:
                    step_in_bar = 0
                # Only schedule on exact step boundaries
                if self.step_ticks == 0 or (tick % self.step_ticks) != 0:
                    return
                for spec in patterns:
                    try:
                        b0 = int(spec.get("bar", 1))
                        key = str(spec.get("key"))
                        pattern_str = str(spec.get("pattern"))
                    except Exception:
                        continue
                    # Active if bar_in_loop within [b0, b0+repeat_bars-1]
                    if not (b0 <= bar_in_loop <= (b0 + repeat_bars - 1)):
                        continue
                    if step_in_bar < 0 or step_in_bar >= len(pattern_str):
                        continue
                    if pattern_str[step_in_bar] != "x":
                        continue
                    # Resolve pitch from drum map (skip if unknown)
                    if key not in drum_map:
                        continue
                    pitch = int(drum_map[key])
                    vel = int(spec.get("vel", 100))
                    ls = int(spec.get("lengthSteps", default_len))
                    length_ticks = max(1, int(self.step_ticks * ls))
                    on_tick = tick
                    off_tick = tick + length_ticks
                    note_id = self._next_note_id
                    self._next_note_id += 1
                    self.sink.note_on(ch, pitch, vel)
                    self.active.setdefault((ch, pitch), []).append(
                        NoteEvent(channel=ch, pitch=pitch, velocity=vel, on_tick=on_tick, off_tick=off_tick, note_id=note_id)
                    )

    def _emit_due_offs(self, tick: int) -> None:
        # Iterate all active notes and emit offs due exactly at this tick
        for key, stack in list(self.active.items()):
            ch, pitch = key
            i = 0
            while i < len(stack):
                ne = stack[i]
                if ne.off_tick <= tick:
                    # Due (or overdue) -> emit off and remove
                    self.sink.note_off(ch, pitch)
                    stack.pop(i)
                else:
                    i += 1
            if not stack:
                del self.active[key]

    def _panic(self) -> None:
        # Emit offs for any lingering notes, then an All Notes Off marker
        for (ch, pitch), stack in list(self.active.items()):
            while stack:
                self.sink.note_off(ch, pitch)
                stack.pop()
        self.active.clear()
        self.sink.panic()
