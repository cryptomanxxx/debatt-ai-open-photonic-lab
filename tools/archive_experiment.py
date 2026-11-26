"""Archive one explicitly selected successful experiment artifact, without rewriting history."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import zipfile

MAX_ZIP = 25 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
MAX_FILE = 20 * 1024 * 1024
# Reviewed exception for one immutable synthetic C2 original, not a global increase.
C2_ORIGINAL = (45865605446, 15140012141, "sha256:8b0033363602a3fa6ce47c6ff5bf8c87244f6352aaba2c3795029738ed00c82a")
C2_NODE_MAX = 95 * 1024 * 1024  # below GitHub's 100 MiB Git blob limit
C2_TOTAL_MAX = 125 * 1024 * 1024
# Bounded exception for the exact successful W-002G diagnostic artifact.
W002G_ORIGINAL = (45907209371, 15158531611, "sha256:9c1a636b7346dc025ac33f449b0673729111b65e3dfd99ed8eca9ace6e686317")
W002G_DIAGNOSTICS_MAX = 48 * 1024 * 1024
W002G_TOTAL_MAX = 72 * 1024 * 1024
W002G_FILES = {"result.json", "state_counts.csv", "diagnostics.csv", "state_summary.csv",
               "confusion_summary.csv", "step_state_summary.csv", "environment-lock.txt",
               "installed-packages.json"}
ALLOWED = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(json|csv|txt)")
ENV_FILES = {"environment-lock.txt", "installed-packages.json"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def api(repo, endpoint):
    return json.loads(subprocess.check_output(["gh", "api", f"repos/{repo}/{endpoint}"]))


# One-time recovery of PR 297, squash merged after successful CI.
C3A_RECOVERY_REPO = "cryptomanxxx/debatt-ai-open-photonic-lab"
C3A_RECOVERY_PR = 297
C3A_RECOVERY_HEAD = "86b24c4b55caae606420a8d25fb8fe3b49c013a0"
C3A_RECOVERY_MERGE = "8464305db498b8c99a58fc9731b0ddf952551da5"
C3A_RECOVERY_BASE = "46db79c01ae3f03a02eb7483d1c303d90aa3d3d2"
C3A_RECOVERY_EXECUTED = "18e0229a0ca19a84c76b4313d5b65e7356de5217"
C3A_RECOVERY_SOURCE = (45876612733, 15145395444)
C3A_RECOVERY_DIGEST = "sha256:aa21052266621af0cee4307847c8b324ec23009765b3c2f8840ab5c7be5d39d3"


def verify_c3a_squash(repo, pr):
    """Prove exact tested tree equals the integrated squash tree."""
    require(repo == C3A_RECOVERY_REPO and pr.get("number") == C3A_RECOVERY_PR
            and pr.get("merged") is True and pr.get("state") == "closed"
            and pr["base"]["ref"] == "main"
            and pr["base"]["repo"]["full_name"] == repo
            and pr["head"]["repo"]["full_name"] == repo
            and pr["head"]["sha"] == C3A_RECOVERY_HEAD
            and pr.get("merge_commit_sha") == C3A_RECOVERY_MERGE,
            "Unexpected C3A recovery PR identity")
    integrated = api(repo, f"commits/{C3A_RECOVERY_MERGE}")
    tested = api(repo, f"commits/{C3A_RECOVERY_EXECUTED}")
    require(integrated["sha"] == C3A_RECOVERY_MERGE
            and tested["sha"] == C3A_RECOVERY_EXECUTED
            and [p["sha"] for p in integrated["parents"]] == [C3A_RECOVERY_BASE]
            and [p["sha"] for p in tested["parents"]] ==
                [C3A_RECOVERY_BASE, C3A_RECOVERY_HEAD],
            "Unexpected C3A recovery commit ancestry")
    tree = tested["commit"]["tree"]["sha"]
    require(re.fullmatch(r"[0-9a-f]{40}", tree)
            and integrated["commit"]["tree"]["sha"] == tree,
            "C3A squash and executed trees differ")
    subprocess.run(["git", "merge-base", "--is-ancestor", C3A_RECOVERY_MERGE, "HEAD"],
                   check=True)
    return C3A_RECOVERY_BASE


def is_c3a_recovery(repo, experiment, run_id, artifact_id, head, archive_pr):
    return (repo == C3A_RECOVERY_REPO and experiment == "opa-g-004c3a"
            and (run_id, artifact_id) == C3A_RECOVERY_SOURCE
            and head == C3A_RECOVERY_HEAD
            and archive_pr == str(C3A_RECOVERY_PR))


def download_job_log(repo, job_id):
    # gh guards terminal output against escape sequences. Capture raw bytes
    # privately for parsing and hashing; never print or execute the log.
    return subprocess.check_output([
        "gh", "api", "--allow-escape-sequences",
        f"repos/{repo}/actions/jobs/{job_id}/logs",
    ])


def validate_metadata(repo, run, artifact, entry, run_id, artifact_id, head):
    require(run["id"] == run_id and run["status"] == "completed"
            and run["conclusion"] == "success", "Source run not successful")
    require(run["path"].split("@")[0] == ".github/workflows/experiments.yml",
            "Wrong workflow")
    require(run["event"] in ("pull_request", "workflow_dispatch"), "Wrong source event")
    require(run["head_sha"] == head, "Unexpected source SHA")
    require(run["head_repository"]["full_name"] == repo, "Fork run not allowed")
    require(artifact["id"] == artifact_id and not artifact["expired"],
            "Artifact unavailable")
    require(artifact["name"] == entry["artifact"], "Wrong artifact name")
    require(artifact["workflow_run"]["id"] == run_id
            and artifact["workflow_run"]["head_sha"] == head, "Wrong artifact origin")
    require(0 < artifact["size_in_bytes"] <= MAX_ZIP, "Archive size limit")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest") or ""),
            "Missing artifact digest")


def executed_checkout(log, event, head, expected_pr=None):
    """Read the historical checkout action output, not today's PR merge ref."""
    lines = [re.sub(r"^\d{4}-\d\d-\d\dT\S+Z ", "", l) for l in log.splitlines()]
    # Limit to the first checkout action, before any experiment code executes.
    starts = [i for i, l in enumerate(lines) if l == "##[group]Run actions/checkout@v5"]
    require(bool(starts), "Missing checkout action log")
    start = starts[0]
    commands = [i for i in range(start, len(lines))
                if lines[i] == "[command]/usr/bin/git log -1 --format=%H"]
    require(bool(commands), "Missing checkout SHA log")
    i = commands[0]
    require(i + 1 < len(lines) and re.fullmatch(r"[0-9a-f]{40}", lines[i+1]),
            "Missing full executed SHA")
    require(not any(l.startswith("##[group]Run ") for l in lines[start+1:i]),
            "Checkout SHA not in first checkout action")
    executed = lines[i+1]
    if event == "pull_request":
        refs = [re.fullmatch(r"\[command\]/usr/bin/git checkout --progress --force refs/remotes/pull/(\d+)/merge", l)
                for l in lines[start:i]]
        require(sum(bool(m) for m in refs) == 1, "Missing unique PR merge checkout")
        require(executed != head, "PR merge SHA unexpectedly equals head")
        # Checkout logs also record the full fetched commit mapped to the merge ref.
        ref = next(m.group(1) for m in refs if m)
        require(expected_pr is None or ref == str(expected_pr), "Historical checkout PR number mismatch")
        require(any(re.search(r"\+" + executed + r":refs/remotes/pull/" + ref + r"/merge$", l)
                    for l in lines[start:i]), "Fetched merge SHA mismatch")
    else:
        require(executed == head, "Dispatch checkout SHA differs from run head")
    return executed


