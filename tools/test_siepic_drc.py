"""Tests that tools/siepic_drc.py finds real violations (needs KLayout and the
klayout Python package, as in the layout-ubc CI job).

    python tools/test_siepic_drc.py
"""
from pathlib import Path
import sys
import tempfile
import unittest

import klayout.db as kdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siepic_drc  # noqa: E402

WHEEL_DIR = tempfile.mkdtemp()


def gds(path, shapes):
    """Write a GDS with boxes {(layer, datatype): [(x1, y1, x2, y2) in um]}."""
    layout = kdb.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("TOP")
    for (layer, datatype), boxes in shapes.items():
        li = layout.layer(layer, datatype)
        for b in boxes:
            top.shapes(li).insert(kdb.DBox(*b))
    layout.write(str(path))
    return path


class DrcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wheel = siepic_drc.fetch_wheel(WHEEL_DIR)
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def drc(self, name, shapes):
        return siepic_drc.run(gds(Path(self.tmp.name) / name, shapes), wheel=self.wheel)

    def test_clean_layout(self):
        r = self.drc("clean.gds", {(1, 0): [(0, 0, 10, 0.5)], (99, 0): [(-5, -5, 15, 5)]})
        self.assertEqual(r["total_violations"], 0, r["violations"])

    def test_too_narrow_silicon(self):
        r = self.drc("narrow.gds", {(1, 0): [(0, 0, 10, 0.04)], (99, 0): [(-5, -5, 15, 5)]})
        self.assertIn("Si_width", r["violations"])

    def test_silicon_outside_floorplan(self):
        r = self.drc("outside.gds", {(1, 0): [(0, 0, 10, 0.5)]})
        self.assertIn("Boundary", r["violations"])

    def test_metal_space(self):
        r = self.drc("m2.gds", {(12, 0): [(0, 0, 10, 10), (14, 0, 24, 10)],
                                (99, 0): [(-5, -5, 30, 15)]})
        self.assertIn("M2_space", r["violations"])

    def test_deck_hash_is_pinned(self):
        self.assertIn("source($input)", siepic_drc.deck_text(self.wheel))


if __name__ == "__main__":
    unittest.main()
