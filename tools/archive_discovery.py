"""Discover approved public artifact profiles for an already merged same-repo PR.
Never execute experiment code or accept filenames/commands from an artifact.
"""
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess

from archive_experiment import (api, require, validate_metadata, verify_c3a_squash,
                                C3A_RECOVERY_PR, C3A_RECOVERY_REPO)

POLICY = Path("tools/archive-public-profiles.json")


def pages(repo, endpoint, key):
    raw = subprocess.check_output(["gh", "api", "--paginate", "--slurp",
                                   f"repos/{repo}/{endpoint}"])
    return [item for page in json.loads(raw) for item in page[key]]


def changed_paths(repo, pr):
    """Use paginated PR file metadata, including both sides of renames.

    GitHub caps this endpoint at 3000 files. Refuse incomplete metadata;
    do not silently infer that a truncated change set is documentation-only.
    """
    raw = subprocess.check_output(["gh", "api", "--paginate", "--slurp",
                                   f"repos/{repo}/pulls/{pr['number']}/files?per_page=100"])
    files = [item for page in json.loads(raw) for item in page]
    require(isinstance(pr.get("changed_files"), int) and
            len(files) == pr["changed_files"] and len(files) < 3000,
            "Incomplete PR changed-file metadata")
    paths = set()
    for item in files:
        paths.add(item["filename"])
        if item.get("status") == "renamed":
            paths.add(item["previous_filename"])
    return paths


def archive_relevant(entry, registry, paths, base_registry=None):
    """CI regression selection is broader than automatic publication.

    Docs and CI machinery may trigger regressions but are not new scientific
    inputs. Changes to a specific experiment's executable/data dependencies
    or semantic registry entry qualify. Manual explicit artifact mode remains.
    """
    if "simulations/experiments.json" in paths:
        require(base_registry is not None, "Missing historical base registry")
        old = {e["id"]: e for e in base_registry["experiments"]}
        if old.get(entry["id"]) != entry:
            return True
    patterns = [entry["script"], entry.get("lock", "simulations/meep/opa-fdtd-linux-64.lock.txt"),
                *entry["deps"], *registry["shared"]]
    return any(not p.lower().endswith((".md", ".rst")) and
               p != "simulations/experiments.json" and
               any(fnmatch.fnmatchcase(p, pattern) for pattern in patterns)
               for p in paths)


def historical_base_registry(repo, pr, paths):
    if "simulations/experiments.json" not in paths:
        return None
    # The integrated merge commit's first parent is the historical target,
    # not the moving current PR base branch. Require standard two-parent merge
    # with the exact source head; ambiguous history requires explicit manual mode.
    merge = pr.get("merge_commit_sha") or ""
    require(re.fullmatch(r"[0-9a-f]{40}", merge), "Missing integrated merge SHA")
    commit = api(repo, f"commits/{merge}")
    parents = [p["sha"] for p in commit["parents"]]
    if repo == C3A_RECOVERY_REPO and pr.get("number") == C3A_RECOVERY_PR:
        base = verify_c3a_squash(repo, pr)
    else:
        require(commit["sha"] == merge and len(parents) == 2 and
                parents[1] == pr["head"]["sha"], "Cannot bind historical registry base")
        base = parents[0]
    return json.loads(subprocess.check_output([
        "gh", "api", f"repos/{repo}/contents/simulations/experiments.json?ref={base}",
        "-H", "Accept: application/vnd.github.raw+json"]))


def candidates(repo, pr, runs, registry, profiles, artifacts_for, paths=None, base_registry=None):
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
                and (not r.get("pull_requests") or
                     any(p.get("number") == pr["number"] for p in r["pull_requests"]))]
    print(f"Discovery: {len(runs)} workflow runs returned, {len(eligible)} matching source head/event/repository/PR metadata")
    if not eligible:
        return []
    # Never choose an older successful run if the latest run is failed/pending.
    run = max(eligible, key=lambda r: r["id"])
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        return []
    result = []
    artifacts = artifacts_for(run["id"])
    print(f"Discovery: selected run {run['id']}, {len(artifacts)} artifacts, {len(profiles)} public profiles")
    for entry in registry["experiments"]:
        exp = entry["id"]
        if exp not in profiles:
            continue
        if paths is not None and not archive_relevant(entry, registry, paths, base_registry):
            print(f"Skip {exp}: regression only; no scientific input or registry entry change")
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
    # Validate same-repository merged PR before inspecting its change metadata.
    require(pr.get("merged") is True and pr.get("state") == "closed"
            and pr["base"]["ref"] == "main"
            and pr["base"]["repo"]["full_name"] == repo
            and pr["head"]["repo"]["full_name"] == repo, "Not an integrated same-repository PR")
    paths = changed_paths(repo, pr)
    base_registry = historical_base_registry(repo, pr, paths)
    found = candidates(repo, pr, runs, registry, profiles,
        lambda run: pages(repo, f"actions/runs/{run}/artifacts?per_page=100","artifacts"),
        paths, base_registry)
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
    if not found and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        raise ValueError("No matching public artifact for explicitly selected merged PR; inspect discovery diagnostics")
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
