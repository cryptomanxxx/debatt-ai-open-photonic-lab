"""Select latest experiment checkpoint from trusted manager workflow metadata."""
import argparse
import json
import os
import re
import subprocess
import sys

LEGACY = "antigravity-encrypted-checkpoint"
EXPERIMENTS = ("AG-PHOTONIC-001", "AG-INFRA-001")

class NoCheckpoint(ValueError):
    pass

def select(runs, artifacts, experiment, prior=""):
    if experiment not in EXPERIMENTS or (prior and not re.fullmatch(r"[0-9]+", prior)):
        raise ValueError("Invalid selection")
    name = LEGACY + "-" + experiment
    for run in sorted(runs, key=lambda r: r["id"], reverse=True):
        if prior and str(run["id"]) != prior:
            continue
        if (run.get("head_branch") != "main" or run.get("event") != "workflow_dispatch"
                or run.get("status") != "completed"):
            continue
        candidates = [a for a in artifacts(run["id"]) if not a.get("expired")
                      and a.get("name") == name]
        # Explicit legacy selection or the verified coupler migration run.
        # manager.load authenticates the experiment before GET.
        if not candidates and (prior or (experiment == "AG-PHOTONIC-001" and run["id"] == 43855012421)):
            candidates = [a for a in artifacts(run["id"]) if not a.get("expired")
                          and a.get("name") == LEGACY]
        if len(candidates) == 1:
            return run["id"], candidates[0]["name"]
        if len(candidates) > 1:
            raise ValueError("Ambiguous checkpoint")
    raise NoCheckpoint("No matching checkpoint")

def api(path, field):
    result = subprocess.run(["gh", "api", "--paginate", "--slurp", path],
                            check=True, capture_output=True, text=True, timeout=120)
    return [item for page in json.loads(result.stdout) for item in page[field]]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--experiment", required=True)
    p.add_argument("--prior", default="")
    a = p.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid repository")
    root = f"repos/{repo}/actions"
    runs = api(root + "/workflows/antigravity-manager.yml/runs?branch=main&event=workflow_dispatch&per_page=100", "workflow_runs")
    current = int(os.environ["GITHUB_RUN_ID"])
    runs = [r for r in runs if r["id"] < current]
    try:
        run, name = select(runs, lambda i: api(root + f"/runs/{i}/artifacts?per_page=100", "artifacts"), a.experiment, a.prior)
    except NoCheckpoint:
        if a.prior:
            raise
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("archive=true\n")
        return
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        out.write(f"run_id={run}\nartifact_name={name}\n")
    print(f"Selected checkpoint from GitHub run {run}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Checkpoint selection failed: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
