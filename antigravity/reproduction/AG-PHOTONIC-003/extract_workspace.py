"""Validate a recovered manifest without executing or publishing agent code."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import manager
from scientific_export import SENSITIVE

NAMES = frozenset(("params.py", "physics_model.py", "sweep.py",
                   "circuit_sim.py", "train_sim.py", "run_all.py", "report.json"))

ID_KEYS = frozenset(("id", "call_id", "signature", "environment_id",
                     "previous_interaction_id", "interaction_id"))

def identifiers(*responses):
    blocked = set()
    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ID_KEYS and isinstance(value, str) and value:
                    blocked.add(value)
                if isinstance(value, (dict, list)):
                    visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    for response in responses:
        visit(response)
    return blocked

def screen(text, blocked):
    if SENSITIVE.search(text) or any(s and s in text for s in blocked):
        raise ValueError("Sensitive content")

def metadata(manifest, blocked=()):
    # Preserve all non-file evidence, including dependency and energy audit fields.
    # Screen decoded strings as well as serialized output (escaped JSON strings
    # must not hide known identifiers or secret patterns).
    evidence = {k: v for k, v in manifest.items() if k != "files"}
    evidence["file_integrity"] = [
        {k: item[k] for k in ("name", "size_bytes", "sha256")}
        for item in manifest["files"]
    ]
    def visit(obj):
        if isinstance(obj, str):
            screen(obj, blocked)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                screen(k, blocked)
                visit(v)
        elif isinstance(obj, list):
            for v in obj:
                visit(v)
    visit(evidence)
    serialized = json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    screen(serialized, blocked)
    return serialized

def validate(manifest, blocked=()):
    if not isinstance(manifest, dict) or manifest.get("missing") or not isinstance(manifest.get("files"), list):
        raise ValueError("Incomplete manifest")
    files = {}
    for item in manifest["files"]:
        name = item["name"]
        if name not in NAMES or name in files:
            raise ValueError("Unexpected or duplicate file")
        data = base64.b64decode(item["base64"], validate=True)
        if not data or len(data) > 2_000_000 or type(item["size_bytes"]) is not int or len(data) != item["size_bytes"]:
            raise ValueError("Invalid size")
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Digest mismatch")
        decoded = data.decode("utf-8")
        screen(decoded, blocked)
        files[name] = data
    if set(files) != NAMES:
        raise ValueError("Missing original files")
    if not isinstance(json.loads(files["report.json"]), dict):
        raise ValueError("Invalid report")
    return files

def select_manifest(response, blocked):
    # Prefer successful code execution results over model-transcribed text.
    # Never execute returned code, repair JSON, or choose between conflicting
    # byte sets. Every recognized manifest must pass full validation.
    candidates = []
    for index, step in enumerate(response["steps"]):
        if step.get("type") == "code_execution_result" and step.get("is_error") is False:
            texts = [step.get("result")]
            source = "code_execution_result"
        elif step.get("type") == "model_output":
            texts = [part.get("text") for part in step["content"] if part.get("type") == "text"]
            source = "model_output"
        else:
            continue
        for text in texts:
            if not isinstance(text, str):
                continue
            try:
                manifest = json.loads(text)
            except ValueError:
                continue
            if not isinstance(manifest, dict) or "files" not in manifest:
                continue
            files = validate(manifest, blocked)
            evidence = json.loads(metadata(manifest, blocked))
            candidates.append((source, index, files, evidence))
    if not candidates:
        raise ValueError("No complete valid manifest")
    chosen = next((c for c in candidates if c[0] == "code_execution_result"), candidates[0])
    if any(c[2] != chosen[2] for c in candidates):
        raise ValueError("Conflicting recovered bytes")
    # Retain separate screened evidence rather than silently overwrite metadata.
    evidence = dict(chosen[3])
    evidence["manifest_source"] = chosen[0]
    evidence["manifest_step"] = chosen[1]
    evidence["other_manifest_evidence"] = [
        {"source": c[0], "step": c[1], "metadata": c[3]}
        for c in candidates if c is not chosen
    ]
    serialized = json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    screen(serialized, blocked)
    return chosen[2], serialized

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--previous", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    key = os.environ["GEMINI_API_KEY"]
    response = manager.load(key, "AG-PHOTONIC-003", a.checkpoint)
    if response.get("status") != "completed":
        raise ValueError("Recovery not completed")
    original = manager.load(key, "AG-PHOTONIC-003", a.original)
    if original.get("status") != "completed" or original["id"] == response["id"]:
        raise ValueError("Invalid original checkpoint")
    previous = manager.load(key, "AG-PHOTONIC-003", a.previous) if a.previous else {}
    if response.get("environment_id") != original.get("environment_id"):
        raise ValueError("Recovery environment mismatch")
    if previous and previous.get("environment_id") != original.get("environment_id"):
        raise ValueError("Previous recovery environment mismatch")
    blocked = identifiers(original, previous, response) | {key}
    files, evidence = select_manifest(response, blocked)
    a.output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (a.output / name).write_bytes(data)
    (a.output / "recovery-metadata.json").write_text(evidence, encoding="utf-8")
    print("Seven files passed byte-integrity checks; manual scientific and security review required.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Recovery extraction stopped: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
