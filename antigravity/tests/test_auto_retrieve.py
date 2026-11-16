import hashlib
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

if importlib.util.find_spec("cryptography") is None:
    raise unittest.SkipTest("Manager encryption dependency not installed; dedicated CI installs it")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("auto_retrieve", ROOT / "auto_retrieve.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
NAME = m.checkpoints.LEGACY + "-AG-INFRA-001"


def run(i, age=timedelta(hours=1)):
    return {"id": i, "head_branch": "main", "event": "workflow_dispatch", "status": "completed",
            "created_at": (NOW - age).isoformat().replace("+00:00", "Z")}


def plan(response, current=None, archived=frozenset(), age=timedelta(hours=1)):
    get = Mock(return_value=current)
    load = Mock(return_value=response)
    result = m.plan("AG-INFRA-001", runs=[run(7, age)], artifacts=lambda i: [{"name": NAME, "expired": False}],
                    load=load, get=get, archived=archived, now=NOW)
    return result, get, load


class PlanTests(unittest.TestCase):
    def test_active_and_still_active_does_nothing(self):
        (action, detail), get, load = plan({"id": "abc", "status": "in_progress"}, {"id": "abc", "status": "in_progress"})
        self.assertEqual(action, "skip")
        load.assert_called_once_with(7, NAME)
        get.assert_called_once_with("abc")

    def test_active_then_completed_dispatches_bound_retrieve(self):
        (action, detail), get, _ = plan({"id": "abc", "status": "queued"}, {"id": "abc", "status": "completed"})
        self.assertEqual((action, detail), ("retrieve", hashlib.sha256(b"abc").hexdigest()))

    def test_any_terminal_status_is_retrieved(self):
        for status in ("failed", "cancelled", "incomplete", "requires_action", "something-new"):
            with self.subTest(status=status):
                (action, _), _, _ = plan({"id": "abc", "status": "in_progress"}, {"id": "abc", "status": status})
                self.assertEqual(action, "retrieve")

    def test_terminal_checkpoint_is_archived_once(self):
        (action, detail), get, _ = plan({"id": "abc", "status": "completed"})
        self.assertEqual((action, detail), ("archive", "7"))
        get.assert_not_called()
        (action, _), _, _ = plan({"id": "abc", "status": "completed"}, archived={"7"})
        self.assertEqual(action, "skip")

    def test_unreadable_archive_index_never_dispatches_archive(self):
        (action, _), _, _ = plan({"id": "abc", "status": "completed"}, archived=None)
        self.assertEqual(action, "skip")

    def test_stale_active_interaction_is_left_alone(self):
        (action, detail), get, _ = plan({"id": "abc", "status": "in_progress"}, age=timedelta(days=8))
        self.assertEqual(action, "skip")
        self.assertIn("stale", detail)
        get.assert_not_called()

    def test_mismatch_and_bad_ids_raise(self):
        with self.assertRaises(ValueError):
            plan({"id": "abc", "status": "in_progress"}, {"id": "xyz", "status": "completed"})
        with self.assertRaises(ValueError):
            plan({"id": "../bad", "status": "in_progress"}, {"id": "../bad", "status": "completed"})

    def test_no_checkpoint(self):
        result = m.plan("AG-INFRA-001", runs=[run(7)], artifacts=lambda i: [], load=Mock(), get=Mock(),
                        archived=set(), now=NOW)
        self.assertEqual(result[0], "skip")

    def test_disabled_by_default(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(m.main(), 0)


if __name__ == "__main__":
    unittest.main()
