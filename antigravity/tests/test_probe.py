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

    @patch.dict(probe.os.environ, {"GEMINI_API_KEY": "mock-key"}, clear=True)
    @patch.object(probe.urllib.request, "build_opener")
    def test_live_status_and_saved_response(self, opener):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            fake_file = Path(directory) / "antigravity/experiments/AG-INFRA-001/probe.py"
            fake_file.parent.mkdir(parents=True)
            with patch.object(probe, "__file__", str(fake_file)):
                for payload, expected in [
                    ({"status": "completed"}, 0),
                    ({"status": "failed"}, 1),
                    ({"status": "incomplete"}, 1),
                    ({"status": "in_progress"}, 1),
                    ({}, 1),
                    ([], 1),
                ]:
                    with self.subTest(payload=payload):
                        opener.reset_mock()
                        response = opener.return_value.open.return_value.__enter__.return_value
                        response.read.return_value = json.dumps(payload).encode()
                        results = fake_file.parents[2] / "results"
                        before = set(results.glob("*.json"))
                        self.assertEqual(probe.main(["--live", "--confirm-free-project"]), expected)
                        after = set(results.glob("*.json")) - before
                        self.assertEqual(len(after), 1)
                        self.assertEqual(json.loads(after.pop().read_text()), payload)
                        opener.return_value.open.assert_called_once()

    def test_token_budget(self):
        self.assertEqual(probe.PAYLOAD["agent_config"], {"type": "antigravity", "max_total_tokens": 20000})
