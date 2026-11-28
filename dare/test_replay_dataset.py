import unittest
from replay_dataset import digest, evaluate
from test_shadow_advisor import record


def case(cid="a", **changes):
    return {"id": cid, "stratum": "clean_ready", "record": record(**changes),
            "now": 100, "raw_sha256": "a"*64}


def run(cases, refs):
    return evaluate(cases, refs, digest({"records": cases, "references": refs}))


def label(value):
    return {"label": value, "reviewer": "synthetic-fixture", "reason": "unit test only"}


class ReplayTests(unittest.TestCase):
    def test_empty(self):
        r = run([], {})
        self.assertIsNone(r["real"]["agreement"])
        self.assertFalse(r["sample_complete"])

    def test_synthetic_excluded(self):
        r = run([case()], {"a": label("REQUEST_HUMAN_REVIEW")})
        self.assertEqual(r["real"]["n"], 0)
        self.assertEqual(r["synthetic"]["agreement"], 1)

    def test_false_ready(self):
        r = run([case()], {"a": label("BLOCK_UNKNOWN")})
        self.assertEqual(r["synthetic"]["false_ready"], 1)
        self.assertEqual(r["synthetic"]["missed_blockers"], 1)

    def test_freeze_mismatch(self):
        with self.assertRaises(ValueError):
            evaluate([case()], {"a": label("REQUEST_HUMAN_REVIEW")}, "0"*64)

    def test_duplicate_head(self):
        with self.assertRaises(ValueError):
            run([case(), case("b")], {"a": label("BLOCK_UNKNOWN"), "b": label("BLOCK_UNKNOWN")})

    def test_missing_reference(self):
        with self.assertRaises(ValueError):
            run([case()], {})

    def test_unmatched_reference(self):
        with self.assertRaises(ValueError):
            run([], {"a": label("BLOCK_UNKNOWN")})

    def test_invalid_hash(self):
        c = case()
        c["raw_sha256"] = "bad"
        with self.assertRaises(ValueError):
            run([c], {"a": label("BLOCK_UNKNOWN")})

    def test_deterministic(self):
        cases = [case()]
        refs = {"a": label("REQUEST_HUMAN_REVIEW")}
        self.assertEqual(run(cases, refs), run(cases, refs))


if __name__ == "__main__":
    unittest.main()
