from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from state_machine import Engine
from test_state_machine import ready
from evidence_gate import ReviewEvidence
from guarded_gate import RecoveryEvidence
from persistence import save_snapshot, load_snapshot
from checkpoint import Checkpoint, Sequenced


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "state.json"
        save_snapshot(self.path, Engine({"A": ready(head="h1")}))
        self.gate = Checkpoint(self.path, {"A": {"ci"}}, {})
        self.cost = {"A": Sequenced(0, 100)}
        self.review = {"A": Sequenced(0, ReviewEvidence("h1", 100, {"ci": "failed"}, "clear", 0, True))}

    def recommend(self):
        return self.gate.recommend("A", 100, self.cost, self.review, {})

    def reserve(self):
        return self.gate.reserve("A", 100, self.cost, self.review, {})

    def test_persistent_reservation(self):
        self.assertTrue(self.reserve())
        self.assertTrue(load_snapshot(self.path).tasks["A"].leased)
        self.assertFalse(self.reserve())
        self.assertEqual(self.recommend(), "WAIT_LEASE")

    def test_recovery_rejects_old_evidence(self):
        self.assertTrue(self.reserve())
        ev = RecoveryEvidence("A", "h1", 1, 1, 100, True, True, True)
        self.assertTrue(self.gate.recover("A", ev, 100))
        engine = load_snapshot(self.path)
        engine.tasks["A"].quota = "available"
        engine.tasks["A"].cost_verified = True
        save_snapshot(self.path, engine)
        self.assertEqual(self.recommend(), "BLOCK_COST")
        self.cost["A"] = Sequenced(1, 100)
        self.assertEqual(self.recommend(), "WAIT_CURRENT_HEAD")
        self.review["A"] = Sequenced(1, ReviewEvidence("h1", 100, {"ci": "passed"}, "clear", 0, True))
        self.assertEqual(self.recommend(), "REQUEST_HUMAN_MERGE")

    def test_interrupted_write(self):
        with patch("checkpoint.save_snapshot", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.reserve()
        restarted = Checkpoint(self.path, {"A": {"ci"}}, {})
        self.assertEqual(restarted.recommend("A", 100, self.cost, self.review, {}), "BLOCK_CHECKPOINT")

    def test_stop_persists(self):
        self.gate.stop()
        self.assertTrue(load_snapshot(self.path).stopped)
        self.assertEqual(self.recommend(), "STOPPED")

    def test_missing_state_blocks(self):
        self.path.unlink()
        self.assertEqual(self.recommend(), "BLOCK_CHECKPOINT")

    def test_unsequenced_evidence(self):
        self.cost["A"] = 100
        self.assertEqual(self.recommend(), "BLOCK_COST")


if __name__ == "__main__":
    unittest.main()
