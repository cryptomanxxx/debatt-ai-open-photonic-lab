import importlib.util
import io
import json
import urllib.error
from contextlib import redirect_stderr
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

if importlib.util.find_spec("cryptography") is None:
    raise unittest.SkipTest("Manager encryption dependency not installed; dedicated CI installs it")

spec = importlib.util.spec_from_file_location("ag_manager", Path(__file__).resolve().parents[1] / "manager.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ManagerTests(unittest.TestCase):
    def test_start_and_retrieve(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/"a.enc", Path(d)/"b.enc"
            with patch.object(m.background, "request", return_value={"id":"test-id","status":"in_progress"}) as req:
                self.assertEqual(m.execute("key","AG-INFRA-001","start",a,allow_submit=True),0)
                self.assertTrue(req.call_args.kwargs["payload"]["background"])
                self.assertEqual(req.call_count,1)
            self.assertNotIn(b"test-id",a.read_bytes())
            with patch.object(m.background, "request", return_value={"id":"test-id","status":"completed"}) as req:
                self.assertEqual(m.execute("key","AG-INFRA-001","retrieve",b,prior=a),0)
                req.assert_called_once_with("key",interaction_id="test-id")
            self.assertEqual(m.load("key","AG-INFRA-001",b)["status"],"completed")
            with self.assertRaises(Exception):
                m.load("wrong","AG-INFRA-001",b)
            with self.assertRaises(ValueError):
                m.load("key","AG-PHOTONIC-001",b)

    def test_no_unconfirmed_post_or_retry(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background,"request",side_effect=TimeoutError) as req:
            a = Path(d)/"a.enc"
            with self.assertRaises(ValueError):
                m.execute("key","AG-INFRA-001","start",a)
            req.assert_not_called()
            with self.assertRaises(TimeoutError):
                m.execute("key","AG-INFRA-001","start",a,allow_submit=True)
            self.assertEqual(req.call_count,1)
            self.assertFalse(a.exists())

    def test_import_mismatch(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background,"request",return_value={"id":"other","status":"completed"}):
            a = Path(d)/"a.enc"
            with self.assertRaises(ValueError):
                m.execute("key","AG-PHOTONIC-001","import",a,legacy_id="expected")
            self.assertFalse(a.exists())

    def test_dynamic_pilot(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background, "request", return_value={"id":"test-id","status":"in_progress"}) as req:
            a = Path(d)/"a.enc"
            self.assertEqual(m.execute("key","AG-INFRA-001","start",a,allow_submit=True,dynamic_webhook=True),0)
            payload = req.call_args.kwargs["payload"]
            self.assertEqual(payload["webhook_config"], {"uris":[m.DYNAMIC_URI]})
            self.assertTrue(payload["background"])
            self.assertTrue(payload["store"])
            self.assertNotIn("webhook_config",m.EXPERIMENTS["AG-INFRA-001"])
            self.assertEqual(req.call_count,1)
            b = Path(d)/"b.enc"
            m.execute("key","AG-INFRA-001","start",b,allow_submit=True)
            self.assertNotIn("webhook_config",req.call_args.kwargs["payload"])

    def test_dynamic_restrictions(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background,"request") as req:
            a = Path(d)/"a.enc"
            for experiment,mode,budget,allow in [
                ("AG-INFRA-001","retrieve",20000,True),
                ("AG-INFRA-001","import",20000,True),
                ("AG-PHOTONIC-003","start",20000,True),
                ("AG-INFRA-001","start",40000,True),
                ("AG-INFRA-001","start",20000,False),
            ]:
                with self.subTest(experiment=experiment,mode=mode,budget=budget,allow=allow), self.assertRaises(ValueError):
                    m.execute("key",experiment,mode,a,budget=budget,allow_submit=allow,dynamic_webhook=True)
            req.assert_not_called()
            self.assertFalse(a.exists())

    def test_safe_http_error(self):
        secret = "secret-api-key-and-interaction-id"
        for code, body, expected in [
            (400, json.dumps({"error":{"status":"INVALID_ARGUMENT","message":secret,"details":[secret]}}).encode(), "INVALID_ARGUMENT"),
            (429, b'{"error":{"status":"RESOURCE_EXHAUSTED"}}', "RESOURCE_EXHAUSTED"),
            (403, json.dumps({"error":{"status":secret}}).encode(), "unknown"),
            (500, b"not json", "unknown"),
            (503, b"x"*65537, "unknown"),
            (400, b'{"error":{"status":[]}}', "unknown"),
        ]:
            with self.subTest(code=code, expected=expected):
                stream = io.BytesIO(body)
                exc = urllib.error.HTTPError("https://example.test/"+secret,code,secret,{},stream)
                self.assertEqual(m.safe_http_error(exc),f"Google API HTTP status: {code}; canonical status: {expected}")
                self.assertTrue(stream.closed)

    def test_main_http_error_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)/"checkpoint.enc"
            exc = urllib.error.HTTPError("https://example.test/private",400,"private",{},io.BytesIO(b'{"error":{"status":"INVALID_ARGUMENT","message":"private"}}'))
            argv = ["manager","--experiment","AG-INFRA-001","--mode","start","--output",str(output),"--confirm-free-project","--allow-submit","--dynamic-webhook"]
            logs = io.StringIO()
            with patch.object(m.sys,"argv",argv), patch.dict(m.os.environ,{"GEMINI_API_KEY":"secret"}), patch.object(m.background,"request",side_effect=exc) as req, redirect_stderr(logs):
                self.assertEqual(m.main(),1)
                req.assert_called_once()
            self.assertIn("HTTP status: 400; canonical status: INVALID_ARGUMENT",logs.getvalue())
            self.assertNotIn("private",logs.getvalue())
            self.assertNotIn("secret",logs.getvalue())
            self.assertFalse(output.exists())

    def test_poll_completed_and_identity(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d)/"a.enc"
            m.seal("key","AG-INFRA-001",{"id":"test-id","status":"in_progress"},a)
            with patch.object(m.background,"request",side_effect=[
                {"id":"test-id","status":"in_progress"},
                {"id":"test-id","status":"completed"}]) as req, patch.object(m.time,"sleep") as wait:
                self.assertEqual(m.poll_existing("key","AG-INFRA-001",a,sleep=wait),0)
                self.assertEqual(req.call_count,2)
                self.assertTrue(all(call.kwargs == {"interaction_id":"test-id"} for call in req.call_args_list))
                self.assertEqual(wait.call_count,2)
            self.assertEqual(m.load("key","AG-INFRA-001",a)["status"],"completed")
            with patch.object(m.background,"request") as req:
                self.assertEqual(m.poll_existing("key","AG-INFRA-001",a),0)
                req.assert_not_called()

    def test_poll_limit_and_failure_preserves_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d)/"a.enc"
            active = {"id":"test-id","status":"in_progress"}
            m.seal("key","AG-INFRA-001",active,a)
            with patch.object(m.background,"request",return_value=active) as req:
                self.assertEqual(m.poll_existing("key","AG-INFRA-001",a,sleep=lambda _:None),0)
                self.assertEqual(req.call_count,12)
            for candidate in ({"id":"wrong","status":"completed"},):
                with patch.object(m.background,"request",return_value=candidate), self.assertRaises(ValueError):
                    m.poll_existing("key","AG-INFRA-001",a,sleep=lambda _:None)
                self.assertEqual(m.load("key","AG-INFRA-001",a),active)
            with patch.object(m.background,"request",side_effect=TimeoutError), self.assertRaises(TimeoutError):
                m.poll_existing("key","AG-INFRA-001",a,sleep=lambda _:None)
            self.assertEqual(m.load("key","AG-INFRA-001",a),active)
            with patch.object(m.background,"request",return_value={"id":"test-id","status":"incomplete"}) as req:
                self.assertEqual(m.poll_existing("key","AG-INFRA-001",a,sleep=lambda _:None),1)
                req.assert_called_once()
            self.assertEqual(m.load("key","AG-INFRA-001",a)["status"],"incomplete")

    def test_continue_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            a,b = Path(d)/"a.enc",Path(d)/"b.enc"
            exp = "AG-PHOTONIC-003"
            parent = {"id":"parent-id","environment_id":"env-id","status":"incomplete"}
            m.seal("key",exp,parent,a)
            with patch.object(m.background,"request",return_value={"id":"child-id","status":"in_progress"}) as req:
                self.assertEqual(m.execute("key",exp,"continue",b,prior=a,budget=50000,allow_submit=True),0)
                req.assert_called_once()
                p = req.call_args.kwargs["payload"]
                self.assertEqual(p["previous_interaction_id"],"parent-id")
                self.assertEqual(p["environment"],"env-id")
                self.assertEqual(p["agent_config"]["max_total_tokens"],50000)
                self.assertTrue(p["background"])
                self.assertNotIn("webhook_config",p)
            self.assertEqual(m.load("key",exp,a),parent)
            self.assertEqual(m.load("key",exp,b)["id"],"child-id")

    def test_continue_rejects_invalid_parent(self):
        with tempfile.TemporaryDirectory() as d, patch.object(m.background,"request") as req:
            a,b = Path(d)/"a.enc",Path(d)/"b.enc"
            exp = "AG-PHOTONIC-003"
            for parent in ({"id":"parent-id","status":"incomplete"},
                           {"id":"parent-id","status":"in_progress","environment_id":"env-id"},
                           {"id":"parent-id","status":"incomplete","environment_id":"remote"}):
                m.seal("key",exp,parent,a)
                with self.assertRaises(ValueError):
                    m.execute("key",exp,"continue",b,prior=a,allow_submit=True)
            with self.assertRaises(ValueError):
                m.execute("key",exp,"continue",b,prior=a)
            req.assert_not_called()
