"""Permanent encrypted archive; no Google requests."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import manager

def archive(root, experiment, run, source, api_key, archive_key):
    if experiment not in manager.EXPERIMENTS or not str(run).isdigit():
        raise ValueError("Invalid archive identity")
    if not archive_key or archive_key == api_key:
        raise ValueError("Separate archive key required")
    response = manager.load(api_key, experiment, source)
    canonical = json.dumps(response, sort_keys=True, separators=(",", ":")).encode()
    # Keyed fingerprint avoids publishing a digest of private plaintext.
    fingerprint = hmac.new(archive_key.encode(), canonical, hashlib.sha256).hexdigest()
    folder = root / experiment
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (fingerprint + ".enc")
    if target.exists():
        if manager.load(archive_key, experiment, target) != response:
            raise ValueError("Archive collision")
    else:
        manager.seal(archive_key, experiment, response, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    index = root / "index.json"
    data = json.loads(index.read_text()) if index.exists() else {}
    entries = data.setdefault(experiment, {})
    record = {"file": str(target.relative_to(root)), "sha256": digest}
    if str(run) in entries and entries[str(run)] != record:
        raise ValueError("Run already archived with different content")
    entries[str(run)] = record
    index.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

def restore(root, experiment, output, api_key, archive_key):
    entries = json.loads((root / "index.json").read_text())[experiment]
    record = entries[max(entries, key=int)]
    path = root / record["file"]
    if path.parent != root / experiment or not path.name.endswith(".enc"):
        raise ValueError("Invalid archive path")
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError("Archive digest mismatch")
    response = manager.load(archive_key, experiment, path)
    manager.seal(api_key, experiment, response, output)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["archive", "restore"])
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--experiment", choices=manager.EXPERIMENTS, required=True)
    p.add_argument("--run")
    p.add_argument("--file", type=Path, required=True)
    a = p.parse_args()
    key, archive_key = os.environ["GEMINI_API_KEY"], os.environ["AG_ARCHIVE_KEY"]
    if a.mode == "archive":
        archive(a.root, a.experiment, a.run, a.file, key, archive_key)
    else:
        restore(a.root, a.experiment, a.file, key, archive_key)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Archive operation failed: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
