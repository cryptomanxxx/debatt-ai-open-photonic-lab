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
        if SENSITIVE.search(decoded) or any(s and s in decoded for s in blocked):
            raise ValueError("Sensitive content")
        files[name] = data
    if set(files) != NAMES:
        raise ValueError("Missing original files")
    if not isinstance(json.loads(files["report.json"]), dict):
        raise ValueError("Invalid report")
    return files

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    key = os.environ["GEMINI_API_KEY"]
    response = manager.load(key, "AG-PHOTONIC-003", a.checkpoint)
    if response.get("status") != "completed":
        raise ValueError("Recovery not completed")
    texts = [part["text"] for step in response["steps"]
             if step.get("type") == "model_output"
             for part in step["content"] if part.get("type") == "text"]
    if not texts:
        raise ValueError("No manifest")
    manifest = json.loads(texts[-1])
    files = validate(manifest, (key, response.get("id"), response.get("environment_id")))
    a.output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (a.output / name).write_bytes(data)
    print("Seven files passed byte-integrity checks; manual scientific and security review required.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Recovery extraction stopped: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
