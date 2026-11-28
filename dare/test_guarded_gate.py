from dataclasses import replace
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from state_machine import Engine
from test_state_machine import ready
from evidence_gate import ArchiveEvidence, ReviewEvidence
from guarded_gate import GuardedGate, RecoveryEvidence
from persistence import load_snapshot


class GuardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.engine = Engine({"A": ready(head="h1"), "B": ready(head="h2", dependencies=("A",)),
                              "C": ready(dependencies=("B",))})
        self.gate = GuardedGate(self.engine, {"A": {"ci"}},
                                {"A": ("r1", {"a"}), "B": ("r2", {"b"})})
        self.cost = {"A": 100, "B": 100, "C": 100}
        self.review = {"A": ReviewEvidence("h1", 100, {"ci": "failed"}, "clear", 0, True)}
        self.archives = {}

    def archive(self, key, file, run):
        task = self.engine.tasks[key]
        task.merged = True
        (self.root / file).write_bytes(b"fixture")
        self.archives[key] = ArchiveEvidence(key, task.head, run, self.root,
                                             {file: hashlib.sha256(b"fixture").hexdigest()})

    def recommend(self, key):
        return self.gate.recommend(key, 100, self.cost, self.review, self.archives)

    def reserve(self):
        self.assertTrue(self.gate.reserve_correction("A", 100, self.cost, self.review, self.archives))
        return RecoveryEvidence("A", "h1", 1, 1, 100, True, True, True)

    def test_transitive_missing(self):
        self.archive("B", "b", "r2")
        self.assertEqual(self.recommend("C"), "WAIT_DEPENDENCY")

    def test_transitive_valid(self):
        self.archive("A", "a", "r1")
        self.archive("B", "b", "r2")
        self.assertEqual(self.recommend("C"), "PROPOSE_IMPLEMENTATION")
        (self.root / "a").unlink()
        self.assertEqual(self.recommend("C"), "WAIT_DEPENDENCY")

    def test_revoked_dependency(self):
        self.archive("A", "a", "r1")
        self.archive("B", "b", "r2")
        self.engine.tasks["A"].approved = False
        self.assertEqual(self.recommend("C"), "WAIT_DEPENDENCY")

    def test_malformed_review(self):
        self.review["A"] = object()
        self.assertEqual(self.recommend("A"), "BLOCK_EVIDENCE")

    def test_unknown_task(self):
        self.assertEqual(self.recommend("missing"), "BLOCK_STATE")

    def test_recovery(self):
        ev = self.reserve()
        path = self.root / "state.json"
        self.assertTrue(self.gate.recover("A", ev, 100, path))
        t = load_snapshot(path).tasks["A"]
        self.assertFalse(t.leased)
        self.assertEqual(t.retries, 1)
        self.assertEqual(t.sequence, 1)
        self.assertEqual(self.recommend("A"), "BLOCK_COST")
        self.assertFalse(self.gate.recover("A", ev, 100, path))

    def test_recovery_rejects_bad_evidence(self):
        ev = self.reserve()
        path = self.root / "state.json"
        for bad in (replace(ev, operator_approved=False),
                    replace(ev, worker_stopped=False), replace(ev, reconciled=False),
                    replace(ev, head="old"), replace(ev, sequence=0),
                    replace(ev, attempt=0), replace(ev, observed=101)):
            self.assertFalse(self.gate.recover("A", bad, 100, path))
            self.assertTrue(self.engine.tasks["A"].leased)
            self.assertFalse(path.exists())

    def test_recovery_keeps_stop(self):
        ev = self.reserve()
        self.engine.stopped = True
        path = self.root / "state.json"
        self.assertTrue(self.gate.recover("A", ev, 100, path))
        self.assertTrue(load_snapshot(path).stopped)
        self.assertEqual(self.recommend("A"), "STOPPED")

    def test_write_failure_stops(self):
        ev = self.reserve()
        with patch("guarded_gate.save_snapshot", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.gate.recover("A", ev, 100, self.root / "state.json")
        self.assertTrue(self.engine.stopped)
        self.assertTrue(self.engine.tasks["A"].leased)


if __name__ == "__main__":
    unittest.main()
