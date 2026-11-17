import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "reproduction" / "AG-PHOTONIC-003"
spec = importlib.util.spec_from_file_location("import_snapshot", ROOT / "import_snapshot.py")
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)

DATA = {"example.py": b"# exact bytes\r\n", "report.json": b"{}"}
EXPECTED = {n: (len(b), hashlib.sha256(b).hexdigest()) for n, b in DATA.items()}

class SnapshotImportTest(unittest.TestCase):
    def setup_source(self, root):
        source = root / "source"
        source.mkdir()
        for name, data in DATA.items():
            (source / name).write_bytes(data)
        return source

    def test_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.setup_source(root)
            output = root / "original"
            imp.import_snapshot(source, output, EXPECTED)
            self.assertEqual(imp.verify(output, EXPECTED), DATA)
            self.assertEqual((output / "example.py").read_bytes(), DATA["example.py"])

    def test_changed_bytes_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.setup_source(root)
            (source / "report.json").write_bytes(b"[]")
            with self.assertRaises(ValueError):
                imp.import_snapshot(source, root / "original", EXPECTED)
            self.assertFalse((root / "original").exists())

    def test_extra_entry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.setup_source(Path(tmp))
            (source / "unexpected").write_text("extra")
            with self.assertRaises(ValueError):
                imp.verify(source, EXPECTED)

    def test_missing_entry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.setup_source(Path(tmp))
            (source / "report.json").unlink()
            with self.assertRaises(ValueError):
                imp.verify(source, EXPECTED)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.setup_source(root)
            target = root / "outside"
            target.write_bytes(DATA["report.json"])
            (source / "report.json").unlink()
            (source / "report.json").symlink_to(target)
            with self.assertRaises(ValueError):
                imp.verify(source, EXPECTED)

    def test_existing_destination_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.setup_source(root)
            output = root / "original"
            output.mkdir()
            sentinel = output / "sentinel"
            sentinel.write_bytes(b"preserve")
            with self.assertRaises(FileExistsError):
                imp.import_snapshot(source, output, EXPECTED)
            self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_real_manifest_has_seven_expected_files(self):
        self.assertEqual(set(imp.EXPECTED), {"params.py", "physics_model.py", "sweep.py",
                        "circuit_sim.py", "train_sim.py", "run_all.py", "report.json"})
        self.assertEqual(sum(v[0] for v in imp.EXPECTED.values()), 164850)

if __name__ == "__main__":
    unittest.main()
