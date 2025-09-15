from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import random


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
        # Deterministic RNG for probability-based events
        self._rng = random.Random(0)

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

    def get_cc_snapshot(self) -> Dict[int, Dict[int, int]]:
        out: Dict[int, Dict[int, int]] = {}
        for (ch, ctrl), val in self._last_cc.items():
            out.setdefault(int(ch), {})[int(ctrl)] = int(val)
        return out

    def get_active_notes_snapshot(self) -> Dict[int, Dict[str, Any]]:
        """Return current active notes per channel with simple stats."""
        summary: Dict[int, Dict[str, Any]] = {}
        for (ch, pitch), stack in self.active.items():
            ent = summary.setdefault(int(ch), {"count": 0, "pitches": []})
            ent["count"] = int(ent.get("count", 0)) + len(stack)
            if pitch not in ent["pitches"]:
                ent["pitches"].append(int(pitch))
        # sort pitches for stable UI
        for ch, ent in summary.items():
            ent["pitches"].sort()
        return summary

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
                period = max(1, bar_ticks * length_bars)
                step_tick = (idx % (spb * length_bars)) * self.step_ticks
                tick_in_loop = tick % period
                # Handle events with microshift/ratchet: compute exact scheduled tick per event
                events = st.get("events", [])
                for e in events:
                        # Probability
                        prob = float(e.get("prob", 1.0))
                        if prob <= 0:
                            continue
                        if prob < 1.0 and self._rng.random() > prob:
                            continue

                        vel = int(e.get("velocity", 100))
                        ls = int(e.get("lengthSteps", 1))
                        gate = float(e.get("gate", 1.0))
                        ratchet = int(e.get("ratchet", 1) or 1)
                        micro_ms = int(e.get("microshiftMs", 0) or 0)
                        bpm = float(meta.get("tempo", 120))
                        ppq = int(meta.get("ppq", 96))
                        # ticks per ms = (ppq * bpm / 60) / 1000
                        tpm = (ppq * bpm) / 60000.0
                        offset_ticks = int(round(micro_ms * tpm))
                        scheduled_tick = (step_tick + offset_ticks) % period
                        if tick_in_loop != scheduled_tick:
                            continue

                        base_len = max(1, int(self.step_ticks * ls * gate))

                        # Resolve pitches from pitch|degree|chord
                        pitches: List[int] = []
                        if isinstance(e.get("pitch"), (int, float)):
                            pitches = [int(e.get("pitch"))]
                        elif isinstance(e.get("degree"), (int, float)):
                            pitches = [self._degree_to_pitch(int(e.get("degree")), int(e.get("octaveOffset", 0))) ]
                        elif isinstance(e.get("chord"), str):
                            pitches = self._expand_chord(str(e.get("chord")), e)
                        else:
                            continue

                        reps = max(1, ratchet)
                        seg = max(1, base_len // reps)
                        for r_i in range(reps):
                            on_tick_abs = tick + (r_i * seg)
                            off_tick = on_tick_abs + seg
                            for p in pitches:
                                pitch = max(0, min(127, int(p)))
                                note_id = self._next_note_id
                                self._next_note_id += 1
                                self.sink.note_on(ch, pitch, vel)
                                self.metrics["msgs_note_on"] += 1
                                key = (ch, pitch)
                                self.active.setdefault(key, []).append(
                                    NoteEvent(channel=ch, pitch=pitch, velocity=vel, on_tick=on_tick_abs, off_tick=off_tick, note_id=note_id)
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
        # Compute positions for this absolute tick
        step_in_bar = (tick % bar_ticks) // self.step_ticks if bar_ticks > 0 else 0
        # Reset LFO phase on first bar boundary after start
        if step_in_bar == 0 and self._started:
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
            # Base values from ccLanes — high-resolution per tick with interpolation
            base_values: Dict[int, int] = {}
            base_value_channel_override: Dict[int, int] = {}
            cc_lanes = tr.get("ccLanes") or []
            if isinstance(cc_lanes, list):
                for lane in cc_lanes:
                    try:
                        dest = str(lane.get("dest", ""))
                        # Resolve control number
                        control: int | None = None
                        if isinstance(lane.get("dest"), int):
                            control = int(lane.get("dest"))
                        elif dest.startswith("cc:"):
                            control = int(dest.split(":", 1)[1])
                        elif dest.startswith("name:"):
                            control = name_cc.get(dest.split(":", 1)[1])
                        if control is None:
                            continue
                        pts = lane.get("points") or []
                        if not isinstance(pts, list) or len(pts) == 0:
                            continue
                        # Convert points to absolute tick positions within the pattern period
                        period = max(1, bar_ticks * length_bars)
                        pts_conv: List[Tuple[int, int, str]] = []  # (tick_in_period, value, curve)
                        for p in pts:
                            t = p.get("t", {}) or {}
                            v = int(p.get("v", 0))
                            curve = str(p.get("curve", "linear"))
                            if isinstance(t.get("ticks"), (int, float)):
                                tt = int(t.get("ticks")) % period
                            else:
                                b = int(t.get("bar", 0))
                                s = int(t.get("step", 0))
                                tt = ((b % max(1, length_bars)) * bar_ticks + (s % spb) * self.step_ticks) % period
                            pts_conv.append((tt, max(0, min(127, v)), curve))
                        if not pts_conv:
                            continue
                        pts_conv.sort(key=lambda x: x[0])
                        pos = tick % period
                        # Find left and right points bracketing pos (circular)
                        left_i = None
                        for i, (tt, _vv, _cv) in enumerate(pts_conv):
                            if tt <= pos:
                                left_i = i
                            else:
                                break
                        if left_i is None:
                            left_i = len(pts_conv) - 1
                        right_i = (left_i + 1) % len(pts_conv)
                        t_left, v_left, curve_left = pts_conv[left_i]
                        t_right, v_right, _curve_right = pts_conv[right_i]
                        if lane.get("mode") == "hold":
                            base_val = v_left
                        else:
                            # Interpolate across segment duration with easing
                            if t_right == t_left:
                                frac = 0.0
                                seg = period
                            else:
                                seg = (t_right - t_left) if t_right > t_left else (t_right + period - t_left)
                                prog = (pos - t_left) if pos >= t_left else (pos + period - t_left)
                                frac = max(0.0, min(1.0, prog / max(1, seg)))
                            mode = str(lane.get("mode", "points"))
                            curve_kind = str(curve_left or "linear").lower()
                            # Map frac through curve
                            if mode == "ramp" and curve_kind == "linear":
                                eased = frac
                            else:
                                if curve_kind in ("linear", "line"):
                                    eased = frac
                                elif curve_kind in ("exp", "exponential"):
                                    eased = frac * frac
                                elif curve_kind in ("log", "logarithmic"):
                                    eased = (frac ** 0.5)
                                elif curve_kind in ("s-curve", "scurve", "smoothstep"):
                                    eased = (3 * (frac ** 2) - 2 * (frac ** 3))
                                else:
                                    eased = frac
                            base_val = int(round(v_left + (v_right - v_left) * eased))
                        # Apply optional lane range clamp, then 0..127
                        rng = lane.get("range")
                        if isinstance(rng, list) and len(rng) == 2:
                            try:
                                lo = int(rng[0]); hi = int(rng[1])
                                if lo > hi:
                                    lo, hi = hi, lo
                                base_val = max(lo, min(hi, base_val))
                            except Exception:
                                pass
                        base_values[int(control)] = max(0, min(127, int(base_val)))
                        # Optional per-lane MIDI channel override
                        if isinstance(lane.get("channel"), int) and 0 <= int(lane.get("channel")) <= 15:
                            base_value_channel_override[int(control)] = int(lane.get("channel"))
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
                        # Triangle from -depth..+depth. Phase resets each bar
                        # Use fractional position within the current bar cycle
                        phase = (tick // max(1, self.step_ticks)) % steps_per_cycle
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
                send_ch = int(base_value_channel_override.get(ctrl, ch))
                per_track = self._cc_sent_tick_per_track.get(send_ch, 0)
                if per_track >= self.cc_limit_per_tick_track or self._cc_sent_tick_global >= self.cc_limit_per_tick_global:
                    self.metrics["shed_cc"] += 1
                    continue
                key = (send_ch, int(ctrl))
                if self._last_cc.get(key) == value:
                    # unchanged; skip without counting toward limit
                    continue
                # Send CC
                try:
                    self.sink.control_change(send_ch, int(ctrl), value)
                    self.metrics["msgs_cc"] += 1
                    self._last_cc[key] = value
                    # increment counters
                    self._cc_sent_tick_global += 1
                    self._cc_sent_tick_per_track[send_ch] = per_track + 1
                except Exception:
                    # treat as shed if send fails
                    self.metrics["shed_cc"] += 1

    # --- Helpers: chord expansion ---
    @staticmethod
    def _note_name_to_midi(name: str) -> int | None:
        """Parse a note name like 'C3' or 'G#4' -> MIDI number. Returns None if invalid.

        Assumes C4 = 60.
        """
        if not isinstance(name, str) or len(name) < 2:
            return None
        name = name.strip()
        letter = name[0].upper()
        if letter not in "CDEFGAB":
            return None
        i = 1
        accidental = 0
        if i < len(name) and name[i] in ("#", "b"):
            accidental = 1 if name[i] == "#" else -1
            i += 1
        try:
            octave = int(name[i:])
        except Exception:
            return None
        semitones = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter]
        return 12 * (octave + 1) + semitones + accidental  # MIDI: C-1 = 0

    @staticmethod
    def _parse_chord_symbol(sym: str) -> tuple[int, List[int]] | None:
        """Very small chord parser for absolute symbols like 'Cmaj7', 'Am', 'G7', 'Dsus4'.

        Returns (root_midi_base, intervals). The root midi base is at octave 3 (C3=48).
        Intervals are semitone offsets from the root.
        """
        if not isinstance(sym, str) or len(sym) < 1:
            return None
        s = sym.strip()
        # Root
        root_letter = s[0].upper()
        if root_letter not in "CDEFGAB":
            return None
        idx = 1
        accidental = 0
        if idx < len(s) and s[idx] in ("#", "b"):
            accidental = 1 if s[idx] == "#" else -1
            idx += 1
        qual = s[idx:].lower()
        # Map of quality -> intervals
        triads = {
            "": [0, 4, 7],
            "maj": [0, 4, 7],
            "m": [0, 3, 7],
            "min": [0, 3, 7],
            "dim": [0, 3, 6],
            "sus2": [0, 2, 7],
            "sus4": [0, 5, 7],
        }
        sevenths = {
            "7": [0, 4, 7, 10],
            "maj7": [0, 4, 7, 11],
            "m7": [0, 3, 7, 10],
            "min7": [0, 3, 7, 10],
        }
        intervals: List[int] | None = None
        # exact match quality
        if qual in triads:
            intervals = triads[qual]
        elif qual in sevenths:
            intervals = sevenths[qual]
        else:
            # Try to strip common suffixes
            for k, iv in list(sevenths.items()) + list(triads.items()):
                if qual == k:
                    intervals = iv; break
            # Fallback: treat unknown quality as major triad
            if intervals is None:
                intervals = triads[""]
        root_pc = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[root_letter] + accidental
        root_base = 48 + root_pc  # C3 base
        return root_base, intervals

    def _key_to_pc(self, key: str) -> int | None:
        if not isinstance(key, str) or len(key) < 1:
            return None
        k = key.strip()
        letter = k[0].upper()
        if letter not in "CDEFGAB":
            return None
        accidental = 0
        if len(k) >= 2 and k[1] in ("#", "b"):
            accidental = 1 if k[1] == "#" else -1
        base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter]
        return (base + accidental) % 12

    def _parse_roman_chord(self, sym: str) -> tuple[int, List[int]] | None:
        """Parse a simple roman numeral chord (I..VII, i..vii) relative to meta.key/mode.

        Uppercase -> major triad, lowercase -> minor triad. Optional '7' not handled in MVP.
        Returns (root_midi_base, intervals). Root base is in octave 3 aligned to key tonic.
        """
        if not isinstance(sym, str) or len(sym) == 0:
            return None
        s = sym.strip()
        # Extract roman numeral letters at start
        rn = ""
        for ch in s:
            if ch in "ivIV":
                rn += ch
            else:
                break
        if not rn:
            return None
        is_major_quality = rn.isupper()
        # Map roman to degree 1..7
        roman_map = {
            "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
            "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
        }
        deg = roman_map.get(rn)
        if not deg:
            return None
        # Determine key pitch-class and scale degrees by mode
        key_pc = self._key_to_pc(str((self.meta or {}).get("key", "C")))
        if key_pc is None:
            key_pc = 0
        mode = str((self.meta or {}).get("mode", "major")).lower()
        if mode == "minor":
            scale = [0, 2, 3, 5, 7, 8, 10]
        else:
            scale = [0, 2, 4, 5, 7, 9, 11]
        # Degree-1 => scale[0]
        root_pc = (key_pc + scale[(deg - 1) % 7]) % 12
        # Place tonic C3 at 48, so key tonic base = 48 + key_pc
        tonic_base = 48 + key_pc
        # Choose base for root within octave 3
        root_base = 48 + root_pc
        # Choose quality intervals
        intervals = [0, 4, 7] if is_major_quality else [0, 3, 7]
        return root_base, intervals

    def _expand_chord(self, sym: str, event: Dict[str, Any]) -> List[int]:
        """Expand chord string to MIDI pitches. MVP: absolute chord symbols only.

        Honors optional 'register': [low, high] note names to clamp/increase octaves.
        Ignores inversion/omit/roll for MVP.
        """
        out: List[int] = []
        parsed = self._parse_chord_symbol(sym)
        if not parsed:
            # Try roman numerals relative to key/mode
            parsed = self._parse_roman_chord(sym)
        if not parsed:
            return out
        base, intervals = parsed
        # Optional register bounds
        low = None; high = None
        reg = event.get("register")
        if isinstance(reg, list) and len(reg) == 2:
            low = self._note_name_to_midi(str(reg[0]))
            high = self._note_name_to_midi(str(reg[1]))
        for iv in intervals:
            p = base + int(iv)
            # Keep within register by nudging octaves
            if low is not None and p < low:
                while p < low:
                    p += 12
            if high is not None and p > high:
                while p > high:
                    p -= 12
            out.append(p)
        # Ensure ascending order for determinism
        out.sort()
        return out

    def _key_to_pc(self, key: str) -> int | None:
        if not isinstance(key, str) or len(key) < 1:
            return None
        k = key.strip()
        letter = k[0].upper()
        if letter not in "CDEFGAB":
            return None
        accidental = 0
        if len(k) >= 2 and k[1] in ("#", "b"):
            accidental = 1 if k[1] == "#" else -1
        base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter]
        return (base + accidental) % 12

    def _degree_to_pitch(self, degree: int, octave_offset: int) -> int:
        degree = max(1, min(7, int(degree)))
        key_pc = self._key_to_pc(str((self.meta or {}).get("key", "C"))) or 0
        mode = str((self.meta or {}).get("mode", "major")).lower()
        scale = [0, 2, 4, 5, 7, 9, 11] if mode != "minor" else [0, 2, 3, 5, 7, 8, 10]
        pc = (key_pc + scale[(degree - 1) % 7]) % 12
        base = 48 + pc
        return base + 12 * int(octave_offset)
