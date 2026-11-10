"""Regression tests for tools/build_catalog.py (standard library only).

    python tools/test_build_catalog.py
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_catalog as bc  # noqa: E402

GOOD = {
    "id": "TEST-001", "title": "Test chip", "function": "nothing", "status": "exploratory",
    "pdk": {"name": "generic", "version": "1", "open_source": True, "platform": "Si"},
    "wavelength_um": {"design": 1.55, "band": [1.5, 1.6]},
    "footprint_um": [10, 20],
    "optical_ports": {"inputs": 2, "outputs": 2},
    "controls": {"heaters": 1},
    "files": {"gds": "chip.gds", "preview": "chip.png"},
    "generator": {"script": "layout/x.py", "environment": "layout/requirements-lock.txt"},
    "checks": {"passed": 1, "total": 1},
    "key_results": [{"name": "loss", "value": "1 dB", "source": "x"}],
    "limitations": ["none checked"],
    "tags": ["test"],
}


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        (folder / "chip.gds").write_bytes(b"x")
        (folder / "chip.png").write_bytes(b"x")
        self.path = folder / "design.json"

    def tearDown(self):
        self.tmp.cleanup()

    def errors(self, **changes):
        sheet = copy.deepcopy(GOOD)
        for dotted, value in changes.items():
            *parents, last = dotted.split("__")
            target = sheet
            for p in parents:
                target = target[p]
            target[last] = value
        return bc.validate(self.path, sheet)

    def test_good_sheet_passes(self):
        self.assertEqual(self.errors(), [])

    def test_nested_fields_rejected(self):
        bad = {
            "pdk__open_source": "false",
            "pdk__name": "",
            "wavelength_um": {},
            "wavelength_um__band": [1.5],
            "footprint_um": [],
            "optical_ports": {},
            "optical_ports__inputs": True,
            "controls__heaters": "6",
            "generator": {},
            "checks__passed": True,
            "key_results": ["loss"],
            "status": "done",
            "title": " ",
            "tags": [""],
            "files__gds": "missing.gds",
        }
        for key, value in bad.items():
            with self.subTest(field=key):
                self.assertNotEqual(self.errors(**{key: value}), [])


class RenderTest(unittest.TestCase):
    def test_pipes_and_newlines_stay_in_one_cell(self):
        sheet = copy.deepcopy(GOOD) | {"_folder": "results/test"}
        sheet["title"] = "A | B\nC"
        sheet["function"] = "x|y"
        md = bc.render_markdown([sheet])
        row = next(line for line in md.splitlines() if "TEST-001" in line and line.startswith("| "))
        cells = [c for c in row.replace("\\|", "").split("|")]
        self.assertEqual(len(cells), 12)  # 10 columns plus the empty ends
        self.assertIn("A \\| B C", row)

    def test_json_round_trip(self):
        sheet = copy.deepcopy(GOOD) | {"_folder": "results/test"}
        data = json.loads(bc.render_json([sheet]))
        self.assertEqual(data["designs"][0]["folder"], "results/test")


if __name__ == "__main__":
    unittest.main()
