import tempfile
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import manager
    import archive
except ModuleNotFoundError as exc:
    if exc.name != "cryptography":
        raise
    manager = archive = None

@unittest.skipIf(manager is None, "cryptography unavailable")
class ArchiveTests(unittest.TestCase):
    def test_deduplicate_restore_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "input.enc"
            store = root / "archive"
            experiment = "AG-PHOTONIC-001"
            response = {"id":"test-id","status":"completed","private":"not public"}
            manager.seal("api", experiment, response, source)
            for run in ("1","2","2"):
                archive.archive(store, experiment, run, source, "api", "archive-key")
            files = list((store / experiment).glob("*.enc"))
            self.assertEqual(len(files), 1)
            self.assertNotIn(b"not public", files[0].read_bytes())
            output = root / "restored.enc"
            archive.restore(store, experiment, output, "new-api", "archive-key")
            self.assertEqual(manager.load("new-api", experiment, output), response)
            files[0].write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                archive.restore(store, experiment, output, "new-api", "archive-key")
    def test_wrong_experiment_and_key(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "input.enc"
            manager.seal("api", "AG-INFRA-001", {"id":"test-id"}, source)
            with self.assertRaises(ValueError):
                archive.archive(root/"archive","AG-PHOTONIC-001","1",source,"api","archive-key")
            with self.assertRaises(ValueError):
                archive.archive(root/"archive","AG-INFRA-001","1",source,"api","api")
