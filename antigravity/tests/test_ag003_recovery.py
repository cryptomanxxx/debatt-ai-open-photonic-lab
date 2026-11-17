import base64
import hashlib
import importlib.util
from pathlib import Path
import unittest
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
