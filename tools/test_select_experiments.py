"""Regression tests for tools/select_experiments.py (standard library only).

    python tools/test_select_experiments.py
"""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_experiments as se  # noqa: E402

REG = {
    "shared": ["simulations/meep/env.lock.txt"],
    "machinery": [".github/workflows/experiments.yml", "simulations/experiments.json"],
    "experiments": [
        {"id": "a", "name": "A", "script": "simulations/meep/a_v001.py",
         "result_dir": "results/a", "artifact": "a", "timeout_minutes": 5,
         "deps": ["simulations/meep/common.py", "results/b/result.json"]},
        {"id": "b", "name": "B", "script": "simulations/meep/b_v001.py",
         "result_dir": "results/b", "artifact": "b", "timeout_minutes": 5, "deps": [],
         "heavy": True, "run": "echo b"},
        {"id": "c", "name": "C", "script": "simulations/circuit/c_v001.py",
         "result_dir": "results/c", "artifact": "c", "timeout_minutes": 5,
         "deps": ["simulations/circuit/*.json"]},
    ],
}
FILES = {
    "simulations/meep/env.lock.txt": "",
    "simulations/meep/common.py": "",
    "simulations/meep/a_v001.py": "import common\nOUT = 'results/a'\nB = 'results/b/result.json'\n",
    "simulations/meep/b_v001.py": "print('b')\n",
    "simulations/circuit/c_v001.py": "import json\n",
    "simulations/circuit/table.json": "{}",
    "results/b/result.json": "{}",
}


def ids(selected):
    return [e["id"] for e in selected]


class SelectTest(unittest.TestCase):
    def test_script_dep_glob_and_unrelated(self):
        self.assertEqual(ids(se.select_changed(REG, ["simulations/meep/a_v001.py"])), ["a"])
        self.assertEqual(ids(se.select_changed(REG, ["results/b/result.json"])), ["a"])
        self.assertEqual(ids(se.select_changed(REG, ["simulations/circuit/x.json"])), ["c"])
        self.assertEqual(ids(se.select_changed(REG, ["README.md"])), [])

    def test_shared_runs_everything_machinery_skips_heavy(self):
        self.assertEqual(ids(se.select_changed(REG, ["simulations/meep/env.lock.txt"])),
                         ["a", "b", "c"])
        self.assertEqual(ids(se.select_changed(REG, [".github/workflows/experiments.yml"])),
                         ["a", "c"])
        # a machinery change must not hide a heavy experiment whose own files changed
        self.assertEqual(ids(se.select_changed(REG, [".github/workflows/experiments.yml",
                                                     "simulations/meep/b_v001.py"])),
                         ["a", "b", "c"])

    def test_ids(self):
        self.assertEqual(ids(se.select_ids(REG, "all")), ["a", "b", "c"])
        self.assertEqual(ids(se.select_ids(REG, "c, a")), ["c", "a"])
        with self.assertRaises(SystemExit):
            se.select_ids(REG, "nope")

    def test_matrix_default_run(self):
        m = se.matrix(REG["experiments"])
        self.assertEqual(m[0]["run"], "python simulations/meep/a_v001.py")
        self.assertEqual(m[1]["run"], "echo b")
        self.assertEqual(m[0]["lock"], "simulations/meep/opa-fdtd-linux-64.lock.txt")
        e = dict(REG["experiments"][0], lock="simulations/meep/id.lock.txt")
        self.assertEqual(se.matrix([e])[0]["lock"], e["lock"])


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        for rel, text in FILES.items():
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(text)

    def tearDown(self):
        self.tmp.cleanup()

    def errors(self, reg=None):
        return se.check(reg or REG, repo=self.repo)

    def test_consistent_registry_passes(self):
        self.assertEqual(self.errors(), [])

    def test_unregistered_script(self):
        (self.repo / "simulations/meep/new_v002.py").write_text("")
        self.assertTrue(any("new_v002.py" in e for e in self.errors()))

    def test_missing_import_dep(self):
        reg = copy.deepcopy(REG)
        reg["experiments"][0]["deps"] = ["results/b/result.json"]
        self.assertTrue(any("imports 'common'" in e for e in self.errors(reg)))

    def test_missing_read_dep(self):
        reg = copy.deepcopy(REG)
        reg["experiments"][0]["deps"] = ["simulations/meep/common.py"]
        self.assertTrue(any("reads 'results/b/result.json'" in e for e in self.errors(reg)))

    def test_duplicates_and_missing_files(self):
        reg = copy.deepcopy(REG)
        reg["experiments"][1]["id"] = "a"
        reg["experiments"][2]["result_dir"] = "results/b"
        reg["experiments"][2]["deps"] = ["simulations/circuit/*.csv"]
        reg["experiments"][0]["timeout_minutes"] = "5"
        errs = self.errors(reg)
        self.assertTrue(any("'timeout_minutes'" in e for e in errs))
        reg["experiments"][0]["timeout_minutes"] = 5
        errs = self.errors(reg)
        self.assertTrue(any("duplicate id 'a'" in e for e in errs))
        self.assertTrue(any("duplicate result_dir 'results/b'" in e for e in errs))
        self.assertTrue(any("matches no file" in e for e in errs))

    def test_custom_lock_requires_dep(self):
        reg = copy.deepcopy(REG)
        e = reg["experiments"][0]
        e["lock"] = "simulations/meep/id.lock.txt"
        (self.repo / e["lock"]).write_text("@EXPLICIT\n")
        self.assertTrue(any("custom lock" in msg for msg in self.errors(reg)))
        e["deps"].append(e["lock"])
        self.assertEqual(self.errors(reg), [])
        self.assertEqual(ids(se.select_changed(reg,[e["lock"]])), ["a"])

    def test_real_registry_passes(self):
        self.assertEqual(se.check(se.load()), [])


if __name__ == "__main__":
    unittest.main()
