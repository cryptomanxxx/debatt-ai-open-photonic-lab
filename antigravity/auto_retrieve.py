"""Scheduled GET-only watcher for active Antigravity interactions.

Antigravity ("Agency") interactions do not emit webhooks: Google rejects
webhook_config with "CreateInteractionEvent.webhook is not supported by
Agency", and the static project webhook received no completion event. This
watcher replaces that notification:

  1. For each experiment, take the newest manager checkpoint (same selection
     as the manager) and decrypt it.
  2. If the interaction was still active, send one GET. If it has since
     reached a terminal status, dispatch the existing manager in retrieve
     mode, bound to the same interaction hash. The manager seals and uploads
     the new checkpoint and its completion triggers the archive workflow.
  3. If the newest checkpoint is already terminal but its run is missing
     from the permanent archive index, dispatch the archive workflow for it.

Never sends a POST to Google, never starts or resumes research, never seals
or uploads anything itself. Public logs get only experiment names, fixed
actions, enum statuses, run IDs and interaction SHA-256 values.
"""
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import checkpoints
import manager

ACTIVE = manager.background.ACTIVE
TERMINAL = {"completed", "failed", "cancelled", "incomplete", "requires_action"}
MAX_AGE = timedelta(days=7)
ARCHIVE_FAILURE_WINDOW = timedelta(hours=1)


def status_of(response):
    status = response.get("status") if isinstance(response, dict) else None
    return status if status in ACTIVE | TERMINAL else "other"


def digest(ident):
    return hashlib.sha256(ident.encode()).hexdigest()


def plan(experiment, *, runs, artifacts, load, get, archived, now):
    """Decide one action for one experiment. Returns (action, detail)."""
    try:
        run_id, name = checkpoints.select(runs, artifacts, experiment)
    except checkpoints.NoCheckpoint:
        return "skip", "no temporary checkpoint"
    run = next(r for r in runs if r["id"] == run_id)
    created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    response = load(run_id, name)
    ident = manager.background.valid_id(response.get("id"))
    status = status_of(response)
    if status in ACTIVE:
        if now - created > MAX_AGE:
            return "skip", f"run {run_id} still {status} after {MAX_AGE.days} days; stale, retrieve manually"
        current = get(ident)
        if current.get("id") != ident:
            raise ValueError("Interaction mismatch")
        new = status_of(current)
        if new in ACTIVE:
            return "skip", f"run {run_id} still {new}"
        return "retrieve", digest(ident)
    if archived is None:
        return "skip", f"run {run_id} {status}; archive index unavailable, not dispatching"
    if str(run_id) not in archived:
        return "archive", str(run_id)
    return "skip", f"run {run_id} {status} and archived"


def gh(*args, timeout=120):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True, timeout=timeout).stdout


def gh_json(path, field=None):
    if field is None:
        return json.loads(gh("api", path))
    pages = json.loads(gh("api", "--paginate", "--slurp", path))
    return [item for page in pages for item in page[field]]


def download(root, run_id, name, workdir):
    matches = [a for a in gh_json(f"{root}/runs/{run_id}/artifacts?per_page=100", "artifacts")
               if a.get("name") == name and not a.get("expired")]
    if len(matches) != 1:
        raise ValueError("Expected one checkpoint artifact")
    raw = subprocess.run(["gh", "api", f"{root}/artifacts/{matches[0]['id']}/zip"],
                         check=True, capture_output=True, timeout=120).stdout
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.getinfo("checkpoint.enc")
        if info.file_size > 8_000_000:
            raise ValueError("Checkpoint too large")
        target = Path(workdir) / f"{run_id}.enc"
        target.write_bytes(archive.read(info))
    return target


def archived_runs(repo):
    """Run IDs in the permanent archive index, or None if it cannot be read."""
    try:
        data = gh_json(f"repos/{repo}/contents/antigravity/archive/index.json?ref=antigravity-archive")
        index = json.loads(base64.b64decode(data["content"]))
        return {run for entries in index.values() for run in entries}
    except Exception:
        return None


def busy(root, workflow):
    runs = gh_json(f"{root}/workflows/{workflow}/runs?per_page=20", "workflow_runs")
    return any(r.get("status") in ("queued", "in_progress", "waiting", "requested", "pending") for r in runs)


def archive_failing(root, now):
    runs = gh_json(f"{root}/workflows/antigravity-archive.yml/runs?per_page=20", "workflow_runs")
    for r in runs:
        created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        if now - created < ARCHIVE_FAILURE_WINDOW and r.get("conclusion") == "failure":
            return True
    return False


def main():
    if os.environ.get("AG_AUTO_RETRIEVE") != "true":
        print("Automatic retrieval disabled (repository variable AG_AUTO_RETRIEVE is not true).")
        return 0
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Main branch required")
    key = os.environ["GEMINI_API_KEY"]
    repo = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository")
    root = f"repos/{repo}/actions"
    now = datetime.now(timezone.utc)
    if busy(root, "antigravity-manager.yml"):
        print("A manager run is queued or running; nothing to do this time.")
        return 0
    runs = gh_json(f"{root}/workflows/antigravity-manager.yml/runs?branch=main&event=workflow_dispatch&per_page=100",
                   "workflow_runs")
    artifact_cache = {}

    def artifacts(run_id):
        if run_id not in artifact_cache:
            artifact_cache[run_id] = gh_json(f"{root}/runs/{run_id}/artifacts?per_page=100", "artifacts")
        return artifact_cache[run_id]

    archived = archived_runs(repo)
    failures = 0
    with tempfile.TemporaryDirectory() as workdir:
        for experiment in checkpoints.EXPERIMENTS:
            def load(run_id, name, experiment=experiment):
                return manager.load(key, experiment, download(root, run_id, name, workdir))

            try:
                action, detail = plan(experiment, runs=runs, artifacts=artifacts, load=load,
                                      get=lambda ident: manager.background.request(key, interaction_id=ident),
                                      archived=archived, now=now)
            except Exception as exc:
                failures += 1
                print(f"{experiment}: check failed ({type(exc).__name__}); no dispatch.")
                continue
            if action == "retrieve":
                gh("workflow", "run", "antigravity-manager.yml", "--ref", "main",
                   "-f", f"experiment={experiment}", "-f", "mode=retrieve",
                   "-f", f"expected_interaction_hash={detail}",
                   "-f", "confirm_free_project=true", "-f", "confirm_new_submission=false")
                print(f"{experiment}: interaction {detail} finished; dispatched GET-only manager retrieve.")
                return failures and 1  # one dispatch per tick; the manager concurrency group is global
            if action == "archive":
                if busy(root, "antigravity-archive.yml") or archive_failing(root, now):
                    print(f"{experiment}: run {detail} not archived, but archive is busy or failed recently; waiting.")
                    continue
                gh("workflow", "run", "antigravity-archive.yml", "--ref", "main", "-f", f"run_id={detail}")
                print(f"{experiment}: dispatched archive for run {detail}.")
                return failures and 1
            print(f"{experiment}: {detail}.")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Automatic retrieval stopped ({type(exc).__name__}); no dispatch.")
        sys.exit(1)
