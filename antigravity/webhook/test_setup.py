import unittest
from unittest.mock import Mock
from setup import setup, URI, NAME, GOOGLE

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
        call = Mock(side_effect=[{"webhooks":[{"uri":URI}]},{"success":True,"result":[{"name":"GITHUB_TOKEN"},{"name":"WEBHOOK_SIGNING_SECRET"}]}])
        setup(call, {}, {}, "a"*32, "diagnose")
        self.assertEqual(call.call_count, 2)
        self.assertTrue(all(len(c.args)==2 for c in call.call_args_list))
    def test_diagnose_missing_secret(self):
        call = Mock(side_effect=[{"webhooks":[]},{"success":True,"result":[]}])
        setup(call, {}, {}, "a"*32, "diagnose")
        self.assertEqual(call.call_count, 2)
