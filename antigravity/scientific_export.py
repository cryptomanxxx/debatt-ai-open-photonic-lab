"""Export selected scientific evidence, never execute agent-provided code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import manager

SENSITIVE = re.compile(r"AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]+|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?i:bearer\s+[A-Za-z0-9._-]{12,})")

def extract(response, experiment, run, secrets=(), allow_partial=False):
    status = response.get("status")
    complete = status == "completed"
    if not complete and not allow_partial:
        raise ValueError("Completed response required")
    safe_status = status if status in ("completed", "failed", "cancelled", "canceled", "incomplete", "expired", "active", "running", "pending", "queued", "requires_action", "in_progress") else "unknown"
    steps = response.get("steps", []) if not complete else response["steps"]
    if not isinstance(steps, list):
        raise ValueError("Unexpected steps format")
    blocked = set(s for s in secrets if s)
    def collect_ids(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("id", "call_id", "signature", "environment_id", "previous_interaction_id", "interaction_id") and isinstance(v, str) and v:
                    blocked.add(v)
                elif isinstance(v, (dict, list)):
                    collect_ids(v)
        elif isinstance(obj, list):
            for v in obj:
                collect_ids(v)
    collect_ids(response)
    evidence = []
    reports = []
    def checked(value):
        if not isinstance(value, str):
            raise ValueError("Unexpected text format")
        if SENSITIVE.search(value) or any(s in value for s in blocked):
            raise ValueError("Sensitive content detected")
        return value
    for i, step in enumerate(steps):
        kind = step.get("type")
        item = {"step": i, "type": kind}
        if kind == "model_output":
            for part in step["content"]:
                if part.get("type") == "text":
                    reports.append({"step": i, "text": checked(part["text"])})
        elif kind == "code_execution_call":
            args = step["arguments"]
            item.update(language=checked(args["language"]), code=checked(args["code"]))
            evidence.append(item)
        elif kind == "function_call" and step.get("name") == "write_to_file":
            args = step["arguments"]
            item.update(target=checked(args["TargetFile"]), code=checked(args["CodeContent"]))
            evidence.append(item)
        elif kind in ("code_execution_result", "function_result"):
            if kind == "function_result" and step.get("name") != "write_to_file":
                continue
            if type(step["is_error"]) is not bool:
                raise ValueError("Invalid error flag")
            item.update(is_error=step["is_error"], result=checked(step["result"]))
            evidence.append(item)
    if complete and not reports:
        raise ValueError("No scientific report found")
    return dict(schema_version=2, experiment=experiment, manager_run=run,
                response_status=safe_status, partial=not complete,
                step_count=len(steps),
                validation="agent-reported; independent validation required" if complete else "partial agent evidence; not a completed scientific result",
                reports=reports, execution_evidence=evidence)

def export(root, experiment, run, key, output, allow_partial=False):
    if not re.fullmatch(r"[0-9]+", run) or not key:
        raise ValueError("Invalid run or key")
    record = json.loads((root / "index.json").read_text())[experiment][run]
    name = record["file"]
    if not re.fullmatch(re.escape(experiment) + r"/[a-f0-9]{64}\.enc", name):
        raise ValueError("Invalid archive path")
    path = root / name
    if path.resolve().parent != (root / experiment).absolute() or path.is_symlink():
        raise ValueError("Invalid archive location")
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("Archive digest mismatch")
    response = manager.load(key, experiment, path)
    result = extract(response, experiment, run, (key,), allow_partial=allow_partial)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--experiment", choices=manager.EXPERIMENTS, required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--allow-partial", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    export(a.root, a.experiment, a.run, os.environ["AG_ARCHIVE_KEY"], a.output, allow_partial=a.allow_partial)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Scientific export stopped: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
