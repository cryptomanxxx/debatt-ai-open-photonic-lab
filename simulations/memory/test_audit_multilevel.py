import unittest
import tempfile
from pathlib import Path
import json
from audit_multilevel_v002 import key, close, require, verify


class AuditTests(unittest.TestCase):
    def test_key(self):
        self.assertEqual(key(dict(bits="4",seed="1027",program_sigma="0.002",
            read_sigma="0",drift_sigma="0.005",adc_bits="8")),
            (4,1027,.002,0,.005,8))

    def test_metrics_tolerance(self):
        self.assertTrue(close("0.001",.001))
        self.assertFalse(close("0.001",.002))

    def test_reject(self):
        with self.assertRaises(ValueError):
            require(False,"mismatch")
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"archive-provenance.json").write_text(json.dumps(dict(
                workflow_run_id=0,artifact_id=0,source_head_sha="",artifact_sha256="")))
            with self.assertRaisesRegex(ValueError,"archive identity"):
                verify(root)


if __name__=="__main__":
    unittest.main()
