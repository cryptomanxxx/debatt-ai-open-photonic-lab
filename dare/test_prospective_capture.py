import hashlib
import json
import unittest
from prospective_capture import prepare_capture
from shadow_advisor import REPOSITORY


class ProspectiveTests(unittest.TestCase):
    def setUp(self):
        self.payload = dict(repository=REPOSITORY, number=342, headSha="a"*40,
                            ci="success", ciComplete=True, state="open",
                            codex={"state": "clear"}, readiness={"state": "ready"})
        self.flags = dict(included_verified=True, no_paid_fallback=True, scope_approved=True)

    def test_candidate(self):
        data, meta = prepare_capture(self.payload, 100, **self.flags)
        self.assertEqual(meta["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(meta["eligibility"], "CANDIDATE_ONLY")
        self.assertIn("explicit_ci_head", meta["missing"])

    def test_cost_and_scope(self):
        for key in self.flags:
            flags = dict(self.flags)
            flags[key] = False
            with self.assertRaises(ValueError):
                prepare_capture(self.payload, 100, **flags)

    def test_secret_not_retained(self):
        self.payload["token"] = "secret-fixture"
        self.payload["codex"]["text"] = "secret-fixture"
        data, _ = prepare_capture(self.payload, 100, **self.flags)
        self.assertNotIn(b"secret-fixture", data)

    def test_unknown_preserved(self):
        self.payload["ci"] = "unexpected"
        data, _ = prepare_capture(self.payload, 100, **self.flags)
        self.assertEqual(json.loads(data)["ci"], "unknown")

    def test_wrong_repository(self):
        self.payload["repository"] = "other/repo"
        with self.assertRaises(ValueError):
            prepare_capture(self.payload, 100, **self.flags)

    def test_bad_time(self):
        with self.assertRaises(ValueError):
            prepare_capture(self.payload, True, **self.flags)

    def test_deterministic(self):
        self.assertEqual(prepare_capture(self.payload, 100, **self.flags),
                         prepare_capture(self.payload, 100, **self.flags))


if __name__ == "__main__":
    unittest.main()
