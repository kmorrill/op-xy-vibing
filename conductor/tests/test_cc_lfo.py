import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestCCLFO(unittest.TestCase):
    def _run_ticks(self, eng: Engine, ticks: int):
        for t in range(ticks + 1):
            eng.on_tick(t)

    def test_cc_lane_with_lfo_triangle(self):
        # Minimal doc: 1 bar, 16 steps, ppq=96 => 24 ticks per step
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {},
            "tracks": [
                {
                    "id": "t1",
                    "name": "Synth",
                    "type": "sampler",
                    "midiChannel": 0,
                    "pattern": {"lengthBars": 1, "steps": []},
                    # Ramp cutoff from 40 to 100 over the bar
                    "ccLanes": [
                        {
                            "id": "cutoff-rise",
                            "dest": "name:cutoff",
                            "points": [
                                {"t": {"bar": 0, "step": 0}, "v": 40},
                                {"t": {"bar": 0, "step": 15}, "v": 100},
                            ],
                        }
                    ],
                    # Triangle LFO on resonance at 1/8 with depth 10
                    "lfos": [
                        {"id": "res-wobble", "dest": "name:resonance", "depth": 10, "rate": {"sync": "1/8"}, "shape": "triangle"}
                    ],
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        # One bar worth of ticks: step_ticks=24, bar_ticks=24*16=384
        ppq, spb = 96, 16
        step_ticks = int((ppq * 4) / spb)  # 24
        bar_ticks = step_ticks * spb  # 384
        # Drive through a full bar at step boundaries
        for t in range(0, bar_ticks + 1, step_ticks):
            eng.on_tick(t)
        # Capture CC events
        cc_events = [e for e in sink.events if e[0] == "cc"]
        self.assertGreater(len(cc_events), 4, "should emit multiple CC updates across the bar")
        # Ensure values are clamped to 0..127
        for _, _ch, _ctl, val in cc_events:
            self.assertGreaterEqual(val, 0)
            self.assertLessEqual(val, 127)

    def test_cc_name_maps_and_channel(self):
        # Track on MIDI channel 0 should emit CC32 when using name:cutoff
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "tracks": [
                {
                    "id": "t1",
                    "name": "Track1",
                    "type": "sampler",
                    "midiChannel": 0,
                    "pattern": {"lengthBars": 1, "steps": []},
                    "ccLanes": [
                        {
                            "id": "cutoff-rise",
                            "dest": "name:cutoff",
                            "points": [
                                {"t": {"bar": 0, "step": 0}, "v": 40},
                                {"t": {"bar": 0, "step": 15}, "v": 100},
                            ],
                        }
                    ],
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        step_ticks = int((96 * 4) / 16)  # 24
        bar_ticks = step_ticks * 16      # 384
        for t in range(0, bar_ticks + 1, step_ticks):
            eng.on_tick(t)
        cc_events = [e for e in sink.events if e[0] == "cc"]
        self.assertGreater(len(cc_events), 0, "expected CC events for cutoff lane")
        # Assert all CCs are sent on channel 0 and control 32
        self.assertTrue(all(ch == 0 for _, ch, _ctl, _ in cc_events))
        self.assertTrue(all(ctl == 32 for _, _ch, ctl, _ in cc_events))
