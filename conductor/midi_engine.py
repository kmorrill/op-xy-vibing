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

    def control_change(self, channel: int, control: int, value: int) -> None:
        self.events.append(("cc", channel, control, max(0, min(127, int(value)))))


class Engine:
    """Real-time scheduling engine (no look-ahead).

    - Tick unit is meta.ppq ticks.
    - step_ticks = (ppq * 4) / stepsPerBar (assume 4/4)
    - On tick T: emit all due Note On/Off for T only.
    - Active notes ledger guarantees Note Off, even on doc replace.
    """

    def __init__(self, sink: VirtualSink, limits: Dict[str, int] | None = None) -> None:
        self.sink = sink
        self.doc: Dict[str, Any] | None = None
        self.meta: Dict[str, Any] | None = None
        self.step_ticks: int = 0
        self.tick: int = 0
        self.playing: bool = False
        # Active notes ledger: (ch,pitch) -> stack of NoteEvent
        self.active: Dict[Tuple[int, int], List[NoteEvent]] = {}
        self._next_note_id: int = 1
        # CC state: last sent value per (channel, control)
        self._last_cc: Dict[Tuple[int, int], int] = {}
        # LFO phase resets on start and bar boundary (tracked via step counter)
        self._started: bool = False
        # Metrics counters
        self.metrics: Dict[str, int] = {
            "msgs_note_on": 0,
            "msgs_note_off": 0,
            "msgs_cc": 0,
            "shed_cc": 0,
        }
        # Simple per-tick CC guard limits (for tests/runtime safety)
        limits = limits or {}
        self.cc_limit_per_tick_global: int = int(limits.get("cc_per_tick_global", 1_000_000))
        self.cc_limit_per_tick_track: int = int(limits.get("cc_per_tick_track", 1_000_000))

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
        self._started = True

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
        # CC/LFO updates on step boundaries
        self._emit_cc_updates(tick)

    def get_metrics(self) -> Dict[str, int]:
        # Return a shallow copy of metrics (e.g., for printing/broadcasting)
        return dict(self.metrics)

    # --- Internals ---
    def _emit_due_ons(self, tick: int) -> None:
        if not self.doc or self.step_ticks <= 0:
            return
        tracks = self.doc.get("tracks", [])
        meta = self.doc.get("meta", {})
        spb = int(meta.get("stepsPerBar", 16))
        bar_ticks = self.step_ticks * spb
        dev = self.doc.get("deviceProfile", {})
        # OP-XY default mapping (lowercase keys)
        default_drum_map = {
            "kick": 53,
            "kick_alt": 54,
            "snare": 55,
            "snare_alt": 56,
            "rim": 57,
            "clap": 58,
            "tambourine": 59,
            "shaker": 60,
            "closed_hat": 61,
            "open_hat": 62,
            "pedal_hat": 63,
            "low_tom": 65,
            "crash": 66,
            "mid_tom": 67,
            "ride": 68,
            "high_tom": 69,
            "conga_low": 71,
            "conga_high": 72,
            "cowbell": 73,
            "guiro": 74,
            "metal": 75,
            "chi": 76,
        }
        # Start with defaults, then overlay any device-specific overrides
        drum_map = dict(default_drum_map)
        if isinstance(dev, dict) and isinstance(dev.get("drumMap"), dict):
            for k, v in dev["drumMap"].items():
                if not isinstance(k, str):
                    continue
                try:
                    drum_map[k.strip().lower()] = int(v)
                except Exception:
                    continue
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
                        self.metrics["msgs_note_on"] += 1
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
                # alias map to allow short keys in patterns
                alias = {
                    "ch": "closed_hat",
                    "oh": "open_hat",
                    "hh": "closed_hat",
                    "lt": "low_tom",
                    "mt": "mid_tom",
                    "ht": "high_tom",
                }
                for spec in patterns:
                    try:
                        b0 = int(spec.get("bar", 1))
                        key = str(spec.get("key")).lower()
                        key = alias.get(key, key)
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
                    self.metrics["msgs_note_on"] += 1
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
                    self.metrics["msgs_note_off"] += 1
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

    def _emit_cc_updates(self, tick: int) -> None:
        doc = self.doc
        if not doc or self.step_ticks <= 0:
            return
        meta = doc.get("meta", {})
        spb = int(meta.get("stepsPerBar", 16))
        bar_ticks = self.step_ticks * spb
        # Only compute on exact step boundaries
        if (tick % max(1, self.step_ticks)) != 0:
            return
        # Compute step position
        step_in_bar = (tick % bar_ticks) // self.step_ticks if bar_ticks > 0 else 0
        # Reset LFO phase on bar boundary or on fresh start
        if step_in_bar == 0 and self._started:
            # phase implied by step_in_bar, nothing to store; just clear the started flag
            self._started = False
        # OP-XY fixed CC name map (subset; see docs)
        name_cc = {
            "track_volume": 7,
            "track_mute": 9,
            "track_pan": 10,
            "param1": 12,
            "param2": 13,
            "param3": 14,
            "param4": 15,
            "amp_attack": 20,
            "amp_decay": 21,
            "amp_sustain": 22,
            "amp_release": 23,
            "filter_attack": 24,
            "filter_decay": 25,
            "filter_sustain": 26,
            "filter_release": 27,
            "voice_mode": 28,  # poly/mono/legato
            "portamento": 29,
            "pitchbend_amount": 30,
            "engine_volume": 31,
            "cutoff": 32,      # Filter cutoff
            "resonance": 33,
            "env_amount": 34,
            "key_tracking": 35,
            "send_ext": 36,
            "send_tape": 37,
            "send_fx1": 38,
            "send_fx2": 39,
            "lfo_dest": 40,
            "lfo_param": 41,
        }
        tracks = doc.get("tracks", [])
        # Determine each track's pattern loop length in bars
        for tr in tracks:
            ch = int(tr.get("midiChannel", 0))
            pat = tr.get("pattern", {})
            length_bars = max(1, int(pat.get("lengthBars", 1)))
            # Base values from ccLanes (simple linear ramp between points within current bar)
            base_values: Dict[int, int] = {}
            cc_lanes = tr.get("ccLanes") or []
            if isinstance(cc_lanes, list):
                for lane in cc_lanes:
                    try:
                        dest = str(lane.get("dest", ""))
                        control = None
                        if dest.startswith("cc:"):
                            control = int(dest.split(":", 1)[1])
                        elif dest.startswith("name:"):
                            control = name_cc.get(dest.split(":", 1)[1])
                        if control is None:
                            continue
                        pts = lane.get("points") or []
                        # Gather points for bar 0 only (MVP). Interpolate across steps of current bar.
                        # Fallback: if no points, skip.
                        if not isinstance(pts, list) or len(pts) == 0:
                            continue
                        # Find two bounding points for current step
                        # Points format: {"t": {"bar": 0, "step": s}, "v": value}
                        s = step_in_bar
                        left_v = None
                        right_v = None
                        left_s = None
                        right_s = None
                        for p in pts:
                            t = p.get("t", {})
                            if int(t.get("bar", 0)) != ((tick // bar_ticks) % length_bars if bar_ticks > 0 else 0):
                                continue
                            ps = int(t.get("step", 0))
                            pv = int(p.get("v", 0))
                            if ps <= s and (left_s is None or ps >= left_s):
                                left_s, left_v = ps, pv
                            if ps >= s and (right_s is None or ps <= right_s):
                                right_s, right_v = ps, pv
                        if left_v is None and right_v is None:
                            continue
                        if left_v is None:
                            base = right_v
                        elif right_v is None or right_s == left_s:
                            base = left_v
                        else:
                            # Linear interpolation between left and right steps
                            frac = (s - left_s) / max(1, (right_s - left_s))
                            base = int(round(left_v + frac * (right_v - left_v)))
                        base_values[int(control)] = max(0, min(127, int(base)))
                    except Exception:
                        continue

            # LFO offsets (triangle only; rate sync values like '1/8' supported minimally)
            lfos = tr.get("lfos") or []
            lfo_offsets: Dict[int, int] = {}
            if isinstance(lfos, list):
                for lf in lfos:
                    try:
                        dest = str(lf.get("dest", ""))
                        control = None
                        if dest.startswith("cc:"):
                            control = int(dest.split(":", 1)[1])
                        elif dest.startswith("name:"):
                            control = name_cc.get(dest.split(":", 1)[1])
                        if control is None:
                            continue
                        depth = int(lf.get("depth", 0))
                        rate = lf.get("rate", {}) or {}
                        sync = rate.get("sync") if isinstance(rate, dict) else None
                        shape = str(lf.get("shape", "triangle"))
                        # Only triangle supported in MVP
                        if shape != "triangle":
                            continue
                        # Compute steps per cycle from sync string like '1/8'
                        steps_per_cycle = 0
                        if isinstance(sync, str) and "/" in sync:
                            # In 4/4 with spb steps per bar, 1/n note = spb/n steps per cycle
                            try:
                                denom = int(sync.split("/", 1)[1])
                                if denom > 0:
                                    steps_per_cycle = max(1, int(spb // denom))
                            except Exception:
                                steps_per_cycle = 0
                        if steps_per_cycle <= 0:
                            # Default to 1/8
                            steps_per_cycle = 2
                        # Triangle from -depth..+depth. Phase resets each bar so use step_in_bar
                        phase = step_in_bar % steps_per_cycle
                        half = steps_per_cycle / 2.0
                        if phase < half:
                            # rising from -1 to +1 across first half
                            norm = (phase / half) * 2 - 1
                        else:
                            # falling from +1 to -1 across second half
                            norm = ((steps_per_cycle - phase) / half) * 2 - 1
                        lfo = int(round(norm * depth))
                        lfo_offsets[int(control)] = lfo
                    except Exception:
                        continue

            # Merge base + lfo offset, clamp
            merged: List[Tuple[int, int]] = []
            all_controls = set(base_values.keys()) | set(lfo_offsets.keys())
            for ctrl in sorted(all_controls):
                base = base_values.get(ctrl, 64)
                off = lfo_offsets.get(ctrl, 0)
                # LFO offset parameter (baseline) if provided on the LFO spec
                # We approximate by looking for any lfo targeting this ctrl and reading its 'offset'
                lfo_offset_baseline = 0
                try:
                    for lf in lfos:
                        d = str(lf.get("dest", ""))
                        c = None
                        if d.startswith("cc:"):
                            c = int(d.split(":", 1)[1])
                        elif d.startswith("name:"):
                            c = name_cc.get(d.split(":", 1)[1])
                        if c == ctrl:
                            lfo_offset_baseline = int(lf.get("offset", 0))
                            break
                except Exception:
                    pass
                value = max(0, min(127, int(lfo_offset_baseline + base + off)))
                merged.append((int(ctrl), value))

            # Apply simple CC rate guards: per-track and global limits per tick
            # Prefer to send earlier controls first; shed extras and count them
            sent_this_tick_global = 0
            for tkey in list(self._cc_sent_tick.keys()) if hasattr(self, "_cc_sent_tick") else []:
                pass
            # Count CCs already sent this tick globally (reset at new tick)
            if not hasattr(self, "_last_cc_tick") or self._last_cc_tick != tick:
                self._last_cc_tick = tick
                self._cc_sent_tick_global = 0
                self._cc_sent_tick_per_track: Dict[int, int] = {}

            for ctrl, value in merged:
                # Check per-track limit
                per_track = self._cc_sent_tick_per_track.get(ch, 0)
                if per_track >= self.cc_limit_per_tick_track or self._cc_sent_tick_global >= self.cc_limit_per_tick_global:
                    self.metrics["shed_cc"] += 1
                    continue
                key = (ch, int(ctrl))
                if self._last_cc.get(key) == value:
                    # unchanged; skip without counting toward limit
                    continue
                # Send CC
                try:
                    self.sink.control_change(ch, int(ctrl), value)
                    self.metrics["msgs_cc"] += 1
                    self._last_cc[key] = value
                    # increment counters
                    self._cc_sent_tick_global += 1
                    self._cc_sent_tick_per_track[ch] = per_track + 1
                except Exception:
                    # treat as shed if send fails
                    self.metrics["shed_cc"] += 1
