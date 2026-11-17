import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "reproduction" / "AG-PHOTONIC-003"
sys_path = str(ROOT)
import sys
sys.path.insert(0, sys_path)
try:
    spec = importlib.util.spec_from_file_location("diagnose_recovery", ROOT / "diagnose_recovery.py")
    diag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diag)
finally:
    sys.path.remove(sys_path)

ORIGINAL = {"id": "original-secret-id", "status": "completed", "environment_id": "env-secret-id"}

def response(**kwargs):
    return dict({"id": "recovery-secret-id", "status": "incomplete",
                 "environment_id": "env-secret-id", "steps": []}, **kwargs)

def manifest():
    files = []
    for name in sorted(diag.NAMES):
        data = b"{}" if name == "report.json" else b"# source\n"
        files.append(dict(name=name, base64=base64.b64encode(data).decode(),
                          size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    return dict(files=files, missing=[])

class DiagnosticsTest(unittest.TestCase):
    def test_status_and_usage_without_raw_messages(self):
        r = response(usage={"total_tokens": 100000},
                     incomplete_details={"reason": "max_total_tokens", "message": "private"},
                     error={"message": "private"})
        with patch.object(diag.manager.background, "request") as req:
            result = diag.inspect(r, ORIGINAL, "test-key", "123")
            req.assert_not_called()
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["usage"]["total_tokens"], 100000)
        self.assertEqual(result["incomplete_reason"], "max_total_tokens")
        self.assertTrue(result["same_environment"])
        self.assertNotIn("private", json.dumps(result))
        self.assertNotIn("secret-id", json.dumps(result))

    def test_tool_result_candidate_is_not_published(self):
        m = manifest()
        r = response(steps=[{"type": "code_execution_result", "result": json.dumps(m), "is_error": False}])
        result = diag.inspect(r, ORIGINAL, "test-key", "123")
        self.assertEqual(result["manifest_candidates"], 1)
        self.assertEqual(result["complete_valid_manifest_candidates"], 1)
        self.assertEqual(result["expected_file_mentions"], sorted(diag.NAMES))
        self.assertNotIn(m["files"][0]["base64"], json.dumps(result))

    def test_missing_and_sensitive_candidates(self):
        m = manifest()
        m["files"].pop()
        bad = manifest()
        bad["audit"] = "original-secret-id"
        r = response(steps=[{"type": "model_output", "content": [{"type": "text", "text": json.dumps(m)}, {"type": "text", "text": json.dumps(bad)}]},
                            {"type": "function_result", "is_error": True, "result": "params.py private"}])
        result = diag.inspect(r, ORIGINAL, "test-key", "123")
        self.assertEqual(result["manifest_candidates"], 2)
        self.assertEqual(result["complete_valid_manifest_candidates"], 0)
        self.assertEqual(result["tool_errors"], 1)
        self.assertNotIn("private", json.dumps(result))

    def test_wrong_original(self):
        with self.assertRaises(ValueError):
            diag.inspect(response(), dict(ORIGINAL, status="incomplete"), "test-key", "123")

if __name__ == "__main__":
    unittest.main()
