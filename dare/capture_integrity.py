"""Verify raw capture bytes before offline study replay.

Only local static files and a trusted, independently frozen manifest.
This establishes byte integrity, not authenticity or normalization fidelity.
"""
import hashlib
from pathlib import Path
from replay_dataset import digest, evaluate


def verify_captures(root, records, manifest, frozen_manifest_digest):
    if digest(manifest) != frozen_manifest_digest:
        raise ValueError("manifest digest mismatch")
    if type(records) is not list or type(manifest) is not dict:
        raise ValueError("invalid input")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("invalid archive directory")
    ids = set()
    for case in records:
        cid = case["id"]
        if type(cid) is not str or not cid or cid in ids:
            raise ValueError("duplicate or invalid case ID")
        ids.add(cid)
        entry = manifest.get(cid)
        if type(entry) is not dict or set(entry) != {"path", "sha256", "source", "collected_at"}:
            raise ValueError("invalid manifest entry")
        name, expected = entry["path"], entry["sha256"]
        if (type(name) is not str or "\\" in name
                or any(p in ("", ".", "..") for p in name.split("/"))):
            raise ValueError("unsafe capture path")
        if (type(expected) is not str or len(expected) != 64
                or any(c not in "0123456789abcdef" for c in expected)
                or expected != case["raw_sha256"]):
            raise ValueError("capture digest mismatch")
        if (entry["source"] != case["record"]["source"]
                or type(entry["collected_at"]) is not int
                or entry["collected_at"] < case["record"]["observed"]):
            raise ValueError("invalid capture metadata")
        path = root
        for part in name.split("/"):
            path = path / part
            if path.is_symlink():
                raise ValueError("symlink capture")
        if not path.is_file():
            raise ValueError("missing capture")
        with path.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != expected:
                raise ValueError("capture bytes mismatch")
    if ids != set(manifest):
        raise ValueError("unmatched manifest entries")


def verified_replay(root, records, references, frozen_digest,
                    manifest, frozen_manifest_digest):
    verify_captures(root, records, manifest, frozen_manifest_digest)
    result = evaluate(records, references, frozen_digest)
    result["capture_integrity"] = "VERIFIED_BYTES_ONLY"
    return result
