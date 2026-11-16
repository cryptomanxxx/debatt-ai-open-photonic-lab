import unittest
from unittest.mock import Mock
from setup import setup, URI, NAME, GOOGLE, CF_VERIFY, cf_error_codes

class SetupTests(unittest.TestCase):
    def test_create(self):
        secret = "whsec_" + "YWFhYWFhYWFhYWFhYWFhYQ=="
        call = Mock(side_effect=[{"webhooks":[]}, {"success":True,"result":[{"name":"GITHUB_TOKEN"}]}, {"new_signing_secret":secret}, {"success":True}])
        setup(call, {}, {}, "a"*32, "create")
        self.assertEqual(call.call_count, 4)
        self.assertEqual(call.call_args_list[2].args[3]["subscribed_events"], ["interaction.completed"])
        self.assertEqual(call.call_args_list[3].args[3]["text"], secret)
    def test_duplicate(self):
        call = Mock(return_value={"webhooks":[{"uri":URI}]})
        with self.assertRaises(RuntimeError):
            setup(call, {}, {}, "a"*32, "create")
        self.assertEqual(call.call_count, 1)
    def test_inspect(self):
        call = Mock(return_value={"webhooks":[]})
        setup(call, {}, {}, "a"*32, "inspect")
        self.assertEqual(call.call_count, 1)
    def test_missing_token(self):
        call = Mock(side_effect=[{"webhooks":[]},{"success":True,"result":[]}])
        with self.assertRaises(RuntimeError):
            setup(call, {}, {}, "a"*32, "create")
        self.assertEqual(call.call_count, 2)

    def test_diagnose_existing(self):
        call = Mock(side_effect=[{"webhooks":[{"uri":URI}]},{"success":True,"result":{"status":"active"}},{"success":True,"result":[{"name":"GITHUB_TOKEN"},{"name":"WEBHOOK_SIGNING_SECRET"}]}])
        setup(call, {}, {}, "a"*32, "diagnose")
        self.assertEqual(call.call_count, 3)
        self.assertTrue(all(len(c.args)==2 for c in call.call_args_list))
        self.assertEqual(call.call_args_list[1].args[0], "https://api.cloudflare.com/client/v4/accounts/" + "a"*32 + "/tokens/verify")
    def test_diagnose_missing_secret(self):
        call = Mock(side_effect=[{"webhooks":[]},{"success":True,"result":{"status":"active"}},{"success":True,"result":[]}])
        setup(call, {}, {}, "a"*32, "diagnose")
        self.assertEqual(call.call_count, 3)

    def test_inactive_token_stops(self):
        call = Mock(side_effect=[{"webhooks":[]},{"success":True,"result":{"status":"disabled"}}])
        with self.assertRaisesRegex(RuntimeError, "not active"):
            setup(call, {}, {}, "a"*32, "diagnose")
        self.assertEqual(call.call_count, 2)
        self.assertEqual(call.call_args_list[1].args[0], CF_VERIFY.format(account="a"*32))

    def test_error_codes_only(self):
        self.assertEqual(cf_error_codes({"errors":[{"code":10000,"message":"secret"},{"code":"secret"},{"code":True}]}), [10000])
        self.assertEqual(cf_error_codes({"errors":"secret"}), [])
