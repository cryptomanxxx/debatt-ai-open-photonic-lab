import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scientific_export import diagnostics

class UsageDiagnosticsTests(unittest.TestCase):
    def test_usage(self):
        result = diagnostics({"status": "incomplete", "agent_config": {"max_total_tokens": 200000},
            "usage": {"total_tokens": 900000, "total_cached_tokens": 700000},
            "error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "private"},
            "incomplete_details": {"reason": "rate_limit"}}, "AG-PHOTONIC-003", "123")
        self.assertEqual(result["max_total_tokens"], 200000)
        self.assertEqual(result["usage"]["total_tokens"], 900000)
        self.assertEqual(result["error_code"], 429)
        self.assertEqual(result["incomplete_reason"], "rate_limit")
        self.assertNotIn("private", str(result))
    def test_missing_and_untrusted(self):
        result = diagnostics({"status": ["private"], "usage": {"total_tokens": True,
            "total_input_tokens": -1, "total_cached_tokens": "private"},
            "agent_config": [], "error": {"status": "private", "code": 10**13},
            "incomplete_details": {"reason": "private"}}, "AG-PHOTONIC-003", "123")
        self.assertEqual(result["status"], "unknown")
        self.assertTrue(all(v is None for v in result["usage"].values()))
        self.assertIsNone(result["max_total_tokens"])
        self.assertIsNone(result["error_code"])
        self.assertNotIn("private", str(result))
