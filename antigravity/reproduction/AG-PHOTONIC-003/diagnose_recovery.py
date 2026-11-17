"""Offline diagnostics; emit only fixed labels, booleans and bounded counts."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import manager
from scientific_export import diagnostics
from extract_workspace import NAMES, identifiers, validate, metadata

EXPERIMENT = "AG-PHOTONIC-003"

def inspect(response, original, key, run):
    if original.get("status") != "completed" or response["id"] == original["id"]:
        raise ValueError("Invalid recovery provenance")
    info = diagnostics(response, EXPERIMENT, run)
    info["schema_version"] = 2
    info["recovery_run"] = info.pop("manager_run")
    info["same_environment"] = (
        isinstance(original.get("environment_id"), str)
        and original["environment_id"] != "remote"
        and response.get("environment_id") == original["environment_id"]
    )
    steps = response.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("Invalid steps")
    types = ("model_output", "code_execution_call", "code_execution_result",
             "function_call", "function_result")
    info["step_count"] = len(steps)
    info["step_counts"] = {kind: sum(isinstance(s, dict) and s.get("type") == kind
                                   for s in steps) for kind in types}
    info["tool_errors"] = sum(isinstance(s, dict) and s.get("type") in
                              ("function_result", "code_execution_result")
                              and s.get("is_error") is True for s in steps)
    info["final_text_count"] = 0
    info["manifest_candidates"] = 0
    info["complete_valid_manifest_candidates"] = 0
    info["expected_file_mentions"] = []
    mentioned = set()
    blocked = identifiers(original, response) | {key}
    for step in steps:
        if not isinstance(step, dict):
            continue
        candidates = []
        if step.get("type") == "model_output":
            parts = step.get("content", [])
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                        info["final_text_count"] += 1
                        candidates.append(part["text"])
        elif step.get("type") in ("function_result", "code_execution_result"):
            if isinstance(step.get("result"), str):
                candidates.append(step["result"])
        for candidate in candidates:
            mentioned.update(name for name in NAMES if name in candidate)
            # A complete JSON object only; never repair or execute agent output.
            try:
                manifest = json.loads(candidate)
            except (ValueError, RecursionError):
                continue
            if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
                continue
            info["manifest_candidates"] += 1
            try:
                validate(manifest, blocked)
                metadata(manifest, blocked)
            except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
                continue
            info["complete_valid_manifest_candidates"] += 1
    info["expected_file_mentions"] = sorted(mentioned)
    info["evidence_note"] = "Mentions are not recovered files. Valid candidates have self-consistent digests only; no execution or provenance verification."
    return info

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if not re.fullmatch(r"[0-9]{1,20}", a.run):
        raise ValueError("Invalid run")
    key = os.environ["GEMINI_API_KEY"]
    original = manager.load(key, EXPERIMENT, a.original)
    response = manager.load(key, EXPERIMENT, a.checkpoint)
    result = inspect(response, original, key, a.run)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    a.output.write_text(text, encoding="utf-8")
    print(text, end="")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Recovery diagnostics stopped: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
