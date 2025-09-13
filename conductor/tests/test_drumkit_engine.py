import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestDrumKitEngine(unittest.TestCase):
    def _run_ticks(self, eng: Engine, ticks: int):
        for t in range(ticks + 1):
            eng.on_tick(t)

    def test_drumkit_single_bar_hits(self):
        # meta: ppq=96, spb=16 => step_ticks=24, bar_ticks=384
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {"drumMap": {"kick": 36, "snare": 38, "ch": 42}},
            "tracks": [
                {
                    "id": "t-drums",
                    "name": "Kit",
                    "type": "sampler",
                    "midiChannel": 9,
                    "pattern": {"lengthBars": 1, "steps": []},
                    "drumKit": {
                        "patterns": [
                            {"bar": 1, "key": "kick", "pattern": "x...x...x...x...", "vel": 112},
                            {"bar": 1, "key": "snare", "pattern": "....x.......x...", "vel": 104},
                            {"bar": 1, "key": "ch", "pattern": ".x.x.x.x.x.x.x.x", "vel": 80},
                        ],
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
        # Run exactly one bar (exclusive of the next bar start)
        for t in range(bar_ticks):
            eng.on_tick(t)
        # Count kick/snare/hat note-ons
        ons = [e for e in sink.events if e[0] == "on"]
        kick_on = len([e for e in ons if e[2] == 36 and e[1] == 9])
        snare_on = len([e for e in ons if e[2] == 38 and e[1] == 9])
        ch_on = len([e for e in ons if e[2] == 42 and e[1] == 9])
        self.assertEqual(kick_on, 4)
        self.assertEqual(snare_on, 2)
        self.assertEqual(ch_on, 8)

    def test_drumkit_repeat_bars(self):
        # Two bars, repeatBars=2 should apply the same pattern across both
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {"drumMap": {"kick": 36}},
            "tracks": [
                {
                    "id": "t-drums",
                    "name": "Kit",
                    "type": "sampler",
                    "midiChannel": 9,
                    "pattern": {"lengthBars": 2, "steps": []},
                    "drumKit": {
                        "patterns": [{"bar": 1, "key": "kick", "pattern": "x...............", "vel": 120}],
                        "repeatBars": 2,
                        "lengthSteps": 1,
                    },
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        step_ticks = int((96 * 4) / 16)
        bar_ticks = step_ticks * 16
        # run two bars
        total_ticks = step_ticks * 16 * 2
        for t in range(total_ticks):
            eng.on_tick(t)
        ons = [e for e in sink.events if e[0] == "on" and e[2] == 36]
        self.assertEqual(len(ons), 2)

    def test_drumkit_and_steps_coexist(self):
        # Both pattern.steps and drumKit schedule hits at the same tick
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {"drumMap": {"kick": 36}},
            "tracks": [
                {
                    "id": "t-mixed",
                    "name": "Mixed",
                    "type": "sampler",
                    "midiChannel": 0,
                    "pattern": {
                        "lengthBars": 1,
                        "steps": [
                            {"idx": 0, "events": [{"pitch": 60, "velocity": 100, "lengthSteps": 1}]}
                        ],
                    },
                    "drumKit": {"patterns": [{"bar": 1, "key": "kick", "pattern": "x...............", "vel": 120}]},
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        step_ticks = int((96 * 4) / 16)
        for t in range(step_ticks + 1):
            eng.on_tick(t)
        ons = [e for e in sink.events if e[0] == "on"]
        # Expect two note-ons at tick 0: C4 on ch0 and kick on ch0
        self.assertEqual(len(ons), 2)
        pitches = sorted([e[2] for e in ons])
        self.assertEqual(pitches, [36, 60])


if __name__ == "__main__":
    unittest.main()
