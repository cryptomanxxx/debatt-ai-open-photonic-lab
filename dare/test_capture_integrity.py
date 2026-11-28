import hashlib
from pathlib import Path
import tempfile
import unittest
from replay_dataset import digest
from test_replay_dataset import case, label
from capture_integrity import verified_replay


class CaptureTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "capture.json"
        self.path.write_bytes(b'{"fixture":true}')
        sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.records = [case()]
        self.records[0]["raw_sha256"] = sha
        self.refs = {"a": label("REQUEST_HUMAN_REVIEW")}
        self.manifest = {"a": {"path": "capture.json", "sha256": sha,
                                "source": "synthetic", "collected_at": 100}}

    def run_replay(self):
        return verified_replay(self.root, self.records, self.refs,
                               digest({"records": self.records, "references": self.refs}),
                               self.manifest, digest(self.manifest))

    def test_valid(self):
        r = self.run_replay()
        self.assertEqual(r["capture_integrity"], "VERIFIED_BYTES_ONLY")
        self.assertEqual(r["real"]["n"], 0)

    def test_tampered(self):
        self.path.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_missing(self):
        self.path.unlink()
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_traversal(self):
        self.manifest["a"]["path"] = "../capture.json"
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_symlink(self):
        (self.root / "alias").symlink_to(self.path)
        self.manifest["a"]["path"] = "alias"
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_source_mismatch(self):
        self.manifest["a"]["source"] = "archived"
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_unmatched_manifest(self):
        self.manifest["b"] = self.manifest["a"]
        with self.assertRaises(ValueError):
            self.run_replay()

    def test_manifest_digest(self):
        with self.assertRaises(ValueError):
            verified_replay(self.root, self.records, self.refs,
                            digest({"records": self.records, "references": self.refs}),
                            self.manifest, "0"*64)


if __name__ == "__main__":
    unittest.main()
