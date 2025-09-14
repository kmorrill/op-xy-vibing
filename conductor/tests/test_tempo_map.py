import unittest

from conductor.tempo_map import bpm_to_cc80, cc80_to_bpm


class TestTempoMap(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual(bpm_to_cc80(40), 0)
        self.assertEqual(bpm_to_cc80(220), 127)
        self.assertEqual(bpm_to_cc80(20), 0)   # clamp low
        self.assertEqual(bpm_to_cc80(300), 127)  # clamp high

    def test_roundtrip_mid(self):
        # Midpoint around 130 BPM should round to near 130 after mapping back
        cc = bpm_to_cc80(130)
        bpm = cc80_to_bpm(cc)
        self.assertTrue(129.0 <= bpm <= 131.5)

