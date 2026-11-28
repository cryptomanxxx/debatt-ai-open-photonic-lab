import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from state_machine import Engine
from test_state_machine import ready
from persistence import save_snapshot, load_snapshot, validated_restore, verify_archive


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "state.json"
        self.engine = Engine({"A": ready()})

    def test_roundtrip(self):
        save_snapshot(self.path, self.engine)
        self.assertEqual(load_snapshot(self.path).snapshot(), self.engine.snapshot())

    def test_stop_and_quota(self):
        self.engine.stopped = True
        self.engine.tasks["A"].quota = "exhausted"
        save_snapshot(self.path, self.engine)
        restored = load_snapshot(self.path)
        self.assertEqual(restored.recommend("A"), "STOPPED")
        restored.stopped = False
        self.assertEqual(restored.recommend("A"), "BLOCK_COST")

    def test_missing(self):
        with self.assertRaises(FileNotFoundError):
            load_snapshot(self.path)

    def test_corrupt(self):
        self.path.write_text("{", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_snapshot(self.path)

    def test_wrong_type(self):
        raw = json.loads(self.engine.snapshot())
        raw["tasks"]["A"]["approved"] = "true"
        with self.assertRaises(ValueError):
            validated_restore(json.dumps(raw))

    def test_duplicate_key(self):
        with self.assertRaises(ValueError):
            validated_restore('{"tasks": {}, "stopped": true, "stopped": false}')

    def test_replace_failure(self):
        save_snapshot(self.path, self.engine)
        before = self.path.read_bytes()
        self.engine.stopped = True
        with patch("persistence.os.replace", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                save_snapshot(self.path, self.engine)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_invalid_archive_state(self):
        self.engine.tasks["A"].archive_verified = True
        with self.assertRaises(ValueError):
            save_snapshot(self.path, self.engine)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "result.json"
        self.data.write_bytes(b"fixture")
        self.expected = {"result.json"}
        self.manifest = {"result.json": hashlib.sha256(b"fixture").hexdigest()}

    def test_valid(self):
        self.assertTrue(verify_archive(self.root, self.expected, self.manifest))

    def test_tampered(self):
        self.data.write_bytes(b"changed")
        self.assertFalse(verify_archive(self.root, self.expected, self.manifest))

    def test_missing(self):
        self.data.unlink()
        self.assertFalse(verify_archive(self.root, self.expected, self.manifest))

    def test_incomplete(self):
        self.assertFalse(verify_archive(self.root, self.expected | {"log.txt"}, self.manifest))

    def test_empty(self):
        self.assertFalse(verify_archive(self.root, set(), {}))

    def test_traversal(self):
        self.assertFalse(verify_archive(self.root, {"../result.json"},
                                        {"../result.json": self.manifest["result.json"]}))

    def test_symlink(self):
        (self.root / "alias").symlink_to(self.data)
        self.assertFalse(verify_archive(self.root, {"alias"},
                                        {"alias": self.manifest["result.json"]}))


if __name__ == "__main__":
    unittest.main()
