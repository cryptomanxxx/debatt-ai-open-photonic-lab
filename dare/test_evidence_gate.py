import hashlib
from pathlib import Path
import tempfile
import unittest
from state_machine import Engine
from test_state_machine import ready
from evidence_gate import EvidenceGate, ReviewEvidence, ArchiveEvidence
from persistence import save_snapshot, load_snapshot


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine({"A": ready(head="h1"), "B": ready(dependencies=("A",))})
        self.gate = EvidenceGate(self.engine, {"A": {"ci"}}, {"A": ("run1", {"result"})})
        self.cost = {"A": 100, "B": 100}
        self.reviews = {"A": ReviewEvidence("h1", 100, {"ci": "passed"}, "clear", 0, True)}
        self.archives = {}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def recommend(self, key="A", now=100):
        return self.gate.recommend(key, now, self.cost, self.reviews, self.archives)

    def review(self, **kw):
        fields = dict(head="h1", observed=100, checks={"ci": "passed"},
                      review="clear", threads=0, complete=True)
        fields.update(kw)
        self.reviews["A"] = ReviewEvidence(**fields)

    def archive(self, **kw):
        self.engine.tasks["A"].merged = True
        (self.root / "result").write_bytes(b"fixture")
        fields = dict(task="A", head="h1", run="run1", root=self.root,
                      manifest={"result": hashlib.sha256(b"fixture").hexdigest()})
        fields.update(kw)
        self.archives["A"] = ArchiveEvidence(**fields)

    def test_merge_request(self):
        self.assertEqual(self.recommend(), "REQUEST_HUMAN_MERGE")

    def test_stale_cost(self):
        self.assertEqual(self.recommend(now=401), "BLOCK_COST")

    def test_stale_review(self):
        self.cost["A"] = 401
        self.assertEqual(self.recommend(now=401), "WAIT_CURRENT_HEAD")

    def test_future_review(self):
        self.review(observed=101)
        self.assertEqual(self.recommend(), "WAIT_CURRENT_HEAD")

    def test_wrong_head(self):
        self.review(head="old")
        self.assertEqual(self.recommend(), "WAIT_CURRENT_HEAD")

    def test_incomplete(self):
        self.review(complete=False)
        self.assertEqual(self.recommend(), "WAIT_CURRENT_HEAD")

    def test_missing_check(self):
        self.review(checks={})
        self.assertEqual(self.recommend(), "WAIT_CURRENT_HEAD")

    def test_skipped(self):
        self.review(checks={"ci": "skipped"})
        self.assertEqual(self.recommend(), "WAIT_CHECKS")

    def test_open_thread(self):
        self.review(threads=1)
        self.assertEqual(self.recommend(), "WAIT_CHECKS")

    def test_legacy_archive_flag(self):
        self.engine.tasks["A"].merged = True
        self.engine.tasks["A"].archive_verified = True
        self.assertEqual(self.recommend("B"), "WAIT_DEPENDENCY")

    def test_verified_archive(self):
        self.archive()
        self.assertEqual(self.recommend("A"), "COMPLETE")
        self.assertEqual(self.recommend("B"), "PROPOSE_IMPLEMENTATION")

    def test_wrong_run(self):
        self.archive(run="other")
        self.assertEqual(self.recommend("B"), "WAIT_DEPENDENCY")

    def test_wrong_archive_head(self):
        self.archive(head="old")
        self.assertEqual(self.recommend("B"), "WAIT_DEPENDENCY")

    def test_tampered_archive(self):
        self.archive()
        (self.root / "result").write_bytes(b"changed")
        self.assertEqual(self.recommend("B"), "WAIT_DEPENDENCY")

    def test_correction_reservation(self):
        self.review(review="findings")
        self.assertTrue(self.gate.reserve_correction("A", 100, self.cost, self.reviews, self.archives))
        self.assertFalse(self.gate.reserve_correction("A", 100, self.cost, self.reviews, self.archives))
        self.assertEqual(self.engine.tasks["A"].retries, 1)
        path = self.root / "snapshot.json"
        save_snapshot(path, self.engine)
        restored = load_snapshot(path)
        self.assertTrue(restored.tasks["A"].leased)
        self.assertEqual(restored.tasks["A"].retries, 1)

    def test_retry_ceiling(self):
        self.engine.tasks["A"].retries = 3
        self.review(review="findings")
        self.assertEqual(self.recommend(), "BLOCK_RETRIES")
        self.review()
        self.assertEqual(self.recommend(), "REQUEST_HUMAN_MERGE")


if __name__ == "__main__":
    unittest.main()
