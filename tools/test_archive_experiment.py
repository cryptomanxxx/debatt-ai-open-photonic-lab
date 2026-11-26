import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import os
import archive_experiment as ae

from archive_experiment import expansion_limits, C2_ORIGINAL, C2_TOTAL_MAX, C2_NODE_MAX, MAX_TOTAL, MAX_FILE, sha, git_blob, unpack, write_archive, verify_staged, validate_metadata, executed_checkout, download_job_log


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.files = {"result.json": b'{"passed": true}\n',
                      "results.csv": b"a,b\r\n1,2\r\n",
                      "environment-lock.txt": b"lock\n",
                      "installed-packages.json": b"[]\n"}

    def zip(self, files=None, extra=None):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for n, d in (self.files if files is None else files).items():
                z.writestr(n, d)
            if extra:
                z.writestr(*extra)
        data = buf.getvalue()
        return data, {"size_in_bytes": len(data), "digest": "sha256:"+sha(data)}

    def test_exact_bytes(self):
        data, a = self.zip()
        self.assertEqual(unpack(data, a, self.files), self.files)

    def c2_profile(self):
        return {**self.files, "node-results.csv": b"node\r\n1\r\n",
                "audit.csv": b"scene\r\n", "workload.json": b"{}",
                "labels.json": b"[]", "calibration.json": b"[]"}

    def test_large_exception_requires_exact_identity_and_profile(self):
        run, artifact, digest = C2_ORIGINAL
        meta = {"id": artifact, "digest": digest, "workflow_run": {"id": run}}
        selected = self.c2_profile()
        self.assertEqual(expansion_limits("opa-g-004c2", meta, selected),
                         (C2_TOTAL_MAX, {"node-results.csv": C2_NODE_MAX}))
        for exp, m in (("opa-g-004c1", meta),
                       ("opa-g-004c2", {**meta, "id": artifact+1}),
                       ("opa-g-004c2", {**meta, "digest": "sha256:"+"0"*64}),
                       ("opa-g-004c2", {**meta, "workflow_run":{"id":run+1}})):
            self.assertEqual(expansion_limits(exp, m, selected), (MAX_TOTAL, {}))
        with self.assertRaisesRegex(ValueError, "exact reviewed profile"):
            expansion_limits("opa-g-004c2", meta, list(selected)+["extra.csv"])

    def test_large_expansion_and_member_limits(self):
        # Scale the limits down for a cheap synthetic ZIP test. Patch only the
        # reviewed immutable identity to the synthetic artifact's real digest.
        files = self.c2_profile()
        files["node-results.csv"] = b"x"*100
        data, a = self.zip(files)
        run, artifact, _ = C2_ORIGINAL
        a.update(id=artifact, workflow_run={"id":run})
        identity = (run,artifact,a["digest"])
        with patch("archive_experiment.C2_ORIGINAL",identity), patch(
                "archive_experiment.MAX_TOTAL",80), patch(
                "archive_experiment.MAX_FILE",32), patch(
                "archive_experiment.C2_TOTAL_MAX",1024), patch(
                "archive_experiment.C2_NODE_MAX",128):
            self.assertEqual(unpack(data,a,files,"opa-g-004c2"),files)
            with self.assertRaisesRegex(ValueError,"ZIP expansion limit"):
                unpack(data,a,files,"opa-g-004c1")
            with patch("archive_experiment.C2_NODE_MAX",99):
                with self.assertRaisesRegex(ValueError,"Unsupported ZIP entry: node-results.csv"):
                    unpack(data,a,files,"opa-g-004c2")
            with patch("archive_experiment.C2_TOTAL_MAX",80):
                with self.assertRaisesRegex(ValueError,"ZIP expansion limit"):
                    unpack(data,a,files,"opa-g-004c2")
            with patch("archive_experiment.MAX_FILE",1):
                with self.assertRaisesRegex(ValueError,"Unsupported ZIP entry"):
                    unpack(data,a,files,"opa-g-004c2")
            bad={**a,"digest":"sha256:"+"0"*64}
            with self.assertRaisesRegex(ValueError,"ZIP digest mismatch"):
                unpack(data,bad,files,"opa-g-004c2")

    def test_w002g_pinned_expansion(self):
        run, artifact, digest = ae.W002G_ORIGINAL
        meta = {"id": artifact, "digest": digest, "workflow_run": {"id": run}}
        self.assertEqual(expansion_limits("opa-w-002g", meta, ae.W002G_FILES),
                         (ae.W002G_TOTAL_MAX, {"diagnostics.csv": ae.W002G_DIAGNOSTICS_MAX}))
        self.assertEqual(ae.expansion_policy("opa-w-002g", meta, ae.W002G_FILES),
                         "w002g-original-bounded")
        for exp, m in (("opa-w-002f", meta),
                       ("opa-w-002g", {**meta, "id": artifact+1}),
                       ("opa-w-002g", {**meta, "digest": "sha256:"+"0"*64}),
                       ("opa-w-002g", {**meta, "workflow_run": {"id":run+1}})):
            self.assertEqual(expansion_limits(exp, m, ae.W002G_FILES), (MAX_TOTAL, {}))
        with self.assertRaisesRegex(ValueError, "exact reviewed profile"):
            expansion_limits("opa-w-002g", meta, ae.W002G_FILES-{"state_counts.csv"})

    def test_w002g_exact_bytes_and_bounds(self):
        files = {n:b"x" for n in ae.W002G_FILES}
        files["result.json"] = b'{"passed":true}'
        files["diagnostics.csv"] = b"x"*100
        data, a = self.zip(files)
        run, artifact, _ = ae.W002G_ORIGINAL
        a.update(id=artifact, workflow_run={"id":run})
        with patch("archive_experiment.W002G_ORIGINAL",(run,artifact,a["digest"])), patch(
                "archive_experiment.MAX_TOTAL",80), patch("archive_experiment.MAX_FILE",32), patch(
                "archive_experiment.W002G_TOTAL_MAX",1024), patch("archive_experiment.W002G_DIAGNOSTICS_MAX",128):
            self.assertEqual(unpack(data,a,files,"opa-w-002g"),files)
            with self.assertRaisesRegex(ValueError,"ZIP expansion limit"):
                unpack(data,a,files,"opa-w-002f")
            with patch("archive_experiment.W002G_DIAGNOSTICS_MAX",99):
                with self.assertRaisesRegex(ValueError,"Unsupported ZIP entry: diagnostics.csv"):
                    unpack(data,a,files,"opa-w-002g")
            with patch("archive_experiment.W002G_TOTAL_MAX",80):
                with self.assertRaisesRegex(ValueError,"ZIP expansion limit"):
                    unpack(data,a,files,"opa-w-002g")
            with patch("archive_experiment.MAX_FILE",1):
                with self.assertRaisesRegex(ValueError,"Unsupported ZIP entry"):
                    unpack(data,a,files,"opa-w-002g")

    def test_digest(self):
        data, a = self.zip()
        a["digest"] = "sha256:"+"0"*64
        with self.assertRaises(ValueError):
            unpack(data, a, self.files)

    def test_allowlist(self):
        data, a = self.zip()
        with self.assertRaises(ValueError):
            unpack(data, a, ["result.json"])

    def test_unexpected_readme_is_still_rejected(self):
        data, a = self.zip(extra=("README.md", b"Derived analysis"))
        with self.assertRaisesRegex(ValueError, "Unexpected ZIP path/type"):
            unpack(data, a, self.files)

    def test_path_traversal(self):
        data, a = self.zip(extra=("../escape.txt", b"x"))
        with self.assertRaises(ValueError):
            unpack(data, a, list(self.files)+["../escape.txt"])

    def test_symlink(self):
        i = zipfile.ZipInfo("link.txt")
        i.create_system = 3
        i.external_attr = (stat.S_IFLNK | 0o777) << 16
        data, a = self.zip(extra=(i,b"target"))
        with self.assertRaises(ValueError):
            unpack(data, a, list(self.files)+["link.txt"])

    def test_duplicate_case(self):
        data, a = self.zip(extra=("RESULTS.csv",b"x"))
        with self.assertRaises(ValueError):
            unpack(data, a, list(self.files)+["RESULTS.csv"])

    def test_failed_result(self):
        files = {**self.files, "result.json":b'{"passed": false}'}
        data, a = self.zip(files)
        with self.assertRaises(ValueError):
            unpack(data, a, files)

    def test_immutable_and_staged_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path.cwd()
            try:
                os.chdir(tmp)
                subprocess.run(["git","init","-q"],check=True)
                root = Path("results/ci-originals/opa-g-003/1-2")
                m = write_archive(root,self.files,{"experiment":"opa-g-003"})
                self.assertEqual(m["files"]["results.csv"]["git_blob_sha1"],
                                 git_blob(self.files["results.csv"]))
                with self.assertRaises(ValueError):
                    write_archive(root,self.files,{})
                subprocess.run(["git","-c","core.autocrlf=false","add","--",str(root)],check=True)
                verify_staged(root)
                (root/"results.csv").write_bytes(b"changed")
                subprocess.run(["git","add","--",str(root)],check=True)
                with self.assertRaises(ValueError):
                    verify_staged(root)
            finally:
                os.chdir(old)

    def test_download_job_log_preserves_raw_bytes(self):
        raw = b"checkout log\n\x1b[36mcolored output\x1b[0m\r\n"
        with patch("archive_experiment.subprocess.check_output", return_value=raw) as call:
            self.assertEqual(download_job_log("owner/repo", 123), raw)
            call.assert_called_once_with([
                "gh", "api", "--allow-escape-sequences",
                "repos/owner/repo/actions/jobs/123/logs",
            ])

    def test_download_job_log_fails_closed(self):
        with patch("archive_experiment.subprocess.check_output",
                   side_effect=subprocess.CalledProcessError(1, ["gh", "api"])):
            with self.assertRaises(subprocess.CalledProcessError):
                download_job_log("owner/repo", 123)

    def test_historical_checkout(self):
        head, merge = "a"*40, "b"*40
        log = "\n".join([
            "2026-11-26T11:26:00.0000000Z ##[group]Run actions/checkout@v5",
            "[command]/usr/bin/git fetch origin +" + merge + ":refs/remotes/pull/267/merge",
            "[command]/usr/bin/git checkout --progress --force refs/remotes/pull/267/merge",
            "[command]/usr/bin/git log -1 --format=%H", merge,
            "##[group]Run experiment",
        ])
        self.assertEqual(executed_checkout(log, "pull_request", head), merge)
        self.assertEqual(executed_checkout(log, "pull_request", head, "267"), merge)
        with self.assertRaises(ValueError):
            executed_checkout(log, "pull_request", head, "278")
        for broken in (log.replace("+"+merge, "+"+head),
                       log.replace("refs/remotes/pull/267/merge", "main"),
                       log.replace("\n"+merge+"\n", "\nmissing\n"),
                       log.replace("[command]/usr/bin/git log -1", "##[group]Run other\n[command]/usr/bin/git log -1")):
            with self.assertRaises(ValueError):
                executed_checkout(broken, "pull_request", head)
        dispatch = "##[group]Run actions/checkout@v5\n[command]/usr/bin/git log -1 --format=%H\n"+head
        self.assertEqual(executed_checkout(dispatch, "workflow_dispatch", head), head)
        with self.assertRaises(ValueError):
            executed_checkout(dispatch, "workflow_dispatch", merge)

    def test_pinned_squash_recovery(self):
        repo = ae.C3A_RECOVERY_REPO
        head, base = ae.C3A_RECOVERY_HEAD, ae.C3A_RECOVERY_BASE
        merged, executed = ae.C3A_RECOVERY_MERGE, ae.C3A_RECOVERY_EXECUTED
        run, artifact = ae.C3A_RECOVERY_SOURCE
        args = (repo, "opa-g-004c3a", run, artifact, head, "297")
        self.assertTrue(ae.is_c3a_recovery(*args))
        for index, value in enumerate(("fork/repo", "opa-g-004c2", run+1,
                                       artifact+1, "a"*40, "298")):
            wrong = list(args)
            wrong[index] = value
            self.assertFalse(ae.is_c3a_recovery(*wrong))
        pr = {"number":297, "merged":True, "state":"closed",
              "base":{"ref":"main","repo":{"full_name":repo}},
              "head":{"sha":head,"repo":{"full_name":repo}},
              "merge_commit_sha":merged}
        tree = {"tree":{"sha":"a"*40}}
        integrated = {"sha":merged,"parents":[{"sha":base}],"commit":tree}
        tested = {"sha":executed,"parents":[{"sha":base},{"sha":head}],"commit":tree}
        with patch("archive_experiment.api",side_effect=[integrated,tested]), patch(
                "archive_experiment.subprocess.run") as ancestor:
            self.assertEqual(ae.verify_c3a_squash(repo,pr),base)
            ancestor.assert_called_once_with(
                ["git","merge-base","--is-ancestor",merged,"HEAD"],check=True)
        for bad in ({**tested,"commit":{"tree":{"sha":"b"*40}}},
                    {**tested,"parents":[{"sha":base},{"sha":"b"*40}]}):
            with patch("archive_experiment.api",side_effect=[integrated,bad]), patch(
                    "archive_experiment.subprocess.run") as ancestor:
                with self.assertRaises(ValueError):
                    ae.verify_c3a_squash(repo,pr)
                ancestor.assert_not_called()
        with patch("archive_experiment.api") as api:
            with self.assertRaises(ValueError):
                ae.verify_c3a_squash(repo,{**pr,"merged":False})
            api.assert_not_called()
        with patch("archive_experiment.api",side_effect=[integrated,tested]), patch(
                "archive_experiment.subprocess.run",
                side_effect=subprocess.CalledProcessError(1,["git"])):
            with self.assertRaises(subprocess.CalledProcessError):
                ae.verify_c3a_squash(repo,pr)

    def test_metadata(self):
        repo,head="owner/repo","a"*40
        run={"id":1,"status":"completed","conclusion":"success",
             "path":".github/workflows/experiments.yml","event":"pull_request",
             "head_sha":head,"head_repository":{"full_name":repo}}
        artifact={"id":2,"expired":False,"name":"opa-g-003",
                  "workflow_run":{"id":1,"head_sha":head},"size_in_bytes":100,
                  "digest":"sha256:"+"b"*64}
        entry={"artifact":"opa-g-003"}
        validate_metadata(repo,run,artifact,entry,1,2,head)
        for change in ({"conclusion":"failure"},{"head_sha":"c"*40},
                       {"head_repository":{"full_name":"other/repo"}}):
            with self.assertRaises(ValueError):
                validate_metadata(repo,{**run,**change},artifact,entry,1,2,head)
        for change in ({"expired":True},{"name":"wrong"},{"digest":None},
                       {"workflow_run":{"id":9,"head_sha":head}}):
            with self.assertRaises(ValueError):
                validate_metadata(repo,run,{**artifact,**change},entry,1,2,head)


if __name__ == "__main__":
    unittest.main()
