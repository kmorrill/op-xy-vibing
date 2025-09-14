import unittest

from conductor.patch_utils import apply_patch
from conductor.validator import validate_loop


class TestPatchUtils(unittest.TestCase):
    def test_apply_patch_changes_velocity(self):
        doc = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
            "tracks": [
                {
                    "id": "t1",
                    "name": "Test",
                    "type": "sampler",
                    "midiChannel": 0,
                    "pattern": {
                        "lengthBars": 1,
                        "steps": [
                            {"idx": 0, "events": [{"pitch": 60, "velocity": 64, "lengthSteps": 1}]}
                        ],
                    },
                }
            ],
        }
        ops = [
            {"op": "replace", "path": "/tracks/0/pattern/steps/0/events/0/velocity", "value": 100}
        ]
        patched = apply_patch(doc, ops)
        self.assertEqual(patched["tracks"][0]["pattern"]["steps"][0]["events"][0]["velocity"], 100)
        # Validate remains spec-compliant
        errors = validate_loop(patched)
        self.assertEqual(errors, [])

