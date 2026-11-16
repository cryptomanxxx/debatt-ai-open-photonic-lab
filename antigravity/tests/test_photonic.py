import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("photonic", Path(__file__).resolve().parents[1] / "experiments/AG-PHOTONIC-001/run.py")
photonic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photonic)

class PhotonicTests(unittest.TestCase):
    def test_independent_payload(self):
        self.assertEqual(photonic.PAYLOAD["input"], photonic.PROMPT)
        self.assertNotEqual(photonic.PAYLOAD["input"], photonic.probe.PAYLOAD["input"])
        self.assertEqual(photonic.PAYLOAD["agent_config"], photonic.probe.PAYLOAD["agent_config"])

    @patch.object(photonic.probe.urllib.request, "build_opener")
    def test_dry_run(self, opener):
        self.assertEqual(photonic.probe.main([], payload=photonic.PAYLOAD, result_prefix="AG-PHOTONIC-001"), 0)
        opener.assert_not_called()
