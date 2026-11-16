import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("ag_manager", Path(__file__).resolve().parents[1] / "manager.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ManagerTests(unittest.TestCase):
    def test_start_and_retrieve(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/"a.enc", Path(d)/"b.enc"
            with patch.object(m.background, "request", return_value={"id":"test-id","status":"in_progress"}) as req:
                self.assertEqual(m.execute("key","AG-INFRA-001","start",a,allow_submit=True),0)
                self.assertTrue(req.call_args.kwargs["payload"]["background"])
                self.assertEqual(req.call_count,1)
            self.assertNotIn(b"test-id",a.read_bytes())
            with patch.object(m.background, "request", return_value={"id":"test-id","status":"completed"}) as req:
                self.assertEqual(m.execute("key","AG-INFRA-001","retrieve",b,prior=a),0)
                req.assert_called_once_with("key",interaction_id="test-id")
            self.assertEqual(m.load("key","AG-INFRA-001",b)["status"],"completed")
            with self.assertRaises(Exception):
                m.load("wrong","AG-INFRA-001",b)
            with self.assertRaises(ValueError):
                m.load("key","AG-PHOTONIC-001",b)

    def test_no_unconfirmed_post_or_retry(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background,"request",side_effect=TimeoutError) as req:
            a = Path(d)/"a.enc"
            with self.assertRaises(ValueError):
                m.execute("key","AG-INFRA-001","start",a)
            req.assert_not_called()
            with self.assertRaises(TimeoutError):
                m.execute("key","AG-INFRA-001","start",a,allow_submit=True)
            self.assertEqual(req.call_count,1)
            self.assertFalse(a.exists())

    def test_import_mismatch(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background,"request",return_value={"id":"other","status":"completed"}):
            a = Path(d)/"a.enc"
            with self.assertRaises(ValueError):
                m.execute("key","AG-PHOTONIC-001","import",a,legacy_id="expected")
            self.assertFalse(a.exists())
