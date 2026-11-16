import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("probe", Path(__file__).resolve().parents[1] / "experiments/AG-INFRA-001/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class ProbeTests(unittest.TestCase):
    @patch.object(probe.urllib.request, "build_opener")
    def test_dry_run_never_networks(self, opener):
        self.assertEqual(probe.main([]), 0)
        opener.assert_not_called()

    @patch.object(probe.urllib.request, "build_opener")
    def test_live_requires_confirmation(self, opener):
        with self.assertRaises(SystemExit):
            probe.main(["--live"])
        opener.assert_not_called()

    @patch.dict(probe.os.environ, {}, clear=True)
    @patch.object(probe.urllib.request, "build_opener")
    def test_missing_key(self, opener):
        with self.assertRaises(SystemExit):
            probe.main(["--live", "--confirm-free-project"])
        opener.assert_not_called()

    def test_payload(self):
        self.assertEqual(probe.PAYLOAD["environment"], "remote")
        self.assertEqual(probe.PAYLOAD["tools"], [{"type": "code_execution"}])
