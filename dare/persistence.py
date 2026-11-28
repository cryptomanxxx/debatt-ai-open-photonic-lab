"""Offline single-writer snapshots and local archive integrity checks."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from dataclasses import asdict
from state_machine import Engine, Task


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validated_restore(raw):
    data = json.loads(raw, object_pairs_hook=_unique_pairs)
    if type(data) is not dict or set(data) != {"tasks", "stopped"}:
        raise ValueError("invalid snapshot")
    if type(data["stopped"]) is not bool or type(data["tasks"]) is not dict:
        raise ValueError("invalid engine fields")
    defaults = asdict(Task())
    tasks = {}
    for key, fields in data["tasks"].items():
        if not key or type(fields) is not dict or set(fields) != set(defaults):
            raise ValueError("invalid task")
        for name, value in fields.items():
            expected = type(defaults[name])
            if expected is tuple:
                if type(value) is not list or any(type(v) is not str or not v for v in value):
                    raise ValueError("invalid sequence field")
                fields[name] = tuple(value)
            elif type(value) is not expected:
                raise ValueError("invalid field type")
        if fields["sequence"] < 0 or fields["retries"] < 0 or fields["threads"] < -1:
            raise ValueError("invalid counter")
        if fields["quota"] not in {"available", "unknown", "exhausted"}:
            raise ValueError("invalid quota")
        if fields["ci"] not in {"unknown", "passed", "failed", "pending", "skipped"}:
            raise ValueError("invalid CI state")
        if fields["review"] not in {"unknown", "clear", "findings", "pending"}:
            raise ValueError("invalid review state")
        if fields["archive_verified"] and not fields["merged"]:
            raise ValueError("archive without merge")
        tasks[key] = Task(**fields)
    engine = Engine(tasks, data["stopped"])
    if not engine._graph_valid():
        raise ValueError("invalid dependency graph")
    return engine


def save_snapshot(path, engine):
    """Atomic replacement on a local filesystem; one trusted writer only."""
    path = Path(path)
    raw = engine.snapshot()
    validated_restore(raw)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as handle:
            temp = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def load_snapshot(path):
    """Missing or invalid state raises; caller must stop, not initialize."""
    return validated_restore(Path(path).read_text(encoding="utf-8"))


def verify_archive(root, expected, manifest):
    """Verify exact required file set and SHA-256 against trusted inputs.

    Local, immutable fixture directory only; not safe for concurrent writers.
    Manifest authenticity and association with a run/head are separate gates.
    """
    if type(expected) not in (set, frozenset) or not expected:
        return False
    if type(manifest) is not dict or set(manifest) != expected:
        return False
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return False
    try:
        for name, digest in manifest.items():
            if type(name) is not str or not name or type(digest) is not str:
                return False
            parts = name.split("/")
            if any(p in {"", ".", ".."} for p in parts) or "\\" in name:
                return False
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                return False
            path = root
            for part in parts:
                path = path / part
                if path.is_symlink():
                    return False
            if not path.is_file():
                return False
            with path.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != digest:
                    return False
    except (OSError, ValueError):
        return False
    return True
