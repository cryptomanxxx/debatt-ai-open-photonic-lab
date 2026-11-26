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


def executed_checkout(log, event, head):
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
        require(any(re.search(r"\+" + executed + r":refs/remotes/pull/" + ref + r"/merge$", l)
                    for l in lines[start:i]), "Fetched merge SHA mismatch")
    else:
        require(executed == head, "Dispatch checkout SHA differs from run head")
    return executed


def unpack(data, artifact, selected):
    require(len(data) == artifact["size_in_bytes"] and len(data) <= MAX_ZIP,
            "ZIP size mismatch")
    require("sha256:" + sha(data) == artifact["digest"], "ZIP digest mismatch")
    files = {}
    seen = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        require(len(infos) <= 256 and sum(i.file_size for i in infos) <= MAX_TOTAL,
                "ZIP expansion limit")
        for i in infos:
            name = i.filename
            require(not i.is_dir() and ALLOWED.fullmatch(name), "Unexpected ZIP path/type: " + name)
            require(name.casefold() not in seen, "Duplicate ZIP entry")
            seen.add(name.casefold())
            mode = (i.external_attr >> 16) & 0xffff
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG), "Nonregular ZIP entry")
            require(i.file_size <= MAX_FILE and not i.flag_bits & 1, "Unsupported ZIP entry")
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
    subprocess.run(["git", "merge-base", "--is-ancestor", head, "HEAD"], check=True)
    run = api(repo, f"actions/runs/{run_id}")
    artifact = api(repo, f"actions/artifacts/{artifact_id}")
    validate_metadata(repo, run, artifact, entry, run_id, artifact_id, head)
    jobs = json.loads(subprocess.check_output([
        "gh", "api", "--paginate", "--slurp",
        f"repos/{repo}/actions/runs/{run_id}/attempts/{run['run_attempt']}/jobs?per_page=100"]))
    matched = [j for page in jobs for j in page["jobs"] if j["name"] == experiment]
    require(len(matched) == 1 and matched[0]["conclusion"] == "success",
            "No unique successful experiment job")
    job_id = matched[0]["id"]
    log = subprocess.check_output(["gh", "api", f"repos/{repo}/actions/jobs/{job_id}/logs"])
    executed = executed_checkout(log.decode("utf-8"), run["event"], head)
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
    files = unpack(data, artifact, selected)
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
        "verification": "GitHub metadata, historical checkout log and executed commit/tree, ZIP SHA-256 and CRC; exact extracted bytes; no rerun",
    })
    subprocess.run(["git", "-c", "core.autocrlf=false", "add", "-f", "--", str(root)], check=True)
    verify_staged(root)


if __name__ == "__main__":
    main()