def expansion_limits(experiment, artifact, selected):
    identity = (artifact.get("workflow_run", {}).get("id"), artifact.get("id"), artifact.get("digest"))
    if experiment == "opa-g-004c2" and identity == C2_ORIGINAL:
        require(set(selected) == {"result.json", "results.csv", "node-results.csv",
                "audit.csv", "workload.json", "labels.json", "calibration.json",
                "environment-lock.txt", "installed-packages.json"},
                "C2 original requires exact reviewed profile")
        return C2_TOTAL_MAX, {"node-results.csv": C2_NODE_MAX}
    if experiment == "opa-w-002g" and identity == W002G_ORIGINAL:
        require(set(selected) == W002G_FILES, "W002G original requires exact reviewed profile")
        return W002G_TOTAL_MAX, {"diagnostics.csv": W002G_DIAGNOSTICS_MAX}
    return MAX_TOTAL, {}


def expansion_policy(experiment, artifact, selected):
    _, limits = expansion_limits(experiment, artifact, selected)
    if "diagnostics.csv" in limits:
        return "w002g-original-bounded"
    if "node-results.csv" in limits:
        return "c2-original-bounded"
    return "default"


def unpack(data, artifact, selected, experiment=None):
    require(len(data) == artifact["size_in_bytes"] and len(data) <= MAX_ZIP,
            "ZIP size mismatch")
    require("sha256:" + sha(data) == artifact["digest"], "ZIP digest mismatch")
    total_limit, file_limits = expansion_limits(experiment, artifact, selected)
    files = {}
    seen = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        require(len(infos) <= 256 and sum(i.file_size for i in infos) <= total_limit,
                "ZIP expansion limit")
        for i in infos:
            name = i.filename
            require(not i.is_dir() and ALLOWED.fullmatch(name), "Unexpected ZIP path/type: " + name)
            require(name.casefold() not in seen, "Duplicate ZIP entry")
            seen.add(name.casefold())
            mode = (i.external_attr >> 16) & 0xffff
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG), "Nonregular ZIP entry")
            require(i.file_size <= file_limits.get(name, MAX_FILE) and not i.flag_bits & 1, "Unsupported ZIP entry: " + name)
        print("ZIP expanded bytes:", sum(i.file_size for i in infos),
              "largest member bytes:", max((i.file_size for i in infos), default=0))
        require(set(selected) == {i.filename for i in infos},
                "Explicit file allowlist must equal ZIP contents")
        require(z.testzip() is None, "ZIP CRC failed")
        for i in infos:
            files[i.filename] = z.read(i)
    require("result.json" in files and ENV_FILES <= files.keys(), "Missing standard outputs")
    report = json.loads(files["result.json"])
    require(isinstance(report, dict) and report.get("passed") is not False,
            "Invalid or explicitly failed result")
    return files


