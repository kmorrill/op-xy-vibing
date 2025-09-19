import unittest

from conductor.tempo_map import bpm_to_cc80, cc80_to_bpm


class TestTempoMap(unittest.TestCase):
    def test_mapping_clamps(self):
        self.assertEqual(bpm_to_cc80(-10), 0)  # clamp low
        self.assertEqual(bpm_to_cc80(0), 0)
        self.assertEqual(bpm_to_cc80(120), 60)
        self.assertEqual(bpm_to_cc80(260), 127)  # clamp high

    def test_roundtrip_mid(self):
        cc = bpm_to_cc80(138)
        bpm = cc80_to_bpm(cc)
        self.assertEqual(bpm, cc * 2.0)
