import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestExternalTransport(unittest.TestCase):
    def test_external_clock_ratio_maps_to_engine_ticks(self):
        # ppq=96 => ratio = 96/24 = 4 engine ticks per MIDI clock pulse
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {"drumMap": {"kick": 53, "kick_alt": 54, "snare": 55, "snare_alt": 56, "rim": 57, "clap": 58, "tambourine": 59, "shaker": 60, "closed_hat": 61, "open_hat": 62, "pedal_hat": 63, "low_tom": 65, "crash": 66, "mid_tom": 67, "ride": 68, "high_tom": 69, "conga_low": 71, "conga_high": 72, "cowbell": 73, "guiro": 74, "metal": 75, "chi": 76}},
            "tracks": [
                {
                    "id": "t-drums",
                    "name": "Kit",
                    "type": "sampler",
                    "midiChannel": 9,
                    "pattern": {"lengthBars": 1, "steps": []},
                    "drumKit": {
                        "patterns": [{"bar": 1, "key": "kick", "pattern": "x...............", "vel": 120}],
                        "repeatBars": 1,
                        "lengthSteps": 1,
                    },
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        ppq, spb = 96, 16
        step_ticks = int((ppq * 4) / spb)  # 24
        bar_ticks = step_ticks * spb  # 384
        ratio = ppq // 24  # 4
        # Simulate one bar's worth of 24PPQN pulses
        pulses = bar_ticks // ratio  # 96
        start_tick = eng.tick
        for _ in range(pulses):
            for _ in range(ratio):
                eng.on_tick(eng.tick + 1)
        # Expect exactly one kick note_on in the bar
        ons = [e for e in sink.events if e[0] == "on"]
        self.assertEqual(len(ons), 1)

    def test_spp_reposition_maps_to_step_boundary(self):
        # One step at idx 8 should fire when engine.tick is set to that step's tick
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "tracks": [
                {
                    "id": "t1",
                    "name": "Synth",
                    "type": "sampler",
                    "midiChannel": 0,
                    "pattern": {
                        "lengthBars": 1,
                        "steps": [
                            {"idx": 8, "events": [{"pitch": 60, "velocity": 100, "lengthSteps": 1}]}
                        ],
                    },
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        spb = 16
        step_ticks = int((96 * 4) / spb)  # 24
        # MIDI SPP pos is in 1/16 notes; mapping sets eng.tick = pos * (ppq/4)
        # For pos=8, that's 8 * 24 = 192
        eng.tick = 8 * (96 // 4)
        eng.start()
        eng.on_tick(eng.tick)
        ons = [e for e in sink.events if e[0] == "on"]
        self.assertEqual(len(ons), 1)

    def test_continue_does_not_reset_tick(self):
        # Engine.tick should be preserved across stop() and subsequent start() (Continue semantics)
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "tracks": [
                {
                    "id": "t1",
                    "name": "Synth",
                    "type": "sampler",
                    "midiChannel": 0,
                    "pattern": {"lengthBars": 1, "steps": []},
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        # Advance some ticks, then stop and continue
        eng.on_tick(100)
        self.assertEqual(eng.tick, 100)
        eng.stop()
        self.assertEqual(eng.tick, 100)  # stop should not reset tick
        eng.start()  # continue
        self.assertEqual(eng.tick, 100)  # start (continue) should not reset tick
        # Resume ticking from preserved position
        eng.on_tick(101)
        self.assertEqual(eng.tick, 101)
