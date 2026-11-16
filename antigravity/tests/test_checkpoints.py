import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("checkpoints", Path(__file__).resolve().parents[1]/"checkpoints.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def run(i, **kw):
    return dict({"id":i,"head_branch":"main","event":"workflow_dispatch","status":"completed"}, **kw)

def artifact(name, expired=False):
    return {"name":name,"expired":expired}

class CheckpointTests(unittest.TestCase):
    def test_latest_matching(self):
        name = m.LEGACY+"-AG-PHOTONIC-001"
        runs = [run(1),run(2),run(3),run(4,head_branch="feature"),run(5,status="in_progress")]
        data = {1:[artifact(name)],2:[artifact(name,True)],3:[artifact(m.LEGACY+"-AG-INFRA-001")]}
        self.assertEqual(m.select(runs,data.__getitem__,"AG-PHOTONIC-001"),(1,name))
    def test_legacy_migration(self):
        runs = [run(43855012421),run(43855012422)]
        self.assertEqual(m.select(runs,lambda i:[artifact(m.LEGACY)],"AG-PHOTONIC-001"),(43855012421,m.LEGACY))
        with self.assertRaises(ValueError):
            m.select(runs,lambda i:[artifact(m.LEGACY)],"AG-INFRA-001")
    def test_explicit_legacy(self):
        self.assertEqual(m.select([run(1)],lambda i:[artifact(m.LEGACY)],"AG-INFRA-001","1"),(1,m.LEGACY))
    def test_no_match(self):
        with self.assertRaises(ValueError):
            m.select([run(1)],lambda i:[],"AG-PHOTONIC-001")
    def test_ambiguous(self):
        with self.assertRaises(ValueError):
            m.select([run(1)],lambda i:[artifact(m.LEGACY+"-AG-INFRA-001")]*2,"AG-INFRA-001")
