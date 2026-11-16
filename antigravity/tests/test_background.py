import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments/AG-PHOTONIC-001"))
import background
sys.path.pop(0)

class BackgroundTests(unittest.TestCase):
    @patch.object(background.time, "sleep")
    @patch.object(background, "request")
    def test_submit_then_poll(self, request, sleep):
        request.side_effect = [{"id":"abc","status":"in_progress"}, {"id":"abc","status":"completed"}]
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(background.execute("key", Path(d), payload={"background":True}), 0)
            self.assertEqual(json.loads((Path(d)/"latest.json").read_text())["status"], "completed")
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.args, ("key","abc"))

    @patch.object(background, "request")
    def test_retrieve_only(self, request):
        request.return_value = {"id":"abc","status":"in_progress"}
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(background.execute("key", Path(d), interaction_id="abc", polls=0), 0)
            self.assertTrue((Path(d)/"latest.json").exists())
        request.assert_called_once_with("key","abc",None)

    @patch.object(background.time, "sleep")
    @patch.object(background, "request")
    def test_poll_failure_preserves_checkpoint(self, request, sleep):
        request.side_effect = [{"id":"abc","status":"in_progress"}, TimeoutError()]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(TimeoutError):
                background.execute("key", Path(d), payload={"background":True})
            self.assertEqual(json.loads((Path(d)/"latest.json").read_text())["id"], "abc")
        self.assertEqual(request.call_count, 2)

    @patch.object(background, "request", side_effect=TimeoutError())
    def test_no_post_retry(self, request):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(TimeoutError):
                background.execute("key", Path(d), payload={"background":True})
        self.assertEqual(request.call_count, 1)

    def test_invalid_id(self):
        for value in ("../abc", "", None, "a/b"):
            with self.assertRaises(ValueError):
                background.valid_id(value)
