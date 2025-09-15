import unittest

from conductor.midi_engine import Engine, VirtualSink


class TestNoteEventFields(unittest.TestCase):
    def _mk_engine(self):
        sink = VirtualSink()
        eng = Engine(sink)
        return sink, eng

    def test_degree_mapping_major_and_gate(self):
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16, "key": "C", "mode": "major"},
            "tracks": [{
                "id":"t","name":"t","type":"synth","midiChannel":3,
                "pattern":{"lengthBars":1,"steps":[{"idx":0,"events":[{"degree":1,"octaveOffset":0,"velocity":100,"lengthSteps":2,"gate":0.5}]}]}
            }]
        }
        sink, eng = self._mk_engine(); eng.load(doc); eng.start()
        spb = doc["meta"]["stepsPerBar"]
        step_ticks = eng.step_ticks; bar_ticks = step_ticks*spb
        for t in range(0, bar_ticks+1): eng.on_tick(t)
        ons = [e for e in sink.events if e[0]=='on']
        offs = [e for e in sink.events if e[0]=='off']
        # C major degree 1 root at octave 3 => C3=48
        self.assertTrue(any(ch==3 and p==48 for (_,ch,p,_v) in ons))
        self.assertTrue(any(ch==3 and p==48 for (_,ch,p,_v) in offs))

    def test_microshift_and_ratchet(self):
        doc = {
            "version":"opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "tracks": [{
                "id":"t","name":"t","type":"synth","midiChannel":3,
                "pattern":{"lengthBars":1,"steps":[{"idx":0,"events":[{"pitch":60,"velocity":100,"lengthSteps":1,"microshiftMs":10,"ratchet":4}]}]}
            }]
        }
        sink, eng = self._mk_engine(); eng.load(doc); eng.start()
        step_ticks = eng.step_ticks; bar_ticks = step_ticks*doc["meta"]["stepsPerBar"]
        # Walk ticks and watch when ons appear
        count_before = len([e for e in sink.events if e[0]=='on'])
        fired_at = None
        for t in range(0, bar_ticks):
            eng.on_tick(t)
            n = len([e for e in sink.events if e[0]=='on'])
            if n>count_before:
                fired_at = t; break
        self.assertIsNotNone(fired_at)
        # Ratchet=4 should emit 4 ons overall
        for t in range(fired_at+1, fired_at + step_ticks + 5):
            eng.on_tick(t)
        ons = [e for e in sink.events if e[0]=='on']
        self.assertGreaterEqual(len(ons), 4)

    def test_probability_zero_skips(self):
        doc = {
            "version":"opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "tracks": [{
                "id":"t","name":"t","type":"synth","midiChannel":3,
                "pattern":{"lengthBars":1,"steps":[{"idx":0,"events":[{"pitch":60,"velocity":100,"lengthSteps":1,"prob":0.0}]}]}
            }]
        }
        sink, eng = self._mk_engine(); eng.load(doc); eng.start()
        step_ticks = eng.step_ticks; bar_ticks = step_ticks*doc["meta"]["stepsPerBar"]
        for t in range(0, bar_ticks+1): eng.on_tick(t)
        ons = [e for e in sink.events if e[0]=='on']
        self.assertEqual(len(ons), 0)

if __name__ == "__main__":
    unittest.main()

