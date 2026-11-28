import unittest
from state_machine import Engine, Task

def ready(**kw):
    d = dict(approved=True, scope=("docs/",), quota="available",
             cost_verified=True, paid_fallback_disabled=True)
    d.update(kw)
    return Task(**d)

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.e = Engine({"A": ready()})
    def test_dispatch(self):
        self.assertEqual(self.e.next_task(), ("A", "PROPOSE_IMPLEMENTATION"))
    def test_unknown_cost(self):
        self.e.tasks["A"].quota = "unknown"
        self.assertEqual(self.e.recommend("A"), "BLOCK_COST")
    def test_exhausted(self):
        self.e.tasks["A"].quota = "exhausted"
        self.assertEqual(self.e.recommend("A"), "BLOCK_COST")
    def test_paid_fallback(self):
        self.e.tasks["A"].paid_fallback_disabled = False
        self.assertEqual(self.e.recommend("A"), "BLOCK_COST")
    def test_unverified_cost(self):
        self.e.tasks["A"].cost_verified = False
        self.assertEqual(self.e.recommend("A"), "BLOCK_COST")
    def test_stop_restart(self):
        self.e.stopped = True
        self.assertEqual(Engine.restore(self.e.snapshot()).recommend("A"), "STOPPED")
    def test_cost_restart(self):
        self.e.tasks["A"].quota = "exhausted"
        self.assertEqual(Engine.restore(self.e.snapshot()).recommend("A"), "BLOCK_COST")
    def test_scope(self):
        self.e.tasks["A"].approved = False
        self.assertEqual(self.e.recommend("A"), "BLOCK_SCOPE")
    def test_cycle(self):
        self.e.tasks["A"].dependencies = ("A",)
        self.assertEqual(self.e.recommend("A"), "BLOCK_GRAPH")
    def test_missing_dependency(self):
        self.e.tasks["A"].dependencies = ("B",)
        self.assertEqual(self.e.recommend("A"), "BLOCK_GRAPH")
    def test_archive_gate(self):
        self.e.tasks["B"] = ready(dependencies=("A",))
        self.e.tasks["A"].merged = True
        self.assertEqual(self.e.recommend("A"), "CHECK_ARCHIVE")
        self.assertEqual(self.e.recommend("B"), "WAIT_DEPENDENCY")
        self.e.tasks["A"].archive_verified = True
        self.assertEqual(self.e.recommend("B"), "PROPOSE_IMPLEMENTATION")
    def test_lease(self):
        self.e.tasks["B"] = ready(leased=True)
        self.assertEqual(self.e.recommend("A"), "WAIT_LEASE")
    def test_retry_limit(self):
        self.e.tasks["A"].retries = 3
        self.assertEqual(self.e.recommend("A"), "BLOCK_RETRIES")
    def checked(self, **kw):
        d = dict(head="h1", ci_head="h1", review_head="h1", ci="passed",
                 review="clear", threads=0)
        d.update(kw)
        self.e.tasks["A"] = ready(**d)
    def test_human_merge_only(self):
        self.checked()
        self.assertEqual(self.e.recommend("A"), "REQUEST_HUMAN_MERGE")
    def test_stale_review(self):
        self.checked(review_head="old")
        self.assertEqual(self.e.recommend("A"), "WAIT_CURRENT_HEAD")
    def test_skipped_ci(self):
        self.checked(ci="skipped")
        self.assertEqual(self.e.recommend("A"), "WAIT_CHECKS")
    def test_unresolved_threads(self):
        self.checked(threads=1)
        self.assertEqual(self.e.recommend("A"), "WAIT_CHECKS")
    def test_correction(self):
        self.checked(review="findings")
        self.assertEqual(self.e.recommend("A"), "PROPOSE_CORRECTION")
    def test_new_head(self):
        self.checked()
        self.e.observe("A", 1, head="h2", ci="passed", review="clear")
        self.assertEqual(self.e.recommend("A"), "WAIT_CURRENT_HEAD")
    def test_replay(self):
        self.e.observe("A", 2, quota="exhausted")
        before = self.e.snapshot()
        self.assertFalse(self.e.observe("A", 2, quota="available"))
        self.assertFalse(self.e.observe("A", 1, quota="available"))
        self.assertEqual(before, self.e.snapshot())
        self.assertEqual(before, Engine.restore(before).snapshot())

if __name__ == "__main__":
    unittest.main()
