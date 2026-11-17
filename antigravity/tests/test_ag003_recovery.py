import base64
import hashlib
import importlib.util
from pathlib import Path
import unittest
import json
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "reproduction" / "AG-PHOTONIC-003"

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

extract = load("extract_workspace")
recover = load("recover_workspace")

def manifest():
    files = []
    for name in sorted(extract.NAMES):
        data = b"{}" if name == "report.json" else b"# source\n"
        files.append(dict(name=name, base64=base64.b64encode(data).decode(),
                          size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    return dict(files=files, missing=[])

class RecoveryTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(set(extract.validate(manifest())), extract.NAMES)
    def test_reject_incomplete(self):
        m = manifest()
        m["files"].pop()
        with self.assertRaises(ValueError):
            extract.validate(m)
    def test_reject_digest(self):
        m = manifest()
        m["files"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            extract.validate(m)
    def test_reject_path(self):
        m = manifest()
        m["files"][0]["name"] = "../escape.py"
        with self.assertRaises(ValueError):
            extract.validate(m)
    def test_reject_decoded_secret(self):
        with self.assertRaises(ValueError):
            extract.validate(manifest(), ("source",))
    def test_nested_identifiers_from_both_responses(self):
        blocked = extract.identifiers({"id": "original-id", "steps": [{"call_id": "nested-call"}]},
                                      {"previous_interaction_id": "original-id", "steps": [{"signature": "nested-signature"}]})
        self.assertEqual(blocked, {"original-id", "nested-call", "nested-signature"})
        m = manifest()
        item = next(x for x in m["files"] if x["name"] == "report.json")
        data = b'{"value":"nested-call"}'
        item.update(base64=base64.b64encode(data).decode(), size_bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaises(ValueError):
            extract.validate(m, blocked)
    def test_metadata_preserves_evidence_and_integrity(self):
        m = manifest()
        m.update(dependencies={"numpy": "version"}, required_inputs=["input.csv"],
                 energy_audit={"previous": "assert x", "final": "assert y"})
        evidence = json.loads(extract.metadata(m))
        self.assertEqual(evidence["energy_audit"], m["energy_audit"])
        self.assertEqual(evidence["dependencies"], m["dependencies"])
        self.assertEqual(evidence["required_inputs"], m["required_inputs"])
        self.assertEqual(len(evidence["file_integrity"]), 7)
        self.assertNotIn("files", evidence)
        self.assertNotIn("base64", evidence["file_integrity"][0])
        m["energy_audit"]["final"] = "nested-signature"
        with self.assertRaises(ValueError):
            extract.metadata(m, ("nested-signature",))
    def test_retrieve_only_get_and_preserve_checkpoint(self):
        parent = {"id": "original", "status": "completed", "environment_id": "env"}
        current = {"id": "recovery", "status": next(iter(recover.manager.background.ACTIVE)), "environment_id": "env"}
        final = dict(current, status="completed")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            with patch.object(recover.manager, "load", side_effect=[parent, current]), patch.object(recover.manager, "seal") as seal, patch.object(recover.manager.background, "request", return_value=final) as req:
                recover.retrieve("key", Path("prior"), Path("recovery"), out, True)
                req.assert_called_once_with("key", interaction_id="recovery")
                self.assertEqual(seal.call_count, 2)
                self.assertEqual(seal.call_args_list[0].args[2], current)
                self.assertEqual(seal.call_args_list[1].args[2], final)
    def test_completed_recovery_no_request(self):
        parent = {"id": "original", "status": "completed", "environment_id": "env"}
        current = dict(parent, id="recovery")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(recover.manager, "load", side_effect=[parent, current]), patch.object(recover.manager, "seal"), patch.object(recover.manager.background, "request") as req:
                recover.retrieve("key", Path("prior"), Path("recovery"), Path(tmp) / "out", True)
                req.assert_not_called()
    def test_no_confirmation_no_request(self):
        with patch.object(recover.manager.background, "request") as req:
            with self.assertRaises(ValueError):
                recover.recover("key", Path("prior"), Path("out"), 20000, False)
            req.assert_not_called()
    def test_noncompleted_parent_no_request(self):
        with patch.object(recover.manager, "load", return_value={"status": "incomplete"}), patch.object(recover.manager.background, "request") as req:
            with self.assertRaises(ValueError):
                recover.recover("key", Path("prior"), Path("out"), 20000, True)
            req.assert_not_called()

if __name__ == "__main__":
    unittest.main()
