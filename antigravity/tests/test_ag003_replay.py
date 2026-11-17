import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "reproduction" / "AG-PHOTONIC-003"
spec = importlib.util.spec_from_file_location("compare_replay", ROOT / "compare_replay.py")
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)

class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.original = replay.load(ROOT / "original" / "report.json")
        self.actual = copy.deepcopy(self.original)

    def test_exact_match(self):
        result = replay.compare(self.original, self.actual)
        self.assertTrue(result["structured_match"])
        self.assertTrue(result["dependency_versions_match"])
        self.assertFalse(result["scientific_validation"])

    def test_runtime_and_dependency_versions(self):
        self.actual["physical_verification"]["nn_training_convergence_sim"]["runtime_s"] += 100
        self.actual["environment"]["numpy"] = "different"
        result = replay.compare(self.original, self.actual)
        self.assertTrue(result["structured_match"])
        self.assertFalse(result["dependency_versions_match"])

    def test_changed_counts_fail(self):
        self.actual["analytic_sweep_summary"]["total_configurations_evaluated"] += 1
        result = replay.compare(self.original, self.actual)
        self.assertFalse(result["structured_match"])
        self.assertEqual(result["difference_count"], 1)

    def test_missing_section_fails(self):
        del self.actual["rankings_and_pareto_candidates"]
        self.assertFalse(replay.compare(self.original, self.actual)["structured_match"])

    def test_changed_seed_results_fail(self):
        models = self.actual["physical_verification"]["nn_training_convergence_sim"]["models"]
        models["digital_fp32_baseline"]["per_seed"][0]["final_val_acc"] = 0.1
        self.assertFalse(replay.compare(self.original, self.actual)["structured_match"])

    def test_tolerance(self):
        self.original["equations_and_conventions"]["numeric_test"] = 1.0
        self.actual["equations_and_conventions"]["numeric_test"] = 1.000000001
        self.assertTrue(replay.compare(self.original, self.actual)["structured_match"])
        self.actual["equations_and_conventions"]["numeric_test"] = 1.001
        self.assertFalse(replay.compare(self.original, self.actual)["structured_match"])

if __name__ == "__main__":
    unittest.main()
