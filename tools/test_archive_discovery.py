import copy
import unittest

from archive_discovery import candidates


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.repo = "owner/repo"
        self.head = "a"*40
        self.pr = {"number":278,"merged":True,"state":"closed",
                   "base":{"ref":"main","repo":{"full_name":self.repo}},
                   "head":{"sha":self.head,"repo":{"full_name":self.repo}}}
        self.run = {"id":1,"head_sha":self.head,"event":"pull_request",
                    "head_repository":{"full_name":self.repo},
                    "path":".github/workflows/experiments.yml",
                    "pull_requests":[{"number":278}],"status":"completed","conclusion":"success"}
        self.artifact = {"id":2,"name":"opa-g-004a","expired":False,"size_in_bytes":100,
                         "digest":"sha256:"+"b"*64,"workflow_run":{"id":1,"head_sha":self.head}}
        self.registry = {"experiments":[{"id":"opa-g-004a","artifact":"opa-g-004a"}]}
        self.profiles = {"opa-g-004a":["result.json","results.csv","timings.csv","workload.csv",
                        "workload-manifest.json","environment-lock.txt","installed-packages.json"]}

    def discover(self, pr=None, runs=None, artifacts=None, profiles=None):
        return candidates(self.repo,self.pr if pr is None else pr,
                          [self.run] if runs is None else runs,self.registry,
                          self.profiles if profiles is None else profiles,
                          lambda _: [self.artifact] if artifacts is None else artifacts)

    def test_exact_selection(self):
        self.assertEqual(self.discover(),[dict(experiment="opa-g-004a",source_run=1,
            source_artifact=2,source_sha=self.head,files=",".join(self.profiles["opa-g-004a"]))])

    def test_unmerged_and_fork(self):
        for change in ({"merged":False},{"state":"open"},
                       {"head":{"sha":self.head,"repo":{"full_name":"fork/repo"}}},
                       {"base":{"ref":"dev","repo":{"full_name":self.repo}}}):
            with self.assertRaises(ValueError):
                self.discover(pr={**self.pr,**change})

    def test_wrong_run(self):
        for change in ({"head_sha":"c"*40},{"event":"workflow_dispatch"},
                       {"pull_requests":[{"number":279}]},{"path":"other"},
                       {"head_repository":{"full_name":"fork/repo"}}):
            self.assertEqual(self.discover(runs=[{**self.run,**change}]),[])

    def test_empty_pr_association_requires_later_checkout_binding(self):
        for association in ([], None):
            self.assertEqual(self.discover(runs=[{**self.run,"pull_requests":association}]),self.discover())
        without = {k:v for k,v in self.run.items() if k != "pull_requests"}
        self.assertEqual(self.discover(runs=[without]),self.discover())

    def test_newest_failure_not_older_success(self):
        self.assertEqual(self.discover(runs=[self.run,{**self.run,"id":2,"conclusion":"failure"}]),[])

    def test_public_profiles_only(self):
        self.assertEqual(self.discover(profiles={}),[])
        self.assertEqual(self.discover(artifacts=[{**self.artifact,"name":"all-experiment-results"}]),[])
        self.assertEqual(self.discover(artifacts=[{**self.artifact,"expired":True}]),[])

    def test_artifact_origin_and_ambiguity(self):
        for artifacts in ([self.artifact,{**self.artifact,"id":3}],
                          [{**self.artifact,"workflow_run":{"id":9,"head_sha":self.head}}],
                          [{**self.artifact,"digest":None}]):
            with self.assertRaises(ValueError):
                self.discover(artifacts=artifacts)

    def test_profile_injection_and_reserved_names(self):
        for name in ("../escape.txt","x.txt\nSOURCE_SHA=bad","archive-provenance.json","result.json"):
            with self.assertRaises(ValueError):
                self.discover(profiles={"opa-g-004a":self.profiles["opa-g-004a"]+[name]})


if __name__ == "__main__":
    unittest.main()
