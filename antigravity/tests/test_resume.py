import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("resume", Path(__file__).resolve().parents[1] / "experiments/AG-PHOTONIC-001/resume.py")
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)

class ResumeTests(unittest.TestCase):
    def test_payload(self):
        p = resume.build_payload("v1_example", "abc123")
        self.assertEqual(p["previous_interaction_id"], "v1_example")
        self.assertEqual(p["environment"], "abc123")
        self.assertEqual(p["agent_config"]["max_total_tokens"], 200000)

    def test_budget(self):
        self.assertEqual(resume.build_payload("id", "env", 50000)["agent_config"]["max_total_tokens"], 50000)
        for budget in (0, 19999, 200001, True, 50000.5):
            with self.assertRaises(ValueError):
                resume.build_payload("id", "env", budget)

    def test_reject_missing_or_new_environment(self):
        for pair in [(None, "abc"), ("id", None), ("id", "remote"), ("id", "local"), ("id", "bad\nvalue")]:
            with self.assertRaises(ValueError):
                resume.build_payload(*pair)

    @patch.dict("os.environ", {"AG_PREVIOUS_INTERACTION_ID": "v1_example", "AG_ENVIRONMENT_ID": "abc123"})
    @patch.object(resume.photonic.probe, "main")
    def test_offline(self, runner):
        self.assertEqual(resume.main([]), 0)
        runner.assert_not_called()

    @patch.dict("os.environ", {"AG_PREVIOUS_INTERACTION_ID": "v1_example", "AG_ENVIRONMENT_ID": "abc123"})
    @patch.object(resume.photonic.probe, "main", return_value=0)
    def test_live_delegates_confirmation(self, runner):
        self.assertEqual(resume.main(["--live"]), 0)
        self.assertEqual(runner.call_args.args[0], ["--live"])
        self.assertEqual(runner.call_args.kwargs["timeout"], 1800)
