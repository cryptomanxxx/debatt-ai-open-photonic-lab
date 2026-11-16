import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scientific_export import extract

class ScientificExportTests(unittest.TestCase):
    def response(self):
        return {"status": "completed", "id": "private-interaction", "environment_id": "private-environment",
                "steps": [{"type": "thought", "summary": "private thought"},
                          {"type": "code_execution_call", "id": "private-call", "signature": "private-signature",
                           "arguments": {"language": "bash", "code": "python train.py"}},
                          {"type": "code_execution_result", "call_id": "private-call", "is_error": False, "result": "loss=0.1"},
                          {"type": "model_output", "content": [{"type": "text", "text": "Scientific report"}]}]}
    def test_allowlist(self):
        result = extract(self.response(), "AG-PHOTONIC-002", "123")
        self.assertEqual(len(result["execution_evidence"]), 2)
        self.assertEqual(result["reports"][0]["text"], "Scientific report")
        self.assertNotIn("private", str(result))
    def test_reject_sensitive_text(self):
        for value in ("private-interaction", "private-signature", "archive-secret", "AIza" + "a"*35):
            r = self.response()
            r["steps"][-1]["content"][0]["text"] = value
            with self.assertRaises(ValueError):
                extract(r, "AG-PHOTONIC-002", "123", ("archive-secret",))
    def test_reject_incomplete(self):
        r = self.response()
        r["status"] = "active"
        with self.assertRaises(ValueError):
            extract(r, "AG-PHOTONIC-002", "123")
    def test_missing_report(self):
        r = self.response()
        r["steps"].pop()
        with self.assertRaises(ValueError):
            extract(r, "AG-PHOTONIC-002", "123")

    def test_partial_without_final_report(self):
        r = self.response()
        r["status"] = "failed"
        r["steps"].pop()
        result = extract(r, "AG-PHOTONIC-003", "123", allow_partial=True)
        self.assertTrue(result["partial"])
        self.assertEqual(result["response_status"], "failed")
        self.assertEqual(result["reports"], [])
        self.assertEqual(len(result["execution_evidence"]), 2)
        self.assertNotIn("private", str(result))

    def test_partial_unknown_status_is_not_disclosed(self):
        r = self.response()
        r["status"] = "private-unrecognized-value"
        result = extract(r, "AG-PHOTONIC-003", "123", allow_partial=True)
        self.assertEqual(result["response_status"], "unknown")
        self.assertTrue(result["partial"])

    def test_partial_sensitive_nested_id_rejected(self):
        r = self.response()
        r["status"] = "incomplete"
        r["steps"][0]["nested"] = {"id": "nested-private-id"}
        r["steps"][-1]["content"][0]["text"] = "nested-private-id"
        with self.assertRaises(ValueError):
            extract(r, "AG-PHOTONIC-003", "123", allow_partial=True)

    def test_completed_still_requires_report_with_opt_in(self):
        r = self.response()
        r["steps"].pop()
        with self.assertRaises(ValueError):
            extract(r, "AG-PHOTONIC-003", "123", allow_partial=True)
