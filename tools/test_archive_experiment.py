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

from archive_experiment import sha, git_blob, unpack, write_archive, verify_staged, validate_metadata, executed_checkout, download_job_log


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

    def test_digest(self):
        data, a = self.zip()
        a["digest"] = "sha256:"+"0"*64
        with self.assertRaises(ValueError):
            unpack(data, a, self.files)

    def test_allowlist(self):
        data, a = self.zip()
        with self.assertRaises(ValueError):
            unpack(data, a, ["result.json"])

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
