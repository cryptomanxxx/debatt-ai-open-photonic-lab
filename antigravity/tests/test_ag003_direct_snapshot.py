import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / "reproduction" / "AG-PHOTONIC-003"
import sys
sys.path.insert(0, str(ROOT))
try:
    spec = importlib.util.spec_from_file_location("download_snapshot", ROOT / "download_snapshot.py")
    snap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snap)
finally:
    sys.path.remove(str(ROOT))

def archive(entries):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()

def expected(prefix="workspace/"):
    return [(prefix + n, b"{}" if n == "report.json" else b"# source\n")
            for n in sorted(snap.NAMES)]

class SnapshotTest(unittest.TestCase):
    def test_expected_files_only(self):
        files, info = snap.inspect(archive(expected() + [("workspace/private.txt", b"private")]), ())
        self.assertEqual(set(files), snap.NAMES)
        self.assertTrue(info["complete"])
        self.assertNotIn("private", json.dumps(info))
    def test_missing_and_withheld(self):
        entries = [(n, b"secret-id" if n.endswith("params.py") else data)
                   for n, data in expected() if not n.endswith("sweep.py")]
        files, info = snap.inspect(archive(entries), ("secret-id",))
        self.assertFalse(info["complete"])
        self.assertEqual(info["missing"], ["sweep.py"])
        self.assertEqual(info["withheld"], ["params.py"])
        self.assertNotIn("secret-id", json.dumps(info))
    def test_reject_path_and_duplicate(self):
        for entries in (expected() + [("../escape", b"x")],
                        expected() + [("params.py", b"x")]):
            with self.assertRaises(ValueError):
                snap.inspect(archive(entries), ())
    def test_no_confirmation(self):
        with patch.object(snap, "download") as req:
            with self.assertRaises(ValueError):
                snap.snapshot("key", Path("prior"), Path("out"), False)
            req.assert_not_called()
    def test_snapshot_encrypted_and_public_opt_in(self):
        original = {"id": "original-id", "status": "completed", "environment_id": "env-id"}
        raw = archive(expected())
        with tempfile.TemporaryDirectory() as tmp:
            for public in (False, True):
                output = Path(tmp) / str(public)
                with patch.object(snap.manager, "load", return_value=original), patch.object(snap, "download", return_value=raw) as req:
                    self.assertTrue(snap.snapshot("key", Path("prior"), output, True, public))
                    req.assert_called_once_with("key", "env-id")
                encrypted = (output / "snapshot.tar.enc").read_bytes()
                self.assertEqual(snap.manager.cipher("workspace-snapshot-v1:key").decrypt(encrypted), raw)
                self.assertEqual((output / "source").exists(), public)
                self.assertFalse((output / "snapshot.tar").exists())
    def test_redirect_does_not_forward_key(self):
        import urllib.request
        req = urllib.request.Request("https://generativelanguage.googleapis.com/test",
                                     headers={"x-goog-api-key": "key"})
        redirect = snap.SafeRedirect()
        new = redirect.redirect_request(req, None, 302, "", {}, "https://storage.googleapis.com/file")
        self.assertEqual(new.get_method(), "GET")
        self.assertFalse(new.header_items())
        with self.assertRaises(ValueError):
            redirect.redirect_request(req, None, 302, "", {}, "https://example.com/file")
    def test_download_get_only(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"tar"
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = response
        with patch.object(snap.urllib.request, "build_opener", return_value=opener):
            self.assertEqual(snap.download("key", "env-id"), b"tar")
        req = opener.open.call_args.args[0]
        self.assertEqual(req.get_method(), "GET")
        self.assertTrue(req.full_url.endswith("/environments/env-id/files/workspace?alt=media&recursive=true"))
        self.assertEqual(req.get_header("X-goog-api-key"), "key")

if __name__ == "__main__":
    unittest.main()
