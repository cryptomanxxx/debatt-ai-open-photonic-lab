import unittest
from unittest.mock import Mock
from diagnostic import inspect, NAME, URI, GOOGLE, EVENTS, SafeError

class DiagnosticTests(unittest.TestCase):
    def test_enabled(self):
        w = dict(id="abc-123", name=NAME, uri=URI, subscribed_events=EVENTS, state="enabled")
        call = Mock(side_effect=[{"webhooks":[w]}, w])
        self.assertEqual(inspect(call, {}), GOOGLE+"/abc-123")
        self.assertEqual(call.call_count, 2)

    def test_bad_registration(self):
        for change in ({"state":"disabled"}, {"uri":"https://wrong.example"}, {"subscribed_events":[]}, {"id":"../bad"}):
            w = dict(id="abc", name=NAME, uri=URI, subscribed_events=EVENTS, state="enabled")
            w.update(change)
            with self.subTest(change=change), self.assertRaises(SafeError):
                inspect(Mock(side_effect=[{"webhooks":[w]}, w]), {})

    def test_missing_duplicate_paginated(self):
        w = dict(id="abc", name=NAME, uri=URI)
        for listing in ({"webhooks":[]}, {"webhooks":[w,w]}, {"webhooks":[w],"next_page_token":"next"}, {}):
            with self.assertRaises(SafeError):
                inspect(Mock(return_value=listing), {})
