import json
import os
import tempfile
import unittest
from unittest import mock


def make_loop_doc(tempo: float, doc_version: int = 1):
    return {
        "version": "opxyloop-1.0",
        "docVersion": doc_version,
        "meta": {
            "tempo": tempo,
            "ppq": 96,
            "stepsPerBar": 16,
        },
        "tracks": [
            {
                "id": "trk-1",
                "name": "Test",
                "type": "sampler",
                "midiChannel": 0,
                "pattern": {
                    "lengthBars": 1,
                    "steps": [
                        {
                            "idx": 0,
                            "events": [
                                {
                                    "pitch": 60,
                                    "velocity": 100,
                                    "lengthSteps": 1,
                                }
                            ],
                        }
                    ],
                },
            }
        ],
    }


class DummyOut:
    def send(self, *_args, **_kwargs):
        pass


class DummyIn:
    def close(self):
        pass


class FakeClock:
    def __init__(self, bpm, tick_handler, send_midi_clock=None):
        self.bpm = float(bpm)
        self.tick_handler = tick_handler
        self.send_midi_clock = send_midi_clock
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def set_bpm(self, bpm):
        self.bpm = float(bpm)

    def get_metrics(self):
        return {}


class TestTempoSync(unittest.TestCase):
    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False)

    def tearDown(self):
        try:
            self.tempfile.close()
        except Exception:
            pass
        try:
            os.unlink(self.tempfile.name)
        except Exception:
            pass

    def write_doc(self, doc):
        self.tempfile.seek(0)
        self.tempfile.truncate()
        json.dump(doc, self.tempfile)
        self.tempfile.flush()

    def test_tempo_change_triggers_cc_command(self):
        initial_doc = make_loop_doc(tempo=120.0, doc_version=4)
        self.write_doc(initial_doc)
        dummy_out = DummyOut()
        dummy_in = DummyIn()
        fake_mido = mock.Mock()
        fake_mido.Message = mock.Mock()
        with mock.patch.dict("sys.modules", {"mido": fake_mido}):
            with mock.patch("conductor.conductor_server.open_mido_output", return_value=dummy_out):
                with mock.patch("conductor.conductor_server.open_mido_input", return_value=dummy_in):
                    from conductor.conductor_server import Conductor

                    with mock.patch.object(Conductor, "do_set_tempo_cc", autospec=True) as mock_cc:
                        conductor = Conductor(self.tempfile.name, port_filter=None, bpm=120.0, clock_source="external")
                        mock_cc.reset_mock()
                        updated_doc = make_loop_doc(tempo=76.0, doc_version=4)
                        res = conductor.do_replace_json(conductor.doc_version, updated_doc)
                        self.assertTrue(res.get("ok"))
                        mock_cc.assert_called_once()
                        mock_cc.assert_called_with(conductor, 76.0)

    def test_internal_clock_updates_and_cc_command(self):
        initial_doc = make_loop_doc(tempo=120.0, doc_version=2)
        self.write_doc(initial_doc)
        dummy_out = DummyOut()
        dummy_in = DummyIn()
        fake_mido = mock.Mock()
        fake_mido.Message = mock.Mock()
        with mock.patch.dict("sys.modules", {"mido": fake_mido}):
            with mock.patch("conductor.conductor_server.open_mido_output", return_value=dummy_out):
                with mock.patch("conductor.conductor_server.open_mido_input", return_value=dummy_in):
                    with mock.patch("conductor.conductor_server.InternalClock", side_effect=lambda *a, **kw: FakeClock(*a, **kw)):
                        from conductor.conductor_server import Conductor

                        with mock.patch.object(Conductor, "do_set_tempo_cc", autospec=True) as mock_cc:
                            with mock.patch.object(Conductor, "do_set_tempo", autospec=True) as mock_set_tempo:
                                conductor = Conductor(self.tempfile.name, port_filter=None, bpm=120.0, clock_source="internal")
                                mock_cc.reset_mock()
                                mock_set_tempo.reset_mock()
                                updated_doc = make_loop_doc(tempo=90.0, doc_version=2)
                                res = conductor.do_replace_json(conductor.doc_version, updated_doc)
                                self.assertTrue(res.get("ok"))
                                mock_set_tempo.assert_called_once()
                                mock_set_tempo.assert_called_with(conductor, 90.0)
                                mock_cc.assert_called_once()
                                mock_cc.assert_called_with(conductor, 90.0)


if __name__ == "__main__":
    unittest.main()
