import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestChordsEngine(unittest.TestCase):
    def test_chord_expansion_absolute_symbol(self):
        # Track 7 (channel 6) plays Cmaj7 chord for 4 steps
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 100, "ppq": 96, "stepsPerBar": 16},
            "tracks": [
                {
                    "id": "t-chords",
                    "name": "Chords",
                    "type": "synth",
                    "midiChannel": 6,
                    "pattern": {"lengthBars": 1, "steps": [
                        {"idx": 0, "events": [{"chord": "Cmaj7", "velocity": 96, "lengthSteps": 4}]}
                    ]},
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        # Tick through one bar
        step_ticks = eng.step_ticks
        bar_ticks = step_ticks * doc["meta"]["stepsPerBar"]
        for t in range(0, bar_ticks + 1):
            eng.on_tick(t)
        # Expect 4 ons at tick 0 on channel 6: C3,E3,G3,B3 (48,52,55,59)
        ons = [(ch, p) for (typ, ch, p, _v) in sink.events if typ == 'on']
        offs = [(ch, p) for (typ, ch, p, _v) in sink.events if typ == 'off']
        expected = {(6, 48), (6, 52), (6, 55), (6, 59)}
        self.assertTrue(expected.issubset(set(ons)), f"missing ons: {expected - set(ons)}")
        # And offs for those
        self.assertTrue(expected.issubset(set(offs)), "missing offs for chord tones")


if __name__ == "__main__":
    unittest.main()

