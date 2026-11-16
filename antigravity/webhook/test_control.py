import contextlib
import io
import json
import unittest
from unittest.mock import Mock

from control import (DYNAMIC_URI, POLLS, SafeError, build_payload, error_summary,
                     run, valid_model)


def quiet(fn, *args, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn(*args, **kwargs)
    return code, out.getvalue()


class PayloadTests(unittest.TestCase):
    def test_static_is_plain_background_model_call(self):
        p = build_payload("gemini-3.8-flash", "static")
        self.assertEqual(p["model"], "gemini-3.8-flash")
        self.assertIs(p["background"], True)
        self.assertIs(p["store"], True)
        for field in ("agent", "agent_config", "environment", "tools", "webhook_config"):
            self.assertNotIn(field, p)

    def test_dynamic_adds_only_the_fixed_uri(self):
        p = build_payload("gemini-3.8-flash", "dynamic")
        self.assertEqual(p["webhook_config"], {"uris": [DYNAMIC_URI]})

    def test_rejects_agents_and_bad_input(self):
        for model in ("antigravity-preview-09-2026", "gemini-deep-research", "gemini-3.8-flash-agent",
                      "gemini/../x", "", "GEMINI-3", "gpt-5"):
            with self.subTest(model=model), self.assertRaises(SafeError):
                valid_model(model)
        with self.assertRaises(SafeError):
            build_payload("gemini-3.8-flash", "other")


class ErrorSummaryTests(unittest.TestCase):
    def test_never_echoes_message(self):
        secret = "projects/123 key AIzaSECRET webhook_config.uris is not supported"
        raw = json.dumps({"error": {"code": 400, "message": secret, "status": "INVALID_ARGUMENT"}}).encode()
        s = error_summary(400, raw)
        self.assertIn("HTTP status: 400", s)
        self.assertIn("INVALID_ARGUMENT", s)
        self.assertIn("'webhook'", s)
        self.assertIn("'uris'", s)
        for leak in ("AIza", "projects/123", "not supported"):
            self.assertNotIn(leak, s)

    def test_non_google_format_and_garbage(self):
        s = error_summary(400, json.dumps({"error": {"type": "invalid_request", "message": "Bad background"}}).encode())
        self.assertIn("canonical status: unknown", s)
        self.assertIn("['message', 'type']", s)
        self.assertIn("'background'", s)
        self.assertIn("unknown", error_summary(999, b"<html>"))
        self.assertIn("error fields: []", error_summary(400, b"x" * 70000))


class RunTests(unittest.TestCase):
    def test_polls_until_completed(self):
        call = Mock(side_effect=[{"id": "abc", "status": "in_progress"},
                                 {"id": "abc", "status": "in_progress"},
                                 {"id": "abc", "status": "completed"}])
        sleep = Mock()
        code, out = quiet(run, "k", "gemini-3.8-flash", "static", call=call, sleep=sleep, clock=lambda: "T")
        self.assertEqual(code, 0)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(call.call_args_list[0].kwargs["payload"]["model"], "gemini-3.8-flash")
        self.assertEqual(call.call_args_list[1].kwargs, {"interaction_id": "abc"})
        self.assertIn("Final status: completed", out)
        self.assertNotIn("abc\n", out)

    def test_create_error_does_not_retry(self):
        call = Mock(side_effect=SafeError("Google API HTTP status: 400"))
        code, out = quiet(run, "k", "gemini-3.8-flash", "dynamic", call=call, sleep=Mock(), clock=lambda: "T")
        self.assertEqual(code, 1)
        self.assertEqual(call.call_count, 1)
        self.assertIn("HTTP status: 400", out)

    def test_poll_limit_and_failure(self):
        call = Mock(return_value={"id": "abc", "status": "queued"})
        code, out = quiet(run, "k", "gemini-3.8-flash", "static", call=call, sleep=Mock(), clock=lambda: "T")
        self.assertEqual((code, call.call_count), (0, POLLS + 1))
        call = Mock(side_effect=[{"id": "abc", "status": "queued"}, {"id": "abc", "status": "failed"}])
        code, out = quiet(run, "k", "gemini-3.8-flash", "static", call=call, sleep=Mock(), clock=lambda: "T")
        self.assertEqual(code, 1)
        self.assertIn("Final status: failed", out)

    def test_identity_and_unknown_status(self):
        call = Mock(side_effect=[{"id": "abc", "status": "queued"}, {"id": "xyz", "status": "completed"}])
        self.assertEqual(quiet(run, "k", "gemini-3.8-flash", "static", call=call, sleep=Mock())[0], 1)
        call = Mock(return_value={"id": "abc", "status": "<script>"})
        code, out = quiet(run, "k", "gemini-3.8-flash", "static", call=call, sleep=Mock())
        self.assertIn("Final status: other", out)
        self.assertNotIn("<script>", out)


if __name__ == "__main__":
    unittest.main()
