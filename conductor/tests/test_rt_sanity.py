import unittest

from conductor.midi_engine import Engine, VirtualSink


def make_simple_doc(ppq=96, spb=16, length_bars=1, pitch=60, vel=100, length_steps=1):
    return {
        "version": "opxyloop-1.0",
        "meta": {"tempo": 120, "ppq": ppq, "stepsPerBar": spb},
        "tracks": [
            {
                "id": "t1",
                "name": "Test",
                "type": "sampler",
                "midiChannel": 0,
                "pattern": {
                    "lengthBars": length_bars,
                    "steps": [
                        {"idx": 0, "events": [{"pitch": pitch, "velocity": vel, "lengthSteps": length_steps}]}
                    ],
                },
            }
        ],
    }


class TestRTSanity(unittest.TestCase):
    def test_demo_note_pairing(self):
        sink = VirtualSink()
        eng = Engine(sink)
        doc = make_simple_doc(ppq=96, spb=16, length_bars=1, pitch=60, vel=110, length_steps=1)
        eng.load(doc)
        eng.start()
        # One bar worth of ticks: step_ticks = (96*4)/16 = 24
        step_ticks = int((96 * 4) / 16)
        # Tick 0..(step_ticks): expect on at 0, off at step_ticks
        for t in range(0, step_ticks + 1):
            eng.on_tick(t)
        # Expected sequence: on, off
        types = [e[0] for e in sink.events]
        self.assertIn(("on", 0, 60, 110), sink.events)
        self.assertIn(("off", 0, 60, 0), sink.events)
        self.assertEqual(types.count("on"), 1)
        self.assertEqual(types.count("off"), 1)

    def test_note_off_preserved_on_replace(self):
        sink = VirtualSink()
        eng = Engine(sink)
        doc = make_simple_doc(ppq=96, spb=16, length_bars=1, pitch=60, vel=100, length_steps=1)
        eng.load(doc)
        eng.start()
        step_ticks = int((96 * 4) / 16)
        # Emit on at tick 0
        eng.on_tick(0)
        # Replace doc before off is due
        replacement = make_simple_doc(ppq=96, spb=16, length_bars=1, pitch=64, vel=90, length_steps=1)
        eng.replace_doc(replacement)
        # Advance to off tick for the first note
        for t in range(1, step_ticks + 1):
            eng.on_tick(t)
        # Off for original note must be present
        self.assertIn(("off", 0, 60, 0), sink.events)

    def test_panic_on_stop(self):
        sink = VirtualSink()
        eng = Engine(sink)
        doc = make_simple_doc()
        eng.load(doc)
        eng.start()
        # Start note
        eng.on_tick(0)
        # Stop should flush offs and emit panic
        eng.stop()
        types = [e[0] for e in sink.events]
        self.assertIn("panic", types)
        # After stop, further ticks produce no events
        before = len(sink.events)
        eng.on_tick(1)
        eng.on_tick(2)
        self.assertEqual(before, len(sink.events))


if __name__ == "__main__":
    unittest.main()

