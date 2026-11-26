"""Discover approved public artifact profiles for an already merged same-repo PR.
Never execute experiment code or accept filenames/commands from an artifact.
"""
import json
import os
from pathlib import Path
import re
import subprocess

from archive_experiment import api, require, validate_metadata

POLICY = Path("tools/archive-public-profiles.json")


def pages(repo, endpoint, key):
    raw = subprocess.check_output(["gh", "api", "--paginate", "--slurp",
                                   f"repos/{repo}/{endpoint}"])
    return [item for page in json.loads(raw) for item in page[key]]


def candidates(repo, pr, runs, registry, profiles, artifacts_for):
    require(pr.get("merged") is True and pr.get("state") == "closed"
            and pr["base"]["ref"] == "main"
            and pr["base"]["repo"]["full_name"] == repo
            and pr["head"]["repo"]["full_name"] == repo, "Not an integrated same-repository PR")
    head = pr["head"]["sha"]
    require(re.fullmatch(r"[0-9a-f]{40}", head), "Invalid PR head")
    eligible = [r for r in runs if r.get("head_sha") == head
                and r.get("event") == "pull_request"
                and r.get("head_repository", {}).get("full_name") == repo
                and r.get("path", "").split("@")[0] == ".github/workflows/experiments.yml"
                and any(p.get("number") == pr["number"] for p in r.get("pull_requests", []))]
    if not eligible:
        return []
    # Never choose an older successful run if the latest run is failed/pending.
    run = max(eligible, key=lambda r: r["id"])
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        return []
    result = []
    artifacts = artifacts_for(run["id"])
    for entry in registry["experiments"]:
        exp = entry["id"]
        if exp not in profiles:
            continue
        require(re.fullmatch(r"opa-[a-z0-9-]+", exp), "Invalid profile ID")
        matches = [a for a in artifacts if a["name"] == entry["artifact"] and not a["expired"]]
        if not matches:
            continue
        require(len(matches) == 1, "Ambiguous artifact")
        artifact = matches[0]
        validate_metadata(repo, run, artifact, entry, run["id"], artifact["id"], head)
        names = profiles[exp]
        require(isinstance(names, list) and all(isinstance(n,str) and
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(json|csv|txt)",n) for n in names)
                and len(set(names)) == len(names)
                and {"result.json","environment-lock.txt","installed-packages.json"} <= set(names)
                and "archive-provenance.json" not in names, "Invalid public profile")
        result.append(dict(experiment=exp, source_run=run["id"], source_artifact=artifact["id"],
                           source_sha=head, files=",".join(names)))
    return result


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    number = os.environ["ARCHIVE_PR"]
    require(re.fullmatch(r"[1-9][0-9]*", number), "Invalid merged PR number")
    pr = api(repo, f"pulls/{number}")
    require(pr["number"] == int(number), "PR identity mismatch")
    # Only trusted main code runs. No checkout of the source PR or artifact code.
    head = pr["head"]["sha"]
    require(re.fullmatch(r"[0-9a-f]{40}",head), "Invalid head")
    runs = pages(repo, f"actions/workflows/experiments.yml/runs?event=pull_request&head_sha={head}&per_page=100", "workflow_runs")
    registry = json.loads(Path("simulations/experiments.json").read_text())
    profiles = json.loads(POLICY.read_text())
    found = candidates(repo, pr, runs, registry, profiles,
        lambda run: pages(repo, f"actions/runs/{run}/artifacts?per_page=100","artifacts"))
    # Archive one eligible artifact per invocation for now; never guess among multiple.
    pending = []
    for item in found:
        exp,run,artifact = item["experiment"],item["source_run"],item["source_artifact"]
        root = Path("results/ci-originals") / exp / f"{run}-{artifact}"
        branch = f"archive/scientific/{exp}-{run}-{artifact}"
        if root.exists():
            print(f"Already archived: {exp} {run}-{artifact}")
            continue
        refs = subprocess.check_output(["git","ls-remote","--heads","origin",f"refs/heads/{branch}"],text=True)
        if refs.strip():
            print(f"Existing review branch: {branch}; inspect it instead of creating duplicates")
            continue
        pending.append(item)
    require(len(pending) <= 1, "Multiple eligible artifacts; use explicit manual archival")
    with open(os.environ["GITHUB_OUTPUT"],"a") as out:
        print("found=" + ("true" if pending else "false"),file=out)
    if pending:
        with open(os.environ["GITHUB_ENV"],"a") as out:
            for k,v in pending[0].items():
                name = {"experiment":"ARCHIVE_EXPERIMENT","files":"ARCHIVE_FILES"}.get(k,k.upper())
                print(f"{name}={v}",file=out)
        print("Selected",pending[0]["experiment"],pending[0]["source_run"],pending[0]["source_artifact"])
    else:
        print("No new eligible public artifact")


if __name__ == "__main__":
    main()
