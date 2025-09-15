import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestChordsRoman(unittest.TestCase):
    def test_roman_progression_one_beat_each(self):
        # I -> II -> III -> iv, one beat (4 steps) each, C major key context
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 100, "ppq": 96, "stepsPerBar": 16, "key": "C", "mode": "major"},
            "tracks": [
                {
                    "id": "t-chords",
                    "name": "Chords",
                    "type": "synth",
                    "midiChannel": 6,
                    "pattern": {"lengthBars": 1, "steps": [
                        {"idx": 0,  "events": [{"chord": "I",   "velocity": 100, "lengthSteps": 4}]},
                        {"idx": 4,  "events": [{"chord": "II",  "velocity": 100, "lengthSteps": 4}]},
                        {"idx": 8,  "events": [{"chord": "III", "velocity": 100, "lengthSteps": 4}]},
                        {"idx": 12, "events": [{"chord": "iv",  "velocity": 100, "lengthSteps": 4}]},
                    ]},
                }
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        step_ticks = eng.step_ticks
        # Tick across the bar
        for t in range(0, 16 * step_ticks + 1):
            eng.on_tick(t)
        # Collect ons grouped by step index
        ons = [(t, ch, p) for (typ, ch, p, _v) in sink.events for t in [0] if typ == 'on']
        # Expected roots at octave 3 (C3=48): I=C, II=D, III=E, iv=F
        expected_roots = {0: 48, 4: 50, 8: 52, 12: 53}
        # Verify at least root tones occurred on channel 6; fuller triads also present
        # Since we didn't record tick times in VirtualSink, we can validate presence of pitch classes
        has = set(p for (_t, _ch, p) in ons if _ch == 6)
        for root in expected_roots.values():
            self.assertIn(root, has)


if __name__ == "__main__":
    unittest.main()

