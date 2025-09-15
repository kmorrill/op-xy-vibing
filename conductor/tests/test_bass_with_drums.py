import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestBassWithDrums(unittest.TestCase):
    def test_bass_and_drumkit_schedule_together(self):
        # One-bar drumkit with kick on 1 & 9; bass plays E2 at start, length 4 steps
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 100, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {"drumMap": {"kick": 53}},
            "tracks": [
                {
                    "id": "t-drums",
                    "midiChannel": 0,
                    "pattern": {"lengthBars": 1, "steps": []},
                    "drumKit": {"patterns": [{"bar": 1, "key": "kick", "pattern": "x.......x.......", "vel": 120}]},
                },
                {
                    "id": "t-bass",
                    "midiChannel": 2,
                    "pattern": {"lengthBars": 1, "steps": [{"idx": 0, "events": [{"pitch": 40, "velocity": 100, "lengthSteps": 4}]}]},
                },
            ],
        }
        sink = VirtualSink()
        eng = Engine(sink)
        eng.load(doc)
        eng.start()
        # Simulate one bar of ticks
        step_ticks = eng.step_ticks
        bar_ticks = step_ticks * doc["meta"]["stepsPerBar"]
        # Tick 0 -> both drum kick and bass note-on
        eng.on_tick(0)
        # Advance a few steps and trigger offs appropriately
        for t in range(1, bar_ticks + 1):
            eng.on_tick(t)
        # Verify both notes were sent on channel 0 (kick) and 2 (bass)
        ons = [e for e in sink.events if e[0] == 'on']
        offs = [e for e in sink.events if e[0] == 'off']
        self.assertTrue(any(ch==0 and pitch==53 for _, ch, pitch, _ in ons), 'kick on missing')
        self.assertTrue(any(ch==2 and pitch==40 for _, ch, pitch, _ in ons), 'bass on missing')
        # Bass off should occur after 4 steps
        self.assertTrue(any(ch==2 and pitch==40 for _, ch, pitch, _ in offs), 'bass off missing')


if __name__ == "__main__":
    unittest.main()

