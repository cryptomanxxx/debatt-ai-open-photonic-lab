import tempfile
from pathlib import Path
import unittest

from bundle_experiments import collect, expected_result


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "collected"
        self.normal = {"id": "opa-mzi-001", "artifact": "opa-mzi-001"}
        self.benchmark = {"id": "opa-fdtd-005", "artifact": "opa-meep-capacity-v005"}

    def run_bundle(self, expected, files, args=""):
        def download(name, directory):
            for filename in files[name]:
                (directory / filename).write_text("{}")
        return collect(self.root, expected, set(files), download, args,
                       {"experiment_job_result": "success"})

    def test_single_normal(self):
        m = self.run_bundle([self.normal], {"opa-mzi-001": ["result.json"]})
        self.assertTrue(m["all_expected_results_present"])
        self.assertTrue((self.root / "opa-mzi-001" / "result.json").is_file())
        self.assertFalse((self.root / "result.json").exists())

    def test_multiple_with_default_benchmark(self):
        m = self.run_bundle([self.normal, self.benchmark], {
            "opa-mzi-001": ["result.json"],
            "opa-meep-capacity-v005": ["benchmark-small.json"],
        })
        self.assertTrue(m["all_expected_results_present"])

    def test_single_benchmark_medium(self):
        m = self.run_bundle([self.benchmark], {
            "opa-meep-capacity-v005": ["benchmark-medium.json"],
        }, "medium")
        self.assertTrue(m["all_expected_results_present"])
        self.assertEqual(m["experiments"][0]["expected_result"], "benchmark-medium.json")

    def test_wrong_profile_and_missing_artifact(self):
        m = self.run_bundle([self.normal, self.benchmark], {
            "opa-meep-capacity-v005": ["benchmark-small.json"],
        }, "large")
        self.assertFalse(m["all_expected_results_present"])
        self.assertFalse(m["experiments"][0]["artifact_present"])
        self.assertTrue(m["experiments"][1]["artifact_present"])
        self.assertFalse(m["experiments"][1]["result_json_present"])
        self.assertTrue((self.root / "opa-meep-capacity-v005" / "benchmark-small.json").is_file())

    def test_no_artifacts(self):
        m = self.run_bundle([self.normal], {})
        self.assertFalse(m["all_expected_results_present"])
        self.assertTrue((self.root / "bundle-manifest.json").is_file())

    def test_profiles(self):
        self.assertEqual(expected_result("opa-fdtd-005", ""), "benchmark-small.json")
        self.assertEqual(expected_result("opa-fdtd-005", "large"), "benchmark-large.json")
        with self.assertRaises(ValueError):
            expected_result("opa-fdtd-005", "unknown")


if __name__ == "__main__":
    unittest.main()