def write_archive(root, files, metadata):
    require(not root.exists() and not root.is_symlink(), "Archive destination already exists")
    require(not root.parent.is_symlink(), "Symlink parent")
    root.mkdir(parents=True)
    for name, data in files.items():
        (root / name).write_bytes(data)
    manifest = {**metadata, "files": {
        name: {"bytes": len(data), "sha256": sha(data), "git_blob_sha1": git_blob(data)}
        for name, data in sorted(files.items())
    }}
    (root / "archive-provenance.json").write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest


def verify_staged(root):
    manifest = json.loads((root / "archive-provenance.json").read_text())
    expected = set(manifest["files"]) | {"archive-provenance.json"}
    actual = subprocess.check_output(["git", "ls-files", "-z", "--", str(root)]).decode().split("\0")
    require({Path(p).name for p in actual if p} == expected, "Unexpected staged files")
    for name, info in manifest["files"].items():
        data = subprocess.check_output(["git", "show", ":" + str(root / name)])
        require(len(data) == info["bytes"] and sha(data) == info["sha256"]
                and git_blob(data) == info["git_blob_sha1"], "Staged bytes changed: " + name)
    staged = subprocess.check_output(["git", "show", ":" + str(root / "archive-provenance.json")])
    require(staged == (root / "archive-provenance.json").read_bytes(), "Staged manifest changed")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    experiment = os.environ["ARCHIVE_EXPERIMENT"]
    head = os.environ["SOURCE_SHA"]
    require(re.fullmatch(r"opa-[a-z0-9-]+", experiment), "Invalid experiment ID")
    require(re.fullmatch(r"[0-9a-f]{40}", head), "Invalid SHA")
    run_id, artifact_id = map(int, (os.environ["SOURCE_RUN"], os.environ["SOURCE_ARTIFACT"]))
    require(run_id > 0 and artifact_id > 0, "Invalid ID")
    registry = json.loads(Path("simulations/experiments.json").read_text())
    matches = [e for e in registry["experiments"] if e["id"] == experiment]
    require(len(matches) == 1, "Experiment not uniquely registered")
    entry = matches[0]
    # Require source commit integrated in current main before publication.
    recovery = is_c3a_recovery(repo, experiment, run_id, artifact_id, head,
                              os.environ.get("ARCHIVE_PR"))
    if recovery:
        verify_c3a_squash(repo, api(repo, f"pulls/{C3A_RECOVERY_PR}"))
    else:
        subprocess.run(["git", "merge-base", "--is-ancestor", head, "HEAD"], check=True)
    run = api(repo, f"actions/runs/{run_id}")
    artifact = api(repo, f"actions/artifacts/{artifact_id}")
    validate_metadata(repo, run, artifact, entry, run_id, artifact_id, head)
    if recovery:
        require(artifact["digest"] == C3A_RECOVERY_DIGEST,
                "Unexpected C3A original digest")
    jobs = json.loads(subprocess.check_output([
        "gh", "api", "--paginate", "--slurp",
        f"repos/{repo}/actions/runs/{run_id}/attempts/{run['run_attempt']}/jobs?per_page=100"]))
    matched = [j for page in jobs for j in page["jobs"] if j["name"] == experiment]
    require(len(matched) == 1 and matched[0]["conclusion"] == "success",
            "No unique successful experiment job")
    job_id = matched[0]["id"]
    log = download_job_log(repo, job_id)
    expected_pr = os.environ.get("ARCHIVE_PR") or None
    if expected_pr is not None:
        require(run["event"] == "pull_request" and re.fullmatch(r"[1-9][0-9]*", expected_pr),
                "Invalid discovery PR context")
    executed = executed_checkout(log.decode("utf-8"), run["event"], head, expected_pr)
    if recovery:
        require(executed == C3A_RECOVERY_EXECUTED, "Unexpected C3A executed checkout")
    # Historical synthetic merge objects may not be in main's history.
    # GitHub's immutable commit endpoint supplies parents and tree by exact SHA.
    commit = api(repo, f"commits/{executed}")
    require(commit["sha"] == executed, "Executed commit identity mismatch")
    if run["event"] == "pull_request":
        parents = [p["sha"] for p in commit["parents"]]
        require(len(parents) == 2 and parents[1] == head,
                "Executed merge does not have expected PR head parent")
    # Read the registry from the actual executed tree rather than the PR head.
    source_registry = json.loads(subprocess.check_output([
        "gh", "api", f"repos/{repo}/contents/simulations/experiments.json?ref={executed}",
        "-H", "Accept: application/vnd.github.raw+json"]))
    require(entry in source_registry["experiments"], "Executed registry entry differs")
    selected = [s.strip() for s in os.environ["ARCHIVE_FILES"].split(",")]
    require(all(ALLOWED.fullmatch(s) for s in selected) and len(set(selected)) == len(selected),
            "Invalid explicit file allowlist")
    require("archive-provenance.json" not in selected, "Reserved filename")
    data = subprocess.check_output(["gh", "api", f"repos/{repo}/actions/artifacts/{artifact_id}/zip"])
    files = unpack(data, artifact, selected, experiment)
    root = Path("results") / "ci-originals" / experiment / f"{run_id}-{artifact_id}"
    require(not any(p.is_symlink() for p in root.parents), "Symlink ancestor")
    write_archive(root, files, {
        "experiment": experiment, "repository": repo, "source_head_sha": head,
        "executed_commit_sha": executed, "executed_tree_sha": commit["commit"]["tree"]["sha"],
        "source_event": run["event"], "checkout_log_sha256": sha(log),
        "workflow_run_id": run_id, "run_attempt": run["run_attempt"],
        "job_id": matched[0]["id"], "artifact_id": artifact_id,
        "artifact_name": artifact["name"], "artifact_sha256": sha(data),
        "artifact_bytes": len(data), "source_workflow": run["path"],
        "expanded_bytes": sum(map(len, files.values())),
        "expansion_policy": expansion_policy(experiment, artifact, selected),
        "verification": "GitHub metadata, historical checkout log and executed commit/tree, ZIP SHA-256 and CRC; exact extracted bytes; no rerun",
    })
    if recovery:
        manifest = root / "archive-provenance.json"
        report = json.loads(manifest.read_text())
        report["integration"] = {"method": "squash", "pr": C3A_RECOVERY_PR,
                                 "integrated_commit_sha": C3A_RECOVERY_MERGE,
                                 "executed_tree_equals_integrated_tree": True}
        manifest.write_text(json.dumps(report, indent=2) + "\n")
    subprocess.run(["git", "-c", "core.autocrlf=false", "add", "-f", "--", str(root)], check=True)
    verify_staged(root)


if __name__ == "__main__":
    main()
