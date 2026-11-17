"""Read-only workspace download from the documented Environments Files API."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile
import urllib.request
import urllib.error
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import manager
from extract_workspace import NAMES, identifiers, screen

EXPERIMENT = "AG-PHOTONIC-003"
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_FILE = 2_000_000
HOST = "generativelanguage.googleapis.com"

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Permit HTTPS redirects to Google storage only, without API credentials."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlsplit(newurl)
        if (u.scheme != "https" or u.username or u.password or u.port not in (None, 443)
                or u.hostname not in (HOST, "storage.googleapis.com",
                                       "generativelanguage.googleapis.com")):
            raise ValueError("Unexpected download redirect")
        return urllib.request.Request(newurl, method="GET")

def download(key, environment):
    environment = manager.background.valid_id(environment)
    if environment == "remote":
        raise ValueError("Existing environment required")
    url = f"https://{HOST}/v1beta/environments/{environment}/files/workspace?alt=media&recursive=true"
    req = urllib.request.Request(url, headers={"x-goog-api-key": key}, method="GET")
    with urllib.request.build_opener(SafeRedirect()).open(req, timeout=120) as response:
        if response.status != 200:
            raise ValueError("Unexpected download status")
        raw = response.read(MAX_ARCHIVE + 1)
    if not raw or len(raw) > MAX_ARCHIVE:
        raise ValueError("Archive empty or exceeds configured limit")
    return raw

def inspect(raw, blocked):
    """Never extract arbitrary archive paths or execute downloaded content."""
    found = {}
    count = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for member in archive:
            count += 1
            if count > 100_000:
                raise ValueError("Too many archive entries")
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts:
                raise ValueError("Unsafe archive path")
            # Accept only exact root or workspace-relative names, not nested
            # lookalikes or symlinks/hardlinks.
            name = p.name
            if name not in NAMES or p.parts not in ((name,), ("workspace", name)):
                continue
            if name in found or not member.isfile() or not 0 < member.size <= MAX_FILE:
                raise ValueError("Duplicate, nonregular or oversized expected file")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing file bytes")
            data = stream.read(MAX_FILE + 1)
            if len(data) != member.size:
                raise ValueError("Truncated file")
            found[name] = data
    files = {}
    unsafe = []
    for name, data in sorted(found.items()):
        try:
            screen(data.decode("utf-8"), blocked)
            if name == "report.json" and not isinstance(json.loads(data), dict):
                raise ValueError("Invalid report")
        except (ValueError, UnicodeError, RecursionError):
            unsafe.append(name)
            continue
        files[name] = data
    info = {"experiment": EXPERIMENT, "archive_bytes": len(raw),
            "archive_sha256": hashlib.sha256(raw).hexdigest(),
            "archive_entries": count,
            "missing": sorted(NAMES - found.keys()),
            "withheld": unsafe,
            "files": [{"name": name, "size_bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()}
                      for name, data in files.items()],
            "complete": set(files) == NAMES,
            "note": "Current workspace snapshot, not immutable historical proof; code not executed."}
    return files, info

def snapshot(key, checkpoint, output, confirm, public=False):
    if not key or not confirm or output.exists():
        raise ValueError("Explicit confirmation and new output required")
    original = manager.load(key, EXPERIMENT, checkpoint)
    if original.get("status") != "completed":
        raise ValueError("Completed original required")
    raw = download(key, original.get("environment_id"))
    output.mkdir(parents=True, exist_ok=False)
    # Full archive may contain unrelated private material. Encrypt before any
    # analysis, using a domain-separated key from the existing checkpoint key.
    encrypted = manager.cipher("workspace-snapshot-v1:" + key).encrypt(raw)
    (output / "snapshot.tar.enc").write_bytes(encrypted)
    files, info = inspect(raw, identifiers(original) | {key})
    report = json.dumps(info, indent=2) + "\n"
    (output / "snapshot-diagnostics.json").write_text(report, encoding="utf-8")
    print(report, end="")
    if public and info["complete"]:
        directory = output / "source"
        directory.mkdir()
        for name, data in files.items():
            (directory / name).write_bytes(data)
    return info["complete"]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--confirm-free-project", action="store_true")
    p.add_argument("--confirm-public-export", action="store_true")
    a = p.parse_args()
    try:
        complete = snapshot(os.environ["GEMINI_API_KEY"], a.checkpoint, a.output,
                            a.confirm_free_project, a.confirm_public_export)
        return 0 if complete else 1
    except urllib.error.HTTPError as exc:
        print(manager.safe_http_error(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Snapshot stopped: {type(exc).__name__}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
