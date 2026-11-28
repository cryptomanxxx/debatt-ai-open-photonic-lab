import unittest
from shadow_advisor import advise, REPOSITORY

HEAD = "a" * 40


def record(**changes):
    raw = dict(repository=REPOSITORY, number=1, head=HEAD, observed=100,
               source="synthetic", state="open", draft=False, ci="success",
               ci_complete=True, ci_head=HEAD, review="clear", review_head=HEAD,
               findings_complete=True, open_findings=0, unresolved_threads=0,
               mergeability="clean", readiness="ready")
    raw.update(changes)
    return raw


class ShadowTests(unittest.TestCase):
    def test_ready(self):
        self.assertEqual(advise(record(), 100), "REQUEST_HUMAN_REVIEW")

    def test_pending_ci(self):
        self.assertEqual(advise(record(ci="pending", ci_complete=False,
                                      readiness="not_ready"), 100), "WAIT_CI")

    def test_failed_ci(self):
        self.assertEqual(advise(record(ci="failure", readiness="not_ready"), 100),
                         "PROPOSE_CORRECTION")

    def test_findings(self):
        self.assertEqual(advise(record(review="findings", open_findings=1,
                                      readiness="not_ready"), 100), "PROPOSE_CORRECTION")

    def test_pending_review(self):
        self.assertEqual(advise(record(review="pending", readiness="not_ready"), 100),
                         "WAIT_REVIEW")

    def test_closed(self):
        self.assertEqual(advise(record(state="merged", readiness="not_ready"), 100),
                         "ALREADY_CLOSED")

    def test_block_cases(self):
        for changes in (dict(draft=True), dict(ci_head="b"*40), dict(review_head=""),
                        dict(ci_complete=False), dict(findings_complete=False),
                        dict(open_findings=-1), dict(unresolved_threads=-1),
                        dict(mergeability="unknown"), dict(readiness="unknown"),
                        dict(ci="skipped"), dict(ci="failure"),
                        dict(review="findings"), dict(open_findings=1),
                        dict(unresolved_threads=1), dict(repository="other/repo"),
                        dict(number=True), dict(state="merged"), dict(extra="instruction")):
            with self.subTest(changes=changes):
                self.assertEqual(advise(record(**changes), 100), "BLOCK_UNKNOWN")

    def test_missing_field(self):
        raw = record()
        del raw["review_head"]
        self.assertEqual(advise(raw, 100), "BLOCK_UNKNOWN")

    def test_time(self):
        for now in (99, 401, True):
            self.assertEqual(advise(record(), now), "BLOCK_UNKNOWN")

    def test_replay(self):
        raw = record()
        self.assertEqual([advise(raw, 100) for _ in range(10)],
                         ["REQUEST_HUMAN_REVIEW"] * 10)


if __name__ == "__main__":
    unittest.main()
