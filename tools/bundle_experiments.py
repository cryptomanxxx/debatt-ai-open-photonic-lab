"""Collect experiment artifacts without depending on single/multi download layout."""
import json
import os
from pathlib import Path
import subprocess
import sys


def expected_result(experiment, args):
    if experiment == "opa-fdtd-005":
        profile = args or "small"
        if profile not in ("small", "medium", "large"):
            raise ValueError(f"Unknown benchmark profile: {profile!r}")
        return f"benchmark-{profile}.json"
    return "result.json"


def collect(root, expected, available, download, args, metadata):
    root.mkdir(exist_ok=True, parents=True)
    entries = []
    for experiment in expected:
        name = experiment["artifact"]
        directory = root / name
        filename = expected_result(experiment["id"], args)
        present = name in available
        if present:
            directory.mkdir(exist_ok=False)
            download(name, directory)
        entries.append({
            "experiment": experiment["id"],
            "artifact": name,
            "artifact_present": present,
            "expected_result": filename,
            "result_json_present": present and (directory / filename).is_file(),
        })
    manifest = {
        **metadata,
        "all_expected_results_present": all(
            e["artifact_present"] and e["result_json_present"] for e in entries
        ),
        "experiments": entries,
    }
    (root / "bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "prepare":
        # Remove the previous checked-in report before the experiment runs.
        # A failed run must not appear complete because an old report exists.
        directory = Path(sys.argv[3])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / expected_result(sys.argv[2], os.environ.get("ARGS", ""))).unlink(missing_ok=True)
        return
    repo = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    expected = json.loads(os.environ["EXPECTED"])["include"]
    available = set(subprocess.check_output([
        "gh", "api", "--paginate",
        f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100",
        "--jq", ".artifacts[] | select(.expired == false) | .name",
    ], text=True).splitlines())

    def download(name, directory):
        # gh extracts a single named artifact directly into --dir.
        subprocess.run([
            "gh", "run", "download", run_id, "--repo", repo,
            "--name", name, "--dir", str(directory),
        ], check=True)

    collect(Path("collected"), expected, available, download,
            os.environ.get("ARGS", ""), {
                "run_id": run_id,
                "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
                "workflow_sha": os.environ["GITHUB_SHA"],
                "experiment_job_result": os.environ["RUN_RESULT"],
            })


if __name__ == "__main__":
    main()
