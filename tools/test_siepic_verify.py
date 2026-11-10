"""Tests that tools/siepic_verify.py reports real design-for-test errors
(environment: layout/requirements-verify.txt).

    python tools/test_siepic_verify.py
"""
from pathlib import Path
import sys
import tempfile
import unittest

import pya

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siepic_verify  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GDS = REPO / "results" / "opa-layout-003" / "mzi_2x2_siepic_full.gds"


class VerifyTest(unittest.TestCase):
    def test_layout_passes_and_reports_coverage(self):
        r = siepic_verify.run(GDS)
        self.assertEqual(r["errors"], 0, r["errors_by_category"])
        self.assertGreater(r["components"], 0)
        self.assertEqual(r["connectivity_covered"], r["nets"] > 0)

    def test_rotated_grating_coupler_is_caught(self):
        layout = pya.Layout()
        layout.read(str(GDS))
        for cell in layout.each_cell():
            for inst in list(cell.each_inst()):
                if inst.cell.name == "ebeam_gc_te1550":
                    inst.transform(pya.Trans(2, False, 0, 0))
                    break
            else:
                continue
            break
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "rotated.gds"
            layout.write(str(bad))
            r = siepic_verify.run(bad)
        self.assertGreater(r["errors"], 0)
        self.assertTrue(any("Grating coupler orientation" in k for k in r["errors_by_category"]),
                        r["errors_by_category"])


if __name__ == "__main__":
    unittest.main()
