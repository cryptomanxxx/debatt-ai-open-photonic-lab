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
    # Check the exact source registry too (avoid changed artifact identity).
    source_registry = json.loads(subprocess.check_output(
        ["git", "show", head+":simulations/experiments.json"]))
    require(entry in source_registry["experiments"], "Source registry entry differs")
    jobs = json.loads(subprocess.check_output([
        "gh", "api", "--paginate", "--slurp",
        f"repos/{repo}/actions/runs/{run_id}/attempts/{run['run_attempt']}/jobs?per_page=100"]))
    matched = [j for page in jobs for j in page["jobs"] if j["name"] == experiment]
    require(len(matched) == 1 and matched[0]["conclusion"] == "success",
            "No unique successful experiment job")
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
        "workflow_run_id": run_id, "run_attempt": run["run_attempt"],
        "job_id": matched[0]["id"], "artifact_id": artifact_id,
        "artifact_name": artifact["name"], "artifact_sha256": sha(data),
        "artifact_bytes": len(data), "source_workflow": run["path"],
        "verification": "GitHub metadata, ZIP SHA-256 and CRC; exact extracted bytes; no rerun",
    })
    subprocess.run(["git", "-c", "core.autocrlf=false", "add", "-f", "--", str(root)], check=True)
    verify_staged(root)


if __name__ == "__main__":
    main()
